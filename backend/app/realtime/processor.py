"""Real-time conversation processor for live voice mode.

Integrates fast live intent routing (TIME, WEATHER, LOCATION),
multi-turn memory tracking, and streaming generation via NVIDIA NIM / LLMs.
"""

from __future__ import annotations

import asyncio
import time
from typing import AsyncGenerator, Dict, Any, Optional
from loguru import logger

from app.realtime.session import LiveSession
from app.services.live_router import classify_live_intent
from app.services.time_service import (
    get_current_time as time_now,
    get_time_for_timezone,
    get_time_for_location,
)
from app.services.tools.weather_tool import WeatherService
from app.services.nvidia.chat import NvidiaChatProvider


# System prompt customized for conversational real-time speech (concise, direct, spoken-friendly)
LIVE_VOICE_SYSTEM_PROMPT = """You are HSBot in Live Voice Mode.
You are engaged in a natural, real-time spoken voice conversation with the user.

CRITICAL VOICE INSTRUCTIONS:
1. Speak naturally, concisely, and conversationally. Keep answers short (1 to 3 sentences unless asked for detail).
2. Do NOT use markdown tables, complex code blocks, bulleted lists with deep indentation, or citations like [1], as this will be read aloud by TTS.
3. Be friendly, direct, and helpful. Answer immediately.
4. If given tool output, use the verified information directly.
5. If the user speaks in Tamil or Hindi, reply fluently and naturally in that language.
"""


