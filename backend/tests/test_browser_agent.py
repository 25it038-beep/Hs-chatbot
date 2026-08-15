"""Browser Automation Agent tests (section 28 spec cases).

Unit tests never launch a real browser: agent-level tests patch the module
driver helpers / `_run`; service tests mock `browser_agent.run_plan`. The
intent/planner layers are pure and tested directly. Real-Chrome smoke is a
manual step (see AGENTS.md).

Covers: intent table (all spec phrasings + false-positive negatives), safety
confirmation gating, media-control context rules, planner minimality, selector
fallback strategy, retry limits, URL safety, screenshot/state, and the service
delegate/confirm flows.
"""

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.browser import intent as bi
from app.services.browser import service as bsvc
from app.services.browser import planner as bp
from app.services.browser.agent import ActionError, BrowserAgent
from app.services.browser.config import browser_config as cfg
from app.services.browser.intent import classify_browser_intent


# --------------------------------------------------------------------------
# Intent table
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "message,expected,fields",
    [
        ("Open Spotify", "OPEN_WEBSITE", {"service": "spotify"}),
        ("Open Gmail", "OPEN_WEBSITE", {"service": "gmail", "url": "https://mail.google.com"}),
        ("Open the OpenAI website", "OPEN_WEBSITE", {"service": "openai"}),
        ("Go to github.com", "NAVIGATE", {"url": "https://github.com"}),
        ("Open this website", "NAVIGATE", {"url": None}),
        ("Open GitHub and search for FastAPI projects", "SEARCH_SITE", {"service": "github", "query": "FastAPI projects"}),
        ("Go to Wikipedia and search for AI", "SEARCH_SITE", {"service": "wikipedia", "query": "AI"}),
        ("Search this website for laptops", "SEARCH_SITE", {"service": bi.CURRENT_PAGE, "query": "laptops"}),
        ("Search GitHub for FastAPI", "SEARCH_SITE", {"service": "github", "query": "FastAPI"}),
        ("Search the web for latest AI news", "SEARCH_WEB", {"query": "latest AI news"}),
        ("Search Google for today's AI news", "SEARCH_SITE", {"service": "google", "query": "today's AI news"}),
        ("Search for python tutorials", "SEARCH_WEB", {"query": "python tutorials"}),
        ("Play Believer on Spotify", "PLAY_MEDIA", {"service": "spotify", "query": "Believer"}),
        ("Play some music", "PLAY_MEDIA", {"service": "spotify", "query": None}),
        ("put on some music", "PLAY_MEDIA", {"service": "spotify", "query": None}),
        ("Play songs by A.R. Rahman", "PLAY_MEDIA", {"service": "spotify", "query": "songs by A.R. Rahman"}),
        ("Play a video about machine learning on YouTube", "PLAY_MEDIA", {"service": "youtube", "query": "machine learning"}),
        ("Pause Spotify", "PAUSE_MEDIA", {"service": None}),
        ("Skip the current song", "SKIP_MEDIA", {"service": None}),
        ("take a screenshot", "SCREENSHOT", {}),
        ("scroll down", "SCROLL", {"direction": "down"}),
        ("scroll up", "SCROLL", {"direction": "up"}),
        ("extract the page content", "EXTRACT", {}),
        ("extract the text", "EXTRACT", {}),
        ("click the login button", "CLICK", {"target": "login"}),
        ("type hello into the search box", "TYPE", {"text": "hello", "target": "search box"}),
        ("download this file", "DOWNLOAD", {"requires_confirmation": True}),
        ("Buy this laptop on Amazon", "OPEN_WEBSITE", {"service": "amazon", "requires_confirmation": True}),
        ("Order food from Zomato", "OPEN_WEBSITE", {"service": "zomato", "requires_confirmation": True}),
        ("yes", "CONFIRM_ACTION", {}),
        ("go ahead and do it", "CONFIRM_ACTION", {}),
        ("ok, sure", "CONFIRM_ACTION", {}),
    ],
)
def test_intent_table(message, expected, fields):
    intent = classify_browser_intent(message)
    assert intent is not None, f"{message!r} should classify"
    assert intent.intent == expected, f"{message!r}: {intent.intent} != {expected}"
    for k, v in fields.items():
        assert getattr(intent, k) == v, f"{message!r}: {k}={getattr(intent, k)!r} != {v!r}"


