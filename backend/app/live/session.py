"""
Live Voice Session Orchestrator
Coordinates WebSocket connection, audio chunking, NVIDIA ASR, LLM streaming, and NVIDIA TTS.
"""

import asyncio
import base64
import json
import logging
import time
from typing import Dict, Any, List, Optional
from fastapi import WebSocket, WebSocketDisconnect

from app.live.turn_manager import LiveTurnManager
from app.live.asr import live_asr
from app.live.tts import live_tts
from app.live.llm import live_llm

logger = logging.getLogger("hsbot.live.session")


class LiveVoiceSession:
    def __init__(self, session_id: str, websocket: WebSocket):
        self.session_id = session_id
        self.websocket = websocket
        self.turn_manager = LiveTurnManager()
        self.audio_buffer = bytearray()
        self.conversation_history: List[Dict[str, str]] = []
        self.active_llm_task: Optional[asyncio.Task] = None
        self.active_tts_task: Optional[asyncio.Task] = None
        self.voice = "Chatterbox-Multilingual"
        self.sample_rate = 16000
        self.is_active = True
        self.last_audio_time = time.time()
        self.silence_threshold_s = 0.75
        self.silence_monitor_task: Optional[asyncio.Task] = None

    async def start(self):
        """Main WebSocket loop for session."""
        self.turn_manager.transition_to("LISTENING", "Session started")
        await self.send_status("LISTENING", "Connected to NVIDIA live engine")

        # Start silence detector loop
        self.silence_monitor_task = asyncio.create_task(self._monitor_silence())

        try:
            while self.is_active:
                raw_text = await self.websocket.receive_text()
                await self.handle_message(raw_text)
        except WebSocketDisconnect:
            logger.info(f"Live session {self.session_id} disconnected by client")
        except Exception as e:
            logger.error(f"Live session {self.session_id} error: {e}")
        finally:
            await self.cleanup()

    async def handle_message(self, raw_text: str):
        try:
            msg = json.loads(raw_text)
        except Exception:
            return

        msg_type = msg.get("type")

        if msg_type == "ping":
            await self.websocket.send_json({
                "type": "pong",
                "timestamp": msg.get("timestamp", int(time.time() * 1000)),
            })

        elif msg_type == "config":
            cfg = msg.get("config", {})
            if "voice" in cfg:
                self.voice = cfg["voice"]
            if "sampleRate" in cfg:
                self.sample_rate = cfg["sampleRate"]
            logger.info(f"Updated live config: voice={self.voice}, sampleRate={self.sample_rate}")

        elif msg_type == "interrupt":
            await self.interrupt()

        elif msg_type == "audio":
            data_b64 = msg.get("data", "")
            if data_b64:
                try:
                    chunk = base64.b64decode(data_b64)
                    self.audio_buffer.extend(chunk)
                    self.last_audio_time = time.time()

                    # If barge-in while speaking
                    if self.turn_manager.get_state() in ("SPEAKING", "PROCESSING"):
                        await self.interrupt()

                except Exception as e:
                    logger.error(f"Error decoding audio chunk: {e}")

    async def interrupt(self):
        """Immediately halts active LLM streaming and TTS generation."""
        logger.info(f"Interrupting live session {self.session_id}")
        self.turn_manager.handle_barge_in()

        if self.active_llm_task and not self.active_llm_task.done():
            self.active_llm_task.cancel()

        if self.active_tts_task and not self.active_tts_task.done():
            self.active_tts_task.cancel()

        self.turn_manager.transition_to("LISTENING", "Interrupted by user")
        await self.send_status("LISTENING", "Listening for next turn")

    async def _monitor_silence(self):
        """Monitors audio buffer and triggers ASR after pause in user speech."""
        while self.is_active:
            await asyncio.sleep(0.15)
            if not self.audio_buffer:
                continue

            idle_duration = time.time() - self.last_audio_time
            # If buffer has accumulated enough audio and user stopped talking
            if idle_duration >= self.silence_threshold_s and len(self.audio_buffer) > 4000:
                pcm_bytes = bytes(self.audio_buffer)
                self.audio_buffer.clear()
                asyncio.create_task(self._process_utterance(pcm_bytes))

    async def _process_utterance(self, pcm_bytes: bytes):
        """Pipelines: ASR -> LLM -> TTS."""
        if self.turn_manager.get_state() not in ("LISTENING", "IDLE"):
            return

        self.turn_manager.transition_to("PROCESSING", "Transcribing speech")
        await self.send_status("PROCESSING", "Transcribing speech with NVIDIA ASR...")

        # 1. NVIDIA ASR
        transcript = await live_asr.transcribe_pcm(pcm_bytes, self.sample_rate)
        if not transcript:
            self.turn_manager.transition_to("LISTENING", "No speech detected")
            await self.send_status("LISTENING", "Listening...")
            return

        # Broadcast final user transcript
        await self.websocket.send_json({
            "type": "transcript",
            "role": "user",
            "text": transcript,
            "isFinal": True,
        })

        # Record in history
        self.conversation_history.append({"role": "user", "content": transcript})

        # 2. NVIDIA LLM Streaming
        accumulated_text = ""
        try:
            async for token in live_llm.stream_reply(transcript, self.conversation_history):
                accumulated_text += token
                await self.websocket.send_json({
                    "type": "llm_chunk",
                    "text": token,
                })
        except asyncio.CancelledError:
            logger.info("LLM generation cancelled by barge-in")
            return
        except Exception as e:
            logger.error(f"Error streaming LLM tokens: {e}")
            accumulated_text = "I encountered an issue processing that."

        response_text = accumulated_text.strip()
        if not response_text:
            self.turn_manager.transition_to("LISTENING", "Empty LLM reply")
            return

        # Broadcast assistant final transcript
        await self.websocket.send_json({
            "type": "transcript",
            "role": "assistant",
            "text": response_text,
            "isFinal": True,
        })
        self.conversation_history.append({"role": "assistant", "content": response_text})

        # 3. NVIDIA TTS
        self.turn_manager.transition_to("SPEAKING", "Synthesizing voice response")
        await self.send_status("SPEAKING", "Synthesizing NVIDIA voice...")

        try:
            tts_res = await live_tts.synthesize(response_text, voice=self.voice)
            if tts_res and tts_res.get("audio"):
                await self.websocket.send_json({
                    "type": "audio_chunk",
                    "audio": tts_res["audio"],
                    "sampleRate": tts_res.get("sampleRate", 24000),
                    "index": 0,
                })
            else:
                logger.warning("No audio generated from NVIDIA TTS")
                self.turn_manager.transition_to("LISTENING", "TTS returned no audio")
                await self.send_status("LISTENING", "Ready")
        except asyncio.CancelledError:
            logger.info("TTS generation cancelled by barge-in")
        except Exception as e:
            logger.error(f"TTS error: {e}")
            self.turn_manager.transition_to("LISTENING", "TTS error")

    async def send_status(self, state: str, message: str = ""):
        try:
            await self.websocket.send_json({
                "type": "status",
                "state": state,
                "message": message,
            })
        except Exception:
            pass

    async def cleanup(self):
        self.is_active = False
        if self.silence_monitor_task and not self.silence_monitor_task.done():
            self.silence_monitor_task.cancel()
        if self.active_llm_task and not self.active_llm_task.done():
            self.active_llm_task.cancel()
        if self.active_tts_task and not self.active_tts_task.done():
            self.active_tts_task.cancel()
        self.turn_manager.reset()
        logger.info(f"Cleaned up live session {self.session_id}")