class LiveConversationProcessor:
    def __init__(self):
        self.weather_service = WeatherService()
        self.chat_provider = NvidiaChatProvider()

    async def execute_live_tool(
        self, intent: str, location: Optional[str], session: LiveSession
    ) -> Optional[Dict[str, Any]]:
        """Run fast deterministic tools for time, timezone, weather, location."""
        try:
            if intent in ("TIME", "TIMEZONE"):
                if intent == "TIME":
                    if session.timezone and session.timezone != "UTC":
                        data = get_time_for_timezone(session.timezone)
                    else:
                        data = time_now()
                    spoken = f"The time is {data['time']} on {data['day']}, {data['date']}."
                    return {"tool": "TIME", "spoken": spoken, "data": data}
                else:
                    target_loc = location or session.location or "UTC"
                    data = await get_time_for_location(target_loc)
                    spoken = f"The current time in {target_loc} is {data['time']} on {data['day']}."
                    return {"tool": "TIMEZONE", "spoken": spoken, "data": data}

            elif intent in ("WEATHER_CURRENT", "WEATHER_FORECAST"):
                target_loc = location or session.location or "Chennai"
                days = 3 if intent == "WEATHER_FORECAST" else 1
                try:
                    weather_data = await self.weather_service.get_weather_by_city(target_loc, forecast_days=days)
                    cur = weather_data.get("current", {})
                    temp = cur.get("temperature")
                    cond = cur.get("condition", "clear")
                    rain = cur.get("rain_probability", 0)
                    loc_name = weather_data.get("location", target_loc)
                    
                    if intent == "WEATHER_CURRENT":
                        spoken = f"In {loc_name}, it's currently {temp} degrees Celsius with {cond}."
                        if rain and rain > 20:
                            spoken += f" There is a {rain}% chance of rain."
                    else:
                        spoken = f"For {loc_name}, expect {cond} with temperatures around {temp} degrees."
                        if rain and rain > 20:
                            spoken += f" Rain probability is around {rain}%."

                    # Also update session location memory so followups work smoothly
                    session.location = target_loc
                    return {"tool": intent, "spoken": spoken, "data": weather_data}
                except Exception as e:
                    logger.warning("Weather tool lookup failed for {}: {}", target_loc, e)
                    return None

            elif intent == "LOCATION":
                loc = session.location or "an unspecified location"
                tz = session.timezone or "UTC"
                spoken = f"Based on your session settings, you are located in {loc} with timezone {tz}."
                return {"tool": "LOCATION", "spoken": spoken, "data": {"location": loc, "timezone": tz}}

        except Exception as e:
            logger.error("Error executing live tool {}: {}", intent, e)
            return None

        return None

    async def stream_utterance_response(
        self,
        session: LiveSession,
        user_text: str,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Process user utterance, yielding events:
        - {"type": "status", "status": "processing"}
        - {"type": "tool_executed", "tool": ..., "spoken": ...}
        - {"type": "ai_text_chunk", "chunk": "..."}
        - {"type": "ai_text_done", "full_text": "..."}
        - {"type": "status", "status": "speaking"}
        """
        session.touch()
        session.set_status("processing")
        session.abort_requested = False
        session.current_assistant_text = ""
        session.add_user_message(user_text)

        yield {"type": "status", "status": "processing"}

        # 1. Fast tool classification
        intent, location = classify_live_intent(user_text)
        logger.info("Live utterance intent: {} (location: {})", intent, location)

        if intent != "NORMAL":
            tool_res = await self.execute_live_tool(intent, location, session)
            if tool_res and tool_res.get("spoken"):
                spoken_text = tool_res["spoken"]
                session.current_assistant_text = spoken_text
                yield {
                    "type": "tool_executed",
                    "tool": tool_res["tool"],
                    "data": tool_res.get("data"),
                }
                yield {"type": "status", "status": "speaking"}
                # Emit chunks for spoken speech
                session.set_status("speaking")
                yield {"type": "ai_text_chunk", "chunk": spoken_text}
                yield {"type": "ai_text_done", "full_text": spoken_text}
                session.add_assistant_message(spoken_text, tool_used=tool_res["tool"])
                session.set_status("listening")
                yield {"type": "status", "status": "listening"}
                return

        # 2. Multi-turn AI generation with streaming
        messages = [{"role": "system", "content": LIVE_VOICE_SYSTEM_PROMPT}]
        if session.language == "ta":
            messages[0]["content"] += "\nLanguage: Reply in natural Tamil script or spoken Tamil."
        elif session.language == "hi":
            messages[0]["content"] += "\nLanguage: Reply in natural Hindi script or spoken Hindi."

        if session.location:
            messages[0]["content"] += f"\nUser location context: {session.location}."
        if session.timezone:
            messages[0]["content"] += f"\nUser timezone context: {session.timezone}."

        recent_history = session.get_recent_history_prompt(max_turns=6)
        messages.extend(recent_history)

        yield {"type": "status", "status": "speaking"}
        session.set_status("speaking")

        accumulated = []
        try:
            # Stream tokens from Nvidia NIM / chat provider
            async for chunk in self.chat_provider.generate_stream(
                messages=messages,
                model="llama-3.1-70b",
                temperature=0.7,
                max_tokens=250,
            ):
                if session.abort_requested:
                    logger.info("Session {} aborted during stream", session.session_id)
                    break

                if chunk.type == "content" and chunk.content:
                    accumulated.append(chunk.content)
                    session.current_assistant_text = "".join(accumulated)
                    yield {"type": "ai_text_chunk", "chunk": chunk.content}
                    # Minimal pause to let event loop handle incoming websocket messages (like interrupts)
                    await asyncio.sleep(0.01)

            full_text = "".join(accumulated).strip()
            if not session.abort_requested and full_text:
                session.add_assistant_message(full_text)
                yield {"type": "ai_text_done", "full_text": full_text}

        except asyncio.CancelledError:
            logger.info("Stream utterance cancelled for session {}", session.session_id)
            raise
        except Exception as e:
            logger.error("Error generating live AI response: {}", e)
            if not accumulated:
                fallback_msg = "I understood your request, but had trouble reaching the voice engine. Could you please repeat that?"
                yield {"type": "ai_text_chunk", "chunk": fallback_msg}
                yield {"type": "ai_text_done", "full_text": fallback_msg}
                session.add_assistant_message(fallback_msg)
        finally:
            if not session.abort_requested:
                session.set_status("listening")
                yield {"type": "status", "status": "listening"}


live_conversation_processor = LiveConversationProcessor()
