"""Voice automation service module for HSBot."""

from .listener import VoiceListener
from .vad import VoiceActivityDetector
from .wake_word import WakeWordDetector
from .speaker_verification import SpeakerVerifier

__all__ = [
    "VoiceListener",
    "VoiceActivityDetector",
    "WakeWordDetector",
    "SpeakerVerifier",
]
