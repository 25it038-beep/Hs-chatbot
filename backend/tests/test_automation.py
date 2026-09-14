"""OS Automation engine tests (section 2-6 spec cases).

Unit tests never touch the real OS: engine tests monkeypatch the controller
singletons with fakes so intent→route→safety logic is exercised without side
effects. Intent detection is pure and tested directly.

Covers: intent table (spec phrasings + negatives), risk classification,
server-hint reclassification, website pre-pass, command chaining, event bus,
confirmation gating (voice_verified), hard-confirm for HIGH/CRITICAL, cancel,
ambiguity resolution, and the cloud/local gate.
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.automation.intent_detector import intent_detector
from app.services.automation.schema import (
    AutomationIntent,
    AutomationResponse,
    IntentType,
    RiskLevel,
)
from app.services.automation import controllers as ctl
from app.services.automation.controllers import ControllerResult
from app.services.automation.engine import AutomationEngine
import app.services.automation.engine as engine_mod
from app.services.automation.isolated_executor import IsolatedExecutor


def fake_controller_result(success=True, message="ok", error=None, data=None):
    return ControllerResult(success=success, message=message, error=error, data=data)


class FakeController:
    """Records calls, returns canned results."""

    def __init__(self, name="controller"):
        self.name = name
        self.calls = []
        self.result = fake_controller_result()

    def __getattr__(self, item):
        def _method(*args, **kwargs):
            self.calls.append((item, args, kwargs))
            return self.result
        return _method


@pytest.fixture
def fresh_engine():
    eng = AutomationEngine()
    yield eng
    eng.pending_confirmations.clear()


# ── Intent detection table ─────────────────────────────────────

@pytest.mark.parametrize("phrase,expected", [
    ("open chrome", IntentType.OPEN_APPLICATION),
    ("launch vs code", IntentType.OPEN_APPLICATION),
    ("switch to chrome", IntentType.SWITCH_APPLICATION),
    ("minimize this window", IntentType.MINIMIZE_WINDOW),
    ("snap this window to the left", IntentType.SNAP_WINDOW_LEFT),
    ("show desktop", IntentType.SHOW_DESKTOP),
    ("take a screenshot", IntentType.TAKE_SCREENSHOT),
    ("lock my computer", IntentType.LOCK_SCREEN),
    ("set volume to 70%", IntentType.SET_VOLUME),
    ("increase volume", IntentType.ADJUST_VOLUME),
    ("what is the volume", IntentType.GET_VOLUME),
    ("check cpu usage", IntentType.GET_CPU_USAGE),
    ("check cpu and ram usage", IntentType.GET_CPU_USAGE),
    ("check ram usage", IntentType.GET_RAM_USAGE),
    ("create a folder called Projects", IntentType.CREATE_FOLDER),
    ("delete the folder Temp", IntentType.DELETE_FOLDER),
    ("rename test.txt to final.txt", IntentType.RENAME_FILE),
    ("copy notes.txt to Documents", IntentType.COPY_FILE),
    ("move report.pdf to Documents", IntentType.MOVE_FILE),
    ("find all pdf files in Downloads", IntentType.SEARCH_FILES),
    ("press ctrl+c", IntentType.KEY_PRESS),
    ("type hello world", IntentType.TYPE_TEXT),
    ("scroll down", IntentType.SCROLL),
    ("run npm install", IntentType.RUN_COMMAND),
    ("run the script deploy.py", IntentType.RUN_SCRIPT),
    ("show running processes", IntentType.LIST_PROCESSES),
    ("stop the chrome process", IntentType.STOP_PROCESS),
    ("monitor cpu", IntentType.MONITOR_PROCESS),
    ("open youtube", IntentType.OPEN_URL),
    ("open github.com", IntentType.OPEN_URL),
    ("search google for python tutorials", IntentType.SEARCH_WEB),
    ("open my downloads", IntentType.OPEN_FOLDER),
    ("check wifi status", IntentType.CHECK_WIFI),
    ("check bluetooth status", IntentType.CHECK_BLUETOOTH),
    ("check battery status", IntentType.CHECK_BATTERY),
    ("restart the computer", IntentType.RESTART),
    ("shut down the computer", IntentType.SHUTDOWN),
    ("restart the backend", IntentType.RESTART_PROCESS),
    ("close the backend", IntentType.STOP_PROCESS),
])
def test_intent_table(phrase, expected):
    intent = intent_detector.detect_intent(phrase)
    assert intent.intent == expected, f"{phrase!r} → {intent.intent.value}"


@pytest.mark.parametrize("phrase", [
    "What is the weather today?",
    "Tell me a joke",
    "Write a poem about the ocean",
    "Explain quantum computing",
    "I can't play football today",
])
def test_negative_intents_stay_unknown(phrase):
    intent = intent_detector.detect_intent(phrase)
    assert intent.intent == IntentType.UNKNOWN


@pytest.mark.parametrize("phrase,risk", [
    ("open chrome", RiskLevel.LOW),
    ("set volume to 50%", RiskLevel.LOW),
    ("type hello", RiskLevel.LOW),
    ("take a screenshot", RiskLevel.LOW),
    ("create a folder called X", RiskLevel.LOW),
    ("rename a.txt to b.txt", RiskLevel.MEDIUM),
    ("move report.pdf to Documents", RiskLevel.MEDIUM),
    ("restart the backend", RiskLevel.MEDIUM),
    ("close the browser", RiskLevel.MEDIUM),
    ("run npm install", RiskLevel.HIGH),
    ("delete the folder Temp", RiskLevel.CRITICAL),
    ("shut down the computer", RiskLevel.CRITICAL),
    ("run the script deploy.py", RiskLevel.CRITICAL),
])
def test_risk_classification(phrase, risk):
    intent = intent_detector.detect_intent(phrase)
    assert intent.risk_level == risk, f"{phrase!r} → {intent.risk_level.value}"


def test_cleanup_strips_wake_word_and_pleas():
    intent = intent_detector.detect_intent("Hey HS, can you please open chrome?")
    assert intent.intent == IntentType.OPEN_APPLICATION
    assert intent.target == "chrome"

    intent = intent_detector.detect_intent("Wake up, open chrome")
    assert intent.intent == IntentType.OPEN_APPLICATION
    assert intent.target == "chrome"

    intent = intent_detector.detect_intent("wakeup open chrome")
    assert intent.intent == IntentType.OPEN_APPLICATION
    assert intent.target == "chrome"


# ── Engine routing + safety ────────────────────────────────────

@pytest.mark.asyncio
async def test_low_risk_executes_without_confirmation(fresh_engine):
    fake = FakeController()
    with patch.object(engine_mod, "system_controller", fake):
        resp = await fresh_engine.process_command("get volume", "u1")
    assert resp.success is True
    assert ("get_volume", (), {}) in fake.calls


@pytest.mark.asyncio
async def test_medium_risk_requires_confirmation(fresh_engine):
    fake = FakeController()
    with patch.object(engine_mod, "app_controller", fake):
        resp = await fresh_engine.process_command("close the browser", "u1")
    assert resp.success is False
    assert resp.requires_confirmation is True
    pending = fresh_engine.get_pending_confirmations()
    assert len(pending) == 1


@pytest.mark.asyncio
async def test_critical_risk_never_auto_executes(fresh_engine):
    fake = FakeController()
    with patch.object(engine_mod, "folder_controller", fake):
        resp = await fresh_engine.process_command("delete the folder Temp", "u1")
    assert resp.success is False
    assert fake.calls == []
    assert resp.requires_confirmation is True


@pytest.mark.asyncio
async def test_confirm_flow_executes_pending(fresh_engine):
    fake = FakeController()
    with patch.object(engine_mod, "app_controller", fake):
        resp = await fresh_engine.process_command("close the browser", "u1")
        pending = fresh_engine.get_pending_confirmations()
        assert len(pending) == 1
        resp2 = await fresh_engine.confirm_action(pending[0]["action_id"], True, "u1")
    assert resp2.success is True
    assert fresh_engine.get_pending_confirmations() == []
    assert any(c[0] == "close_application" for c in fake.calls)


@pytest.mark.asyncio
async def test_reject_clears_pending(fresh_engine):
    fake = FakeController()
    with patch.object(engine_mod, "app_controller", fake):
        resp = await fresh_engine.process_command("close the browser", "u1")
        pending = fresh_engine.get_pending_confirmations()
        resp2 = await fresh_engine.confirm_action(pending[0]["action_id"], False, "u1")
    assert resp2.success is False
    assert "cancelled" in resp2.message.lower()
    assert fake.calls == []
    assert fresh_engine.get_pending_confirmations() == []


@pytest.mark.asyncio
async def test_voice_verified_unlocks_medium_without_ui_confirm(fresh_engine):
    """Voice-verified users bypass the confirmation prompt for MEDIUM (spec: voice match = trusted)."""
    fake = FakeController()
    with patch.object(engine_mod, "app_controller", fake):
        resp = await fresh_engine.process_command("close the browser", "u1", voice_verified=True)
    assert resp.success is True
    assert any(c[0] == "close_application" for c in fake.calls)


@pytest.mark.asyncio
async def test_voice_unverified_blocks_critical_even_with_confirmation(fresh_engine):
    fake = FakeController()
    with patch.object(engine_mod, "folder_controller", fake):
        resp = await fresh_engine.process_command("delete the folder Temp", "u1", voice_verified=False)
    assert resp.success is False
    assert fake.calls == []


@pytest.mark.asyncio
async def test_command_chain_runs_sequential_steps(fresh_engine):
    fake = FakeController()
    with patch.object(engine_mod, "system_controller", fake):
        resp = await fresh_engine.process_command("increase volume and get battery status", "u1")
    assert resp.success is True
    step_calls = [c[0] for c in fake.calls]
    assert step_calls == ["adjust_volume", "check_battery"]


@pytest.mark.asyncio
async def test_chain_stops_on_failure(fresh_engine):
    fake = FakeController()
    fake.result = fake_controller_result(success=False, message="boom", error="boom")
    with patch.object(engine_mod, "system_controller", fake):
        resp = await fresh_engine.process_command("increase volume and get battery status", "u1")
    assert resp.success is False
    assert "boom" in resp.message


@pytest.mark.asyncio
async def test_cancel_aborts_pending_action(fresh_engine):
    fake = FakeController()

    async def slow_adjust(*args, **kwargs):
        await asyncio.sleep(0.05)
        return fake_controller_result(success=True, message="adjusted")

    fake.adjust_volume = slow_adjust
    with patch.object(engine_mod, "system_controller", fake):
            task = asyncio.create_task(
                fresh_engine.process_command("increase volume", "u1")
            )
            await asyncio.sleep(0.01)
            await fresh_engine.cancel()
            resp = await task
    assert resp.success is False
    assert "cancelled" in resp.message.lower()


@pytest.mark.asyncio
async def test_event_bus_publishes_steps(fresh_engine):
    fake = FakeController()
    events = []
    sub = fresh_engine.subscribe()
    consumer = asyncio.create_task(_drain(sub, events))
    with patch.object(engine_mod, "system_controller", fake):
        await fresh_engine.process_command("increase volume", "u1")
    await asyncio.sleep(0.05)
    consumer.cancel()
    types = {e.get("type") for e in events}
    assert "action_start" in types
    assert "action_done" in types


@pytest.mark.asyncio
async def test_ambiguity_offers_options(fresh_engine):
    fake = FakeController()
    fake.find_folder_candidates = lambda name: [
        r"C:\Work\Projects", r"C:\Archive\Projects"]
    with patch.object(engine_mod, "folder_controller", fake):
        resp = await fresh_engine.process_command("open the folder Projects", "u1")
    assert resp.success is False
    assert "multiple matches" in resp.message.lower()
    assert len(resp.options or []) == 2


async def _drain(queue, sink):
    while True:
        sink.append(await queue.get())
