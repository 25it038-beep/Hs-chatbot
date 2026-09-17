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
            "locale": ENGLISH_LANGUAGE_CODE,
            "label": "English",
            "default": True,
            "asr_provider": "nvidia_nvcf_parakeet",
            "asr_model": "parakeet-tdt-0.6b-en-US-asr-offline",
            "tts_provider": "nvidia_nvcf_chatterbox",
            "tts_voice": "Chatterbox-Multilingual",
            "llm_system_instruction": None,
        },
        "ta": {
            "code": "ta",
            "locale": TAMIL_LANGUAGE_CODE,
            "label": "Tamil",
            "default": False,
            "asr_provider": "nvidia_riva_custom",
            "asr_model": "riva-tamil-conformer-asr",
            "tts_provider": "nvidia_riva_custom",
            "tts_voice": "ta-IN-Standard",
            "llm_system_instruction": (
                "Respond naturally in Tamil. "
                "Use Tamil script unless the user explicitly asks for another language. "
                "Do not translate Tamil into English unless requested."
            ),
        },
    }

    @classmethod
    def get_config(cls, language_code: str) -> Dict[str, Any]:
        normalized = (language_code or "en").lower().strip()
        if normalized in ("ta", "ta-in", "tamil"):
            return cls.SUPPORTED_LANGUAGES["ta"]
        return cls.SUPPORTED_LANGUAGES["en"]

    @classmethod
    def is_tamil(cls, language_code: str) -> bool:
        normalized = (language_code or "").lower().strip()
        return normalized in ("ta", "ta-in", "tamil", TAMIL_LANGUAGE_CODE.lower())
