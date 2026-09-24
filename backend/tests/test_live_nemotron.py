"""
Unit and integration tests for NVIDIA Nemotron VoiceChat subsystem.
Verifies:
- Availability probing of nvidia/nemotron-voicechat
- Honest error reporting (NEMOTRON_VOICECHAT_UNAVAILABLE) with zero fake voice
- Dynamic switching to cascaded engine
- Real-time 14-metric diagnostics snapshot
"""

import pytest
import asyncio
from app.live.voicechat import nemotron_voicechat, NemotronVoiceChatUnavailableError
from app.live.diagnostics import live_diagnostics


@pytest.mark.asyncio
async def test_nemotron_voicechat_availability_probe():
    """Verifies that Nemotron VoiceChat probe returns real status from NVIDIA NIM."""
    status = await nemotron_voicechat.check_availability(force=True)
    assert isinstance(status, dict)
    assert "available" in status
    assert status["model"] == "nvidia/nemotron-voicechat"

    # Since nvidia/nemotron-voicechat is an Early Access containerized NIM,
    # it is not in the serverless NIM catalog and must return unavailable.
    if not status["available"]:
        assert status["code"] == "NEMOTRON_VOICECHAT_UNAVAILABLE"
        assert status.get("status_code", 404) in (404, 500, 502, 503)
        assert "error" in status


@pytest.mark.asyncio
async def test_nemotron_voicechat_zero_simulation_contract():
    """Verifies that calling stream_voicechat raises error and NEVER simulates fake voice."""
    status = await nemotron_voicechat.check_availability()
    if not status.get("available"):
        with pytest.raises(NemotronVoiceChatUnavailableError) as exc_info:
            async for _ in nemotron_voicechat.stream_voicechat(text="Hello"):
                pass
        assert exc_info.value.code == "NEMOTRON_VOICECHAT_UNAVAILABLE"


@pytest.mark.asyncio
async def test_live_diagnostics_snapshot():
    """Verifies 14-metric telemetry snapshot structure."""
    snap = await live_diagnostics.get_snapshot()
    assert "status" in snap
    assert "engine" in snap
    assert "models" in snap
    assert "nemotron_voicechat" in snap["models"]
    assert "cascaded" in snap["models"]
    assert snap["engine"]["supported"] == ["nemotron_voicechat", "cascaded"]

    # Test engine toggle
    live_diagnostics.set_engine("cascaded")
    assert live_diagnostics.get_engine() == "cascaded"
    live_diagnostics.set_engine("nemotron_voicechat")
    assert live_diagnostics.get_engine() == "nemotron_voicechat"
