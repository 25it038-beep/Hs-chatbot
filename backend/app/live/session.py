"""
Live Voice Session Orchestrator
Coordinates WebSocket connection, audio chunking, NVIDIA ASR, streaming LLM,
and streaming NVIDIA TTS in a fully overlapped, asynchronous pipeline.
"""

import asyncio
import base64
import json
import logging
import re
import time
from typing import Dict, Any, List, Optional
from fastapi import WebSocket, WebSocketDisconnect

from app.live.turn_manager import LiveTurnManager
from app.live.asr import live_asr
from app.live.tts import live_tts
from app.live.llm import live_llm

logger = logging.getLogger("hsbot.live.session")

SENTENCE_SPLIT_REGEX = re.compile(r"^(.*?[.!?\n])\s*(.*)$", re.DOTALL)
CLAUSE_SPLIT_REGEX = re.compile(r"^(.*?[,;:])\s*(.*)$", re.DOTALL)


class LiveVoiceSession:
    def __init__(self, session_id: str, websocket: WebSocket):
        self.session_id = session_id
        self.websocket = websocket
        self.turn_manager = LiveTurnManager()
        self.audio_buffer = bytearray()
        self.conversation_history: List[Dict[str, str]] = []
        self.voice = "Chatterbox-Multilingual"
        self.sample_rate = 16000
        self.is_active = True
        self.last_audio_time = time.time()
        self.silence_threshold_s = 0.65
        self.silence_monitor_task: Optional[asyncio.Task] = None

        # Turn concurrency management
        self._turn_in_progress = False
        self._llm_task: Optional[asyncio.Task] = None
        self._tts_task: Optional[asyncio.Task] = None
        self._tts_queue: Optional[asyncio.Queue] = None
        self._t_asr_final = 0.0
        self._t_llm_first = 0.0
        self._first_audio_sent = False

    async def start(self):
        """Main WebSocket loop for session."""
        self.turn_manager.transition_to("LISTENING", "Session started")
        await self.send_status("LISTENING", "Connected to NVIDIA live engine")

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

        elif msg_type == "user_speech":
            # Direct client-side speech transcript (fast path)
            text = (msg.get("text") or "").strip()
            if text and not self._turn_in_progress:
                self.audio_buffer.clear()
                asyncio.create_task(self.execute_turn(text=text))

        elif msg_type == "commit_turn":
            # Explicit speech completion
            if self.audio_buffer and not self._turn_in_progress:
                pcm_bytes = bytes(self.audio_buffer)
                self.audio_buffer.clear()
                asyncio.create_task(self.execute_turn(pcm_bytes=pcm_bytes))

        elif msg_type == "audio":
            data_b64 = msg.get("data", "")
            if data_b64:
                try:
                    chunk = base64.b64decode(data_b64)
                    self.audio_buffer.extend(chunk)
                    self.last_audio_time = time.time()

                    # Barge-in check: if AI is speaking or thinking and incoming audio is substantial
                    if self.turn_manager.get_state() in ("SPEAKING", "PROCESSING") and len(chunk) > 300:
                        # Quick energy check on 16-bit PCM
                        sum_sq = 0
                        for i in range(0, min(len(chunk) - 1, 400), 2):
                            sample = int.from_bytes(chunk[i:i+2], byteorder="little", signed=True)
                            sum_sq += sample * sample
                        rms = (sum_sq / 200) ** 0.5
                        if rms > 1500:  # Deliberate user voice
                            logger.info(f"Barge-in detected (RMS={rms:.0f}), interrupting")
                            await self.interrupt()

                except Exception as e:
                    logger.error(f"Error decoding audio chunk: {e}")

    async def interrupt(self):
        """Immediately cancels active LLM streaming and TTS playback."""
        logger.info(f"Interrupting live session {self.session_id}")
        self.turn_manager.handle_barge_in()

        if self._llm_task and not self._llm_task.done():
            self._llm_task.cancel()

        if self._tts_task and not self._tts_task.done():
            self._tts_task.cancel()

        if self._tts_queue:
            while not self._tts_queue.empty():
                try:
                    self._tts_queue.get_nowait()
                except Exception:
                    break

        self._turn_in_progress = False
        self.audio_buffer.clear()
        self.turn_manager.transition_to("LISTENING", "Interrupted by user")
        await self.send_status("LISTENING", "Listening...")

    async def _monitor_silence(self):
        """Monitors audio buffer and triggers turn after pause in speech."""
        while self.is_active:
            await asyncio.sleep(0.1)
            if not self.audio_buffer or self._turn_in_progress:
                continue

            idle_duration = time.time() - self.last_audio_time
            # If buffer has accumulated >= ~200ms of audio and user has stopped speaking for silence_threshold_s
            if idle_duration >= self.silence_threshold_s and len(self.audio_buffer) >= 3200:
                pcm_bytes = bytes(self.audio_buffer)
                self.audio_buffer.clear()
                asyncio.create_task(self.execute_turn(pcm_bytes=pcm_bytes))

    async def execute_turn(self, text: Optional[str] = None, pcm_bytes: Optional[bytes] = None):
        """
        Executes an overlapped speech turn:
        USER STOPS SPEAKING -> STREAMING ASR -> FINAL TRANSCRIPT -> STREAMING LLM -> SENTENCE BUFFER -> STREAMING TTS -> SPEAKER
        """
        if self._turn_in_progress:
            return

        self._turn_in_progress = True
        self._first_audio_sent = False

        try:
            # 1. ASR Step (if text not provided)
            if not text and pcm_bytes:
                self.turn_manager.transition_to("PROCESSING", "Transcribing speech")
                await self.send_status("PROCESSING", "Transcribing speech...")
                t_asr_start = time.time()
                text = await live_asr.transcribe_pcm(pcm_bytes, self.sample_rate)
                t_asr_end = time.time()
                if not text:
                    self.turn_manager.transition_to("LISTENING", "No speech detected")
                    await self.send_status("LISTENING", "Listening...")
                    self._turn_in_progress = False
                    return
                logger.info(f"[LIVE][TIMING] ASR took {(t_asr_end - t_asr_start)*1000:.1f} ms: '{text}'")

            if not text or not text.strip():
                self.turn_manager.transition_to("LISTENING", "Empty utterance")
                self._turn_in_progress = False
                return

            user_text = text.strip()
            self._t_asr_final = time.time()

            # Broadcast final user transcript
            await self.websocket.send_json({
                "type": "transcript",
                "role": "user",
                "text": user_text,
                "isFinal": True,
            })
            self.conversation_history.append({"role": "user", "content": user_text})

            # Transition to PROCESSING
            self.turn_manager.transition_to("PROCESSING", "Streaming NVIDIA LLM")
            await self.send_status("PROCESSING", "Thinking (NVIDIA LLM)...")

            # 2. Setup Overlapped LLM + TTS Pipeline
            self._tts_queue = asyncio.Queue()

            # Start TTS Consumer Task
            self._tts_task = asyncio.create_task(self._tts_consumer(self._tts_queue, self._t_asr_final))

            # Run LLM Producer in this coroutine
            full_reply = await self._llm_producer(user_text, self._tts_queue, self._t_asr_final)

            # Wait for TTS consumer to finish synthesizing all queued phrases
            if self._tts_task:
                await self._tts_task

            # Broadcast final assistant transcript
            if full_reply:
                await self.websocket.send_json({
                    "type": "transcript",
                    "role": "assistant",
                    "text": full_reply,
                    "isFinal": True,
                })
                self.conversation_history.append({"role": "assistant", "content": full_reply})

        except asyncio.CancelledError:
            logger.info("Turn cancelled by interruption")
        except Exception as e:
            logger.error(f"Error during live turn: {e}", exc_info=True)
            self.turn_manager.handle_error(str(e))
        finally:
            self._turn_in_progress = False
            if self.turn_manager.get_state() not in ("IDLE", "ERROR"):
                self.turn_manager.transition_to("LISTENING", "Turn complete")
                await self.send_status("LISTENING", "Listening...")

    async def _llm_producer(self, user_text: str, tts_queue: asyncio.Queue, t_asr_final: float) -> str:
        """Streams LLM tokens, applies phrase buffer, and feeds sentences immediately into tts_queue."""
        full_text = ""
        token_buffer = ""
        first_token_received = False

        try:
            async for token in live_llm.stream_reply(user_text, self.conversation_history):
                if not first_token_received:
                    first_token_received = True
                    self._t_llm_first = time.time()
                    asr_to_llm_ms = (self._t_llm_first - t_asr_final) * 1000
                    logger.info(f"[LIVE][TIMING] ASR_FINAL → LLM_FIRST_TOKEN = {asr_to_llm_ms:.1f} ms")
                    await self.websocket.send_json({
                        "type": "timing",
                        "metric": "asr_to_llm_first_token_ms",
                        "value": round(asr_to_llm_ms, 1),
                    })

                full_text += token
                token_buffer += token

                await self.websocket.send_json({
                    "type": "llm_chunk",
                    "text": token,
                })

                # Check sentence boundary
                s_match = SENTENCE_SPLIT_REGEX.match(token_buffer)
                if s_match:
                    ready_sentence = s_match.group(1).strip()
                    token_buffer = s_match.group(2) or ""
                    if len(ready_sentence) >= 2:
                        await tts_queue.put(ready_sentence)
                    continue

                # Check clause boundary if we have accumulated >= 5 words
                words = token_buffer.split()
                if len(words) >= 5:
                    c_match = CLAUSE_SPLIT_REGEX.match(token_buffer)
                    if c_match:
                        ready_clause = c_match.group(1).strip()
                        token_buffer = c_match.group(2) or ""
                        if len(ready_clause) >= 2:
                            await tts_queue.put(ready_clause)

            # Flush remaining token buffer
            remaining = token_buffer.strip()
            if remaining:
                await tts_queue.put(remaining)

            # Signal end of phrases to TTS consumer
            await tts_queue.put(None)
            return full_text.strip()

        except asyncio.CancelledError:
            await tts_queue.put(None)
            raise

    async def _tts_consumer(self, tts_queue: asyncio.Queue, t_asr_final: float):
        """Pulls phrases from queue and streams synthesized audio chunks to WebSocket immediately."""
        chunk_index = 0

        try:
            while True:
                phrase = await tts_queue.get()
                if phrase is None:  # End of turn sentinel
                    break

                clean_phrase = phrase.strip()
                if not clean_phrase:
                    continue

                try:
                    async for pcm_chunk in live_tts.stream_synthesize(clean_phrase, voice=self.voice):
                        if not pcm_chunk:
                            continue

                        if not self._first_audio_sent:
                            self._first_audio_sent = True
                            t_first_audio = time.time()
                            llm_to_tts_ms = (t_first_audio - self._t_llm_first) * 1000 if self._t_llm_first else 0.0
                            asr_to_speaker_ms = (t_first_audio - t_asr_final) * 1000
                            logger.info(f"[LIVE][TIMING] LLM_FIRST_TOKEN → TTS_FIRST_AUDIO = {llm_to_tts_ms:.1f} ms")
                            logger.info(f"[LIVE][TIMING] ASR_FINAL → SPEAKER = {asr_to_speaker_ms:.1f} ms")

                            self.turn_manager.transition_to("SPEAKING", "First audio chunk ready")
                            await self.send_status("SPEAKING", "NVIDIA Voice Speaking...")

                            await self.websocket.send_json({
                                "type": "timing",
                                "metric": "llm_first_token_to_tts_first_audio_ms",
                                "value": round(llm_to_tts_ms, 1),
                            })
                            await self.websocket.send_json({
                                "type": "timing",
                                "metric": "total_latency_ms",
                                "value": round(asr_to_speaker_ms, 1),
                            })

                        audio_b64 = base64.b64encode(pcm_chunk).decode("ascii")
                        await self.websocket.send_json({
                            "type": "audio_chunk",
                            "audio": audio_b64,
                            "sampleRate": 24000,
                            "index": chunk_index,
                        })
                        chunk_index += 1

                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.error(f"Error streaming TTS phrase '{clean_phrase[:30]}': {e}")

        except asyncio.CancelledError:
            pass

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
        if self._llm_task and not self._llm_task.done():
            self._llm_task.cancel()
        if self._tts_task and not self._tts_task.done():
            self._tts_task.cancel()
        self.turn_manager.reset()
        logger.info(f"Cleaned up live session {self.session_id}")
