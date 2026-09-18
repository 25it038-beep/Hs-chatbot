"""
Language Configuration for HSBot Live Voice.
Centralizes language identifiers, speech model specifications, and routing rules.
"""

from typing import Dict, Any

TAMIL_LANGUAGE_CODE = "ta-IN"
ENGLISH_LANGUAGE_CODE = "en-US"


class LanguageConfig:
    SUPPORTED_LANGUAGES = {
        "en": {
            "code": "en",
            "name": "English",
            "native_name": "English",
            "locale": ENGLISH_LANGUAGE_CODE,
            "speech_locale": ENGLISH_LANGUAGE_CODE,
            "label": "English",
            "default": True,
            "asr_provider": "nvidia_nvcf_parakeet",
            "asr_model": "parakeet-tdt-0.6b-en-US-asr-offline",
            "tts_provider": "nvidia_nvcf_chatterbox",
            "tts_voice": "Chatterbox-Multilingual",
            "llm_system_instruction": None,
            "voices": [
                {"id": "Chatterbox-Multilingual", "name": "Chatterbox Multilingual", "default": True},
                {"id": "English-US.Female-1", "name": "English US Female", "default": False},
                {"id": "English-US.Male-1", "name": "English US Male", "default": False},
            ],
        },
        "ta": {
            "code": "ta",
            "name": "Tamil",
            "native_name": "தமிழ்",
            "locale": TAMIL_LANGUAGE_CODE,
            "speech_locale": TAMIL_LANGUAGE_CODE,
            "label": "Tamil",
            "default": False,
            "asr_provider": "nvidia_nvcf_whisper_or_riva",
            "asr_model": "whisper-large-v3",
            "tts_provider": "nvidia_riva_or_chatterbox",
            "tts_voice": "ta-IN-Standard",
            "llm_system_instruction": (
                "You are speaking with the user in Tamil.\n"
                "Respond naturally in Tamil.\n"
                "Use clear conversational Tamil.\n"
                "Preserve technical terminology in English when that is more natural "
                "(e.g., Python, FastAPI, React, JavaScript, API, database, GitHub, Docker, NVIDIA).\n"
                "Do not translate programming keywords unnecessarily.\n"
                "If the user explicitly asks for English, respond in English."
            ),
            "voices": [
                {"id": "ta-IN-Standard", "name": "Tamil Natural", "default": True},
                {"id": "ta-IN-Female", "name": "Tamil Female", "default": False},
                {"id": "ta-IN-Male", "name": "Tamil Male", "default": False},
            ],
        },
    }

    @classmethod
    def get_config(cls, language_code: str) -> Dict[str, Any]:
        normalized = (language_code or "en").lower().strip()
        if normalized in ("ta", "ta-in", "tamil"):
            return cls.SUPPORTED_LANGUAGES["ta"]
        return cls.SUPPORTED_LANGUAGES["en"]

    @classmethod
    def get_supported_languages(cls) -> Dict[str, Dict[str, Any]]:
        return cls.SUPPORTED_LANGUAGES

    @classmethod
    def get_supported_voices(cls, language_code: str = "en") -> list:
        cfg = cls.get_config(language_code)
        return cfg.get("voices", [])

    @classmethod
    def is_tamil(cls, language_code: str) -> bool:
        normalized = (language_code or "").lower().strip()
        return normalized in ("ta", "ta-in", "tamil", TAMIL_LANGUAGE_CODE.lower())

