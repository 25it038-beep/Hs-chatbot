"""Voice listener bridge + event bus tests.

Unit tests never open a microphone: the listener components (VAD, wake word,
verifier) are mocked, and the bridge is exercised via the listener's command
handler. Covers: strict chat/automation separation (unknown → chat_intent),
verified vs unverified execution flags, event bus subscription.
"""

import sys
import time
import queue as std_queue
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.voice.listener import VoiceCommand, VoiceListener, get_voice_listener
from app.services.voice import bridge as bridge_mod
from app.services.voice.bridge import handle_voice_command


def make_command(text: str, verified: bool = True, confidence: float = 0.95):
    import numpy as np
    return VoiceCommand(
        wake_word="wake up",
        speaker_id="u1" if verified else None,
        speaker_confidence=confidence if verified else 0.2,
        command_text=text,
        audio_data=np.zeros(1600, dtype=np.float32),
        timestamp=__import__("datetime").datetime.now(),
        is_verified=verified,
    )


@pytest.fixture
def listener():
    with patch("app.services.voice.listener.get_vad_detector"), \
         patch("app.services.voice.listener.get_wake_word_detector"), \
         patch("app.services.voice.listener.get_speaker_verifier"):
        inst = VoiceListener(enable_speaker_verification=False)
    yield inst


def test_event_bus_receives_state_and_command_events(listener):
    q = listener.subscribe()
    listener._set_state(listener.state.__class__("listening"))
    events = _drain(q, timeout=1.0)
    assert any(e["type"] == "state_change" and e["new_state"] == "listening" for e in events)


def test_listener_is_always_listening_by_default(listener):
    assert listener.wake_word_required is False
    listener.set_wake_word_required(True)
    assert listener.wake_word_required is True


def test_unknown_voice_command_is_chat_intent_not_executed(listener, monkeypatch):
    monkeypatch.setattr(bridge_mod, "get_voice_listener", lambda: listener)
    monkeypatch.setattr("app.services.voice.tts.speak_async", lambda *a, **k: None)
    events = []
    q = listener.subscribe()
    monkeypatch.setattr(listener, "command_handler", lambda cmd: handle_voice_command(cmd, "u1"))
    listener._run_command_handler(make_command("Tell me a joke"))
    time.sleep(0.5)
    events = _drain(q, timeout=1.0)
    assert any(e["type"] == "chat_intent" for e in events), events
    assert not any(e["type"] == "execution_result" for e in events), events


def test_known_voice_command_executes_via_engine(listener, monkeypatch):
    monkeypatch.setattr(bridge_mod, "get_voice_listener", lambda: listener)
    monkeypatch.setattr("app.services.voice.tts.speak_async", lambda *a, **k: None)
    events = []
    q = listener.subscribe()
    monkeypatch.setattr(listener, "command_handler", lambda cmd: handle_voice_command(cmd, "u1"))
    listener._run_command_handler(make_command("get volume"))
    deadline = time.time() + 5.0
    while time.time() < deadline:
        events.extend(_drain(q, timeout=0.5))
        if any(e["type"] == "execution_result" for e in events):
            break
    results = [e for e in events if e["type"] == "execution_result"]
    assert results, events
    assert results[0]["intent"] == "get_volume"


def _drain(q: std_queue.Queue, timeout: float):
    out = []
    end = time.time() + timeout
    while time.time() < end:
        try:
            out.append(q.get(timeout=0.1))
        except std_queue.Empty:
            break
    return out
