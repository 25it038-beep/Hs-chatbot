"""Bridge between the voice listener and the automation engine.

Voice commands are routed by strict separation rules:
- Automation intents (intent_detector) → automation_engine.process_command
  with the speaker's voice_verified flag (trusted voice skips MEDIUM confirm).
- Everything else (chat, questions) → emitted as a `chat_intent` event for the
  frontend to pass into chat — never executed on the OS.
"""

import asyncio
import logging
import threading
from typing import Optional

from .listener import VoiceCommand, get_voice_listener

logger = logging.getLogger("hsbot.voice.bridge")

_loop_ref: Optional[asyncio.AbstractEventLoop] = None


def set_loop(loop: asyncio.AbstractEventLoop):
    """Remember the main asyncio loop so listener-thread code can schedule into it."""
    global _loop_ref
    _loop_ref = loop


def handle_voice_command(command: VoiceCommand, user_id: str = "default_user_id") -> None:
    """Route a detected voice command (runs in the listener thread)."""
    try:
        from app.services.automation.intent_detector import intent_detector
        from app.services.automation.engine import automation_engine

        intent = intent_detector.detect_intent(command.command_text)
        if intent.intent.value == "unknown":
            listener = get_voice_listener()
            listener._emit({
                "type": "chat_intent",
                "command_text": command.command_text,
                "timestamp": command.timestamp.isoformat(),
            })
            logger.info(f"Voice command is chat intent (not executed): {command.command_text}")
            return

        verified = command.is_verified and command.speaker_confidence >= 0.85

        def _run():
            loop = asyncio.new_event_loop()
            try:
                response = loop.run_until_complete(
                    automation_engine.process_command(
                        command.command_text, user_id, voice_verified=verified
                    )
                )
                listener = get_voice_listener()
                listener._emit({
                    "type": "execution_result",
                    "command_text": command.command_text,
                    "intent": intent.intent.value,
                    "success": response.success,
                    "message": response.message,
                    "action_id": response.action_id,
                    "requires_confirmation": response.requires_confirmation,
                    "options": response.options,
                    "confirmation_prompt": response.confirmation_prompt,
                    "spoken": response.spoken,
                    "timestamp": command.timestamp.isoformat(),
                })
                # Spoken feedback for voice-driven automation
                try:
                    from app.services.voice.tts import speak_async
                    if response.spoken and not response.requires_confirmation:
                        speak_async(response.spoken)
                except Exception as e:
                    logger.warning(f"TTS feedback failed: {e}")
            except Exception as e:
                logger.error(f"Voice command execution failed: {e}", exc_info=True)
            finally:
                loop.close()

        threading.Thread(target=_run, daemon=True).start()
    except Exception as e:
        logger.error(f"Error routing voice command: {e}", exc_info=True)


def wire_voice_bridge(user_id: str = "default_user_id") -> None:
    """Attach the bridge to the voice listener singleton."""
    listener = get_voice_listener()
    listener.set_command_handler(lambda cmd: handle_voice_command(cmd, user_id))