@pytest.mark.parametrize(
    "message",
    [
        "What is the capital of France?",
        "Can you write a poem?",
        "I cant play football today",
        "Tell me about machine learning",
        "thanks for the help",
        "Pause",  # bare media control needs current_service context
        "Resume",
    ],
)
def test_intent_negatives(message):
    assert classify_browser_intent(message) is None, message


@pytest.mark.parametrize(
    "message,service",
    [
        ("Pause", "spotify"),
        ("Resume", "youtube"),
        ("Skip", "spotify"),
        ("next", "youtube"),
    ],
)
def test_bare_media_control_requires_context(message, service):
    intent = classify_browser_intent(message, current_service=service)
    assert intent is not None and intent.service == service


@pytest.mark.parametrize(
    "message",
    [
        ("I should pause and think"),
        ("Let's skip that topic"),
        ("Resume my question"),
    ],
)
def test_media_control_false_positives(message):
    assert classify_browser_intent(message) is None, message


def test_compound_command_priority():
    i1 = classify_browser_intent("Open GitHub and search for FastAPI projects")
    assert i1.intent == "SEARCH_SITE" and i1.service == "github"
    i2 = classify_browser_intent("Open Spotify and play Believer")
    assert i2.intent == "PLAY_MEDIA" and i2.service == "spotify" and i2.query == "Believer"


def test_confirm_does_not_steal_search():
    assert classify_browser_intent("ok google search for python").intent == "SEARCH_SITE"


def test_clean_query_removes_trailing_on():
    i = classify_browser_intent("Play Believer on Spotify")
    assert i.query == "Believer"


# --------------------------------------------------------------------------
# Planner
# --------------------------------------------------------------------------

def _intent(**kw):
    defaults = dict(intent="OPEN_WEBSITE", service=None, query=None, url=None,
                    target=None, text=None, direction=None, requires_confirmation=False)
    defaults.update(kw)
    return bi.BrowserIntent(**defaults)


def test_plan_open_website_minimal():
    plan = bp.build_plan(_intent(intent="OPEN_WEBSITE", service="spotify", url="https://open.spotify.com"))
    assert [s["action"] for s in plan] == ["open_website", "verify_navigation"]


def test_plan_play_media_minimal():
    plan = bp.build_plan(_intent(intent="PLAY_MEDIA", service="spotify", query="Believer"))
    actions = [s["action"] for s in plan]
    assert "play_media" in actions and "verify_playback" in actions
    assert "search_site" in actions and "select_best_match" in actions
    assert plan[0]["action"] == "open_website"


def test_plan_play_media_no_query_skips_search():
    plan = bp.build_plan(_intent(intent="PLAY_MEDIA", service="spotify", query=None))
    actions = [s["action"] for s in plan]
    assert "search_site" not in actions
    assert actions[-1] == "verify_playback"


def test_plan_media_controls():
    for intent in ("PAUSE_MEDIA", "RESUME_MEDIA", "SKIP_MEDIA"):
        plan = bp.build_plan(_intent(intent=intent, service="spotify"))
        actions = [s["action"] for s in plan]
        expected_first = {"PAUSE_MEDIA": "pause_media", "RESUME_MEDIA": "resume_media", "SKIP_MEDIA": "skip_media"}[intent]
        assert actions[0] == expected_first
        assert actions[-1] == "verify_media_state"


def test_plan_search_site_current_page():
    plan = bp.build_plan(_intent(intent="SEARCH_SITE", service=bi.CURRENT_PAGE, query="laptops"))
    actions = [s["action"] for s in plan]
    assert actions[0] == "open_website"  # "using the current page" step
    assert "search_site" in actions and "verify_results" in actions


def test_plan_web_search_delegates():
    plan = bp.build_plan(_intent(intent="SEARCH_WEB", query="ai"))
    assert [s["action"] for s in plan] == ["delegate_web_search"]


