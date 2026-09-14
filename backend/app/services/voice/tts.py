"""Offline TTS (Windows SAPI5 via pyttsx3) for spoken automation responses.

Never runs on cloud (gated by callers + settings). Speak() is thread-safe and
never blocks the caller meaningfully — pyttsx3 runs the engine in its own
message loop inside a worker thread.
"""

import logging
import threading

from app.config import settings

logger = logging.getLogger("hsbot.voice.tts")

_engine_lock = threading.Lock()
_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        import pyttsx3
        _engine = pyttsx3.init()
        try:
            _engine.setProperty("rate", 175)
            _engine.setProperty("volume", 1.0)
        except Exception:
            pass
    return _engine


def speak(text: str) -> bool:
    """Speak text aloud on the local machine. Returns False if unavailable."""
    if not text or not settings.voice_response_enabled or settings.is_cloud:
        return False
    try:
        with _engine_lock:
            engine = _get_engine()
        engine.say(text)
        engine.runAndWait()
        return True
    except Exception as e:
        logger.warning(f"TTS failed: {e}")
        return False


def speak_async(text: str) -> None:
    """Speak in a background thread (never blocks the caller)."""
    if not text or not settings.voice_response_enabled or settings.is_cloud:
        return
    threading.Thread(target=speak, args=(text,), daemon=True).start()