def test_plan_max_steps_cap():
    many = bp.build_plan(_intent(intent="PLAY_MEDIA", service="spotify", query="x" * 50))
    assert len(many) <= cfg.MAX_PLAN_STEPS


# --------------------------------------------------------------------------
# Agent (browser mocked)
# --------------------------------------------------------------------------

def _fake_driver():
    d = SimpleNamespace(
        current_url="https://example.com",
        title="Example",
        page_source="<html><body><p>hi</p></body></html>",
        get_screenshot_as_png=lambda: b"\x89PNG\r\n" + b"0" * 100,
        execute_script=lambda *a, **k: None,
    )
    return d


@pytest.fixture
def agent(monkeypatch):
    ag = BrowserAgent()
    driver = _fake_driver()

    async def _run(fn, timeout=None):
        return fn(driver)

    monkeypatch.setattr(ag, "_run", AsyncMock(side_effect=_run))
    return ag


def test_open_website_rejects_non_http(agent):
    intent = _intent(intent="OPEN_WEBSITE", url="file:///etc/passwd")
    events = asyncio.run(agent.run_plan(intent))
    assert events[-1]["success"] is False
    assert "Only http/https" in events[-2]["content"]


def test_open_website_no_url_without_browser(agent):
    intent = _intent(intent="OPEN_WEBSITE", url=None, service=None)
    events = asyncio.run(agent.run_plan(intent))
    assert events[-1]["success"] is False
    assert "don't know which website" in events[-2]["content"].lower()


def test_execute_step_retries_recoverable_then_fails(agent, monkeypatch):
    attempts = []

    async def _flaky_step(intent, action):
        attempts.append(action)
        raise ActionError("boom", recoverable=True, hint="flaky")

    monkeypatch.setattr(agent, "_step_once", AsyncMock(side_effect=_flaky_step))
    monkeypatch.setattr("app.services.browser.agent.asyncio.sleep", AsyncMock())
    with pytest.raises(ActionError):
        asyncio.run(agent._execute_step(_intent(), "open_website"))
    assert len(attempts) == cfg.MAX_ACTION_RETRIES + 1


def test_execute_step_no_retry_on_unrecoverable(agent, monkeypatch):
    attempts = []

    async def _hard_step(intent, action):
        attempts.append(action)
        raise ActionError("nope", recoverable=False)

    monkeypatch.setattr(agent, "_step_once", AsyncMock(side_effect=_hard_step))
    with pytest.raises(ActionError):
        asyncio.run(agent._execute_step(_intent(), "open_website"))
    assert len(attempts) == 1


def test_run_plan_returns_events_and_state(agent):
    events = asyncio.run(agent.run_plan(_intent(intent="SCREENSHOT")))
    types = [e["type"] for e in events]
    assert "image" in types and "done" in types and "content" in types
    done = events[-1]
    assert done["success"] is True
    assert done["browser"]["browser_open"] is False  # no real driver used


def test_pick_best_prefers_title_overlap(agent):
    els = [
        SimpleNamespace(text="Python for beginners", get_attribute=lambda k: None),
        SimpleNamespace(text="FastAPI projects", get_attribute=lambda k: None),
        SimpleNamespace(text="Something unrelated", get_attribute=lambda k: None),
    ]
    d = SimpleNamespace(find_elements=lambda by, css: els)
    best = agent._pick_best(d, "a", {"fastapi", "projects"})
    assert best is els[1]


def test_media_control_keyboard_fallback(agent, monkeypatch):
    from selenium.common.exceptions import TimeoutException

    def _clickable(driver, cands, timeout):
        raise TimeoutException("no button")

    monkeypatch.setattr("app.services.browser.agent._clickable_candidates", _clickable)

    body = SimpleNamespace(send_keys=lambda k: None)
    monkeypatch.setattr("app.services.browser.agent._visible_candidates", lambda d, cands, t: body)
    res = agent._media_control(_fake_driver(), "youtube", "pause")
    assert res["used"] == "shortcut"


def test_media_control_button_path(agent, monkeypatch):
    btn = SimpleNamespace(click=lambda: None)
    monkeypatch.setattr(
        "app.services.browser.agent._clickable_candidates",
        lambda d, cands, t: btn,
    )
    res = agent._media_control(_fake_driver(), "youtube", "pause")
    assert res["used"] == "button"


def test_screenshot_data_uri(agent):
    monkeypatch = pytest.MonkeyPatch()

    d = SimpleNamespace(get_screenshot_as_png=lambda: b"\x89PNG\r\n" + b"0" * 100)
    res = agent._screenshot(d)
    assert res.startswith("data:image/png;base64,")


def test_search_input_candidates_are_site_aware(agent):
    agent.current_url = "https://www.youtube.com/watch?v=x"
    cands = agent._search_input_candidates(_fake_driver())
    css = [v for by, v in cands]
    assert 'input#search' in css  # youtube first choice


def test_detect_service():
    assert BrowserAgent._detect_service("https://open.spotify.com/search") == "spotify"
    assert BrowserAgent._detect_service("https://youtu.be/abc") == "youtube"
    assert BrowserAgent._detect_service("https://github.com") == "github"
    assert BrowserAgent._detect_service("https://example.com") is None


def test_state_contains_no_secrets(agent):
    st = agent.state()
    assert set(st) == {"browser_open", "current_url", "current_title", "active_service", "persistent_session"}


# --------------------------------------------------------------------------
# Service (confirmation gating + delegation)
# --------------------------------------------------------------------------

@pytest.fixture
def service(monkeypatch):
    svc = bsvc.BrowserService()

    async def _noop_plan(intent):
        return [
            {"type": "browser_status", "content": "did something"},
            {"type": "content", "content": "Done."},
            {"type": "done", "success": True},
        ]

    monkeypatch.setattr(bsvc.browser_agent, "run_plan", AsyncMock(side_effect=_noop_plan))
    return svc


async def _collect(svc, message, user="u1"):
    return [ev async for ev in svc.stream_for_message(message, user_id=user)]


@pytest.mark.asyncio
async def test_service_delegates_web_search(service):
    events = await _collect(service, "Search the web for latest AI news")
    assert any(e["type"] == "delegate_web_search" for e in events)
    assert service._pending == {}


@pytest.mark.asyncio
async def test_service_queues_consequential_until_confirmed(service):
    events = await _collect(service, "Buy this laptop on Amazon", user="u2")
    types = [e["type"] for e in events]
    assert "browser_status" in types and "done" in types
    assert events[-1]["awaiting_confirmation"] is True
    assert service.has_pending("u2")
    # the run_plan mock must NOT have been called yet
    assert not bsvc.browser_agent.run_plan.called


@pytest.mark.asyncio
async def test_service_confirms_then_executes(service):
    await _collect(service, "Buy this laptop on Amazon", user="u3")
    events = await _collect(service, "yes", user="u3")
    assert any("did something" in e["content"] for e in events if e["type"] == "browser_status")
    assert not service.has_pending("u3")


@pytest.mark.asyncio
async def test_service_confirm_without_pending(service):
    events = await _collect(service, "yes", user="u4")
    assert any("pending action" in e["content"] for e in events if e["type"] == "browser_status")


@pytest.mark.asyncio
async def test_service_other_browser_intent_replaces_pending(service):
    await _collect(service, "Buy this laptop on Amazon", user="u5")
    assert service.pending_description("u5") is not None
    # a harmless screenshot does NOT cancel a queued consequential action
    await _collect(service, "take a screenshot", user="u5")
    assert service.has_pending("u5") is True
    # a new consequential intent replaces the pending one
    await _collect(service, "Delete my account from Twitter", user="u5")
    assert service.has_pending("u5") is True
    assert "twitter" in service.pending_description("u5")


def test_service_disabled_by_config(monkeypatch):
    monkeypatch.setattr(cfg, "BROWSER_ENABLED", False)
    assert bsvc.BrowserService().detect("Open Spotify") is None


def test_service_detect_uses_active_service(monkeypatch):
    monkeypatch.setattr(bsvc.browser_agent, "active_service", "spotify")
    intent = bsvc.BrowserService().detect("Pause")
    assert intent is not None and intent.intent == "PAUSE_MEDIA"
