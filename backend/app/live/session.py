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
from app.live.tamil_provider import (
    get_voice_engine,
    is_tamil_voice_available,
    BaseVoiceEngine,
    TamilVoiceUnavailableError,
)
from app.config import settings

logger = logging.getLogger("hsbot.live.session")

SENTENCE_SPLIT_REGEX = re.compile(r"^(.*?[.!?\n])\s*(.*)$", re.DOTALL)
CLAUSE_SPLIT_REGEX = re.compile(r"^(.*?[,;:])\s*(.*)$", re.DOTALL)


def calculate_pcm_rms(chunk: bytes) -> float:
    """Calculates RMS energy of 16-bit linear PCM audio chunk."""
    if len(chunk) < 2:
        return 0.0
    sample_count = len(chunk) // 2
    sum_sq = 0
    for i in range(0, len(chunk) - 1, 2):
        s = int.from_bytes(chunk[i:i+2], byteorder="little", signed=True)
        sum_sq += s * s
    return (sum_sq / (sample_count or 1)) ** 0.5


class LiveVoiceSession:
    def __init__(self, session_id: str, websocket: WebSocket):
        self.session_id = session_id
        self.websocket = websocket
        self.turn_manager = LiveTurnManager()
        self.conversation_history: List[Dict[str, str]] = []
        self.voice = getattr(settings, "live_voice", "Chatterbox-Multilingual")
        self.sample_rate = 16000
        self.is_active = True

        # Language and Voice Engine Isolation (Additive)
        self.language = "en"
        self.generation_id = 0
        self.voice_engine: BaseVoiceEngine = get_voice_engine("en")

        # VAD and Audio Buffering
        self._pre_speech_buffer = bytearray()
        self._speech_buffer = bytearray()
        self._has_voice_in_turn = False
        self._speech_onset_frames = 0
        self._last_voice_time = 0.0
        self.last_audio_time = time.time()
        self.silence_threshold_s = 0.8
        self.silence_monitor_task: Optional[asyncio.Task] = None
        self._current_turn_id: Optional[str] = None

        # Turn concurrency management
        self._turn_in_progress = False
        self._llm_task: Optional[asyncio.Task] = None
        self._tts_task: Optional[asyncio.Task] = None
        self._tts_queue: Optional[asyncio.Queue] = None
        self._t_asr_final = 0.0
        self._t_llm_first = 0.0
        self._first_audio_sent = False
        self._greeting_sent = False

    async def start(self):
        """Main WebSocket loop for session."""
        self.turn_manager.transition_to("LISTENING", "Session started")
        await self.send_status("LISTENING", "Connected to NVIDIA live engine")

        self.silence_monitor_task = asyncio.create_task(self._monitor_silence())
        asyncio.create_task(self.send_greeting())

        try:
            while self.is_active:
                raw_text = await self.websocket.receive_text()
                await self.handle_message(raw_text)
        except WebSocketDisconnect:
            logger.info(f"[LIVE][session={self.session_id}] Disconnected by client")
        except Exception as e:
            logger.error(f"[LIVE][session={self.session_id}] Error in session loop: {e}")
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
            if "silenceDurationMs" in cfg:
                self.silence_threshold_s = max(0.6, min(5.0, float(cfg["silenceDurationMs"]) / 1000.0))
            if "silenceTimeoutMs" in cfg:
                self.silence_threshold_s = max(0.6, min(5.0, float(cfg["silenceTimeoutMs"]) / 1000.0))
            logger.info(
                f"[LIVE][session={self.session_id}] Updated config: voice={self.voice}, "
                f"silence={self.silence_threshold_s}s, sampleRate={self.sample_rate}"
            )

        elif msg_type == "interrupt":
            await self.interrupt()

        elif msg_type == "set_language":
            new_lang = (msg.get("language") or "en").lower().strip()
            logger.info(f"[LIVE][session={self.session_id}] Language switch requested: '{self.language}' -> '{new_lang}'")
            # Cancel active generation to prevent race conditions (Section 15 & 16)
            await self.interrupt()
            self.generation_id += 1

            if new_lang in ("ta", "ta-in", "tamil"):
                status = is_tamil_voice_available()
                if not status.get("supported"):
                    logger.warning(f"[LIVE][session={self.session_id}] Tamil voice requested but unavailable: {status.get('code')}")
                    await self.websocket.send_json({
                        "type": "error",
                        "code": "TAMIL_VOICE_UNAVAILABLE",
                        "message": status.get("reason") or "Tamil voice is unavailable on NVIDIA hosted models.",
                        "details": status,
                    })
                    # Strictly retain English
                    self.language = "en"
                    self.voice_engine = get_voice_engine("en")
                else:
                    self.language = "ta"
                    self.voice_engine = get_voice_engine("ta")
            else:
                self.language = "en"
                self.voice_engine = get_voice_engine("en")

            await self.websocket.send_json({
                "type": "language_changed",
                "language": self.language,
                "generationId": self.generation_id,
            })
            self.turn_manager.transition_to("LISTENING", f"Language switched to {self.language}")
            await self.send_status("LISTENING", f"Listening ({self.language.upper()})...")

        elif msg_type == "user_speech":
            # Direct client-side speech transcript (fast path)
            text = (msg.get("text") or "").strip()
            if text and not self._turn_in_progress:
                self._speech_buffer.clear()
                self._has_voice_in_turn = False
                turn_id = f"turn_{int(time.time() * 1000)}"
                asyncio.create_task(self.execute_turn(text=text, turn_id=turn_id))

        elif msg_type == "commit_turn":
            # Explicit speech completion signal from client
            if not self._turn_in_progress and (self._has_voice_in_turn or len(self._speech_buffer) >= 3200):
                turn_id = self._current_turn_id or f"turn_{int(time.time() * 1000)}"
                pcm_bytes = bytes(self._speech_buffer)
                self._speech_buffer.clear()
                self._has_voice_in_turn = False
                self._speech_onset_frames = 0
                asyncio.create_task(self.execute_turn(pcm_bytes=pcm_bytes, turn_id=turn_id))

        elif msg_type == "audio":
            data_b64 = msg.get("data", "")
            if data_b64:
                try:
                    chunk = base64.b64decode(data_b64)
                    if not chunk:
                        return

                    self.last_audio_time = time.time()
                    rms = calculate_pcm_rms(chunk)

                    # 1. Barge-in check: if AI is speaking and user speaks deliberately
                    if self.turn_manager.get_state() in ("SPEAKING", "PROCESSING") and len(chunk) > 300:
                        if rms > 1200:
                            logger.info(f"[LIVE][session={self.session_id}] Barge-in detected (RMS={rms:.0f}), interrupting AI")
                            await self.interrupt()

                    # 2. If turn currently processing, drop/skip audio until reset
                    if self._turn_in_progress:
                        return

                    # 3. Voice Activity Detection (RMS threshold 380)
                    if rms >= 380:
                        self._speech_onset_frames += 1
                        if not self._has_voice_in_turn and self._speech_onset_frames >= 2:
                            self._has_voice_in_turn = True
                            self._current_turn_id = f"turn_{int(time.time() * 1000)}"
                            logger.info(
                                f"[LIVE][session={self.session_id}][turn={self._current_turn_id}] "
                                f"SPEECH_ONSET detected (RMS={rms:.0f})"
                            )
                            # Prepend rolling pre-speech buffer so initial consonants are intact
                            self._speech_buffer.clear()
                            self._speech_buffer.extend(self._pre_speech_buffer)
                            self.turn_manager.transition_to("USER_SPEAKING", "Speech onset detected")
                            await self.send_status("USER_SPEAKING", "Hearing your voice...")

                        if self._has_voice_in_turn:
                            self._last_voice_time = time.time()
                            self._speech_buffer.extend(chunk)
                    else:
                        # Low-energy or silence frame
                        if self._has_voice_in_turn:
                            # Natural pause between words, accumulate into utterance buffer
                            self._speech_buffer.extend(chunk)
                        else:
                            # Rolling pre-speech buffer (capped at 16000 bytes = ~500ms)
                            self._speech_onset_frames = max(0, self._speech_onset_frames - 1)
                            self._pre_speech_buffer.extend(chunk)
                            if len(self._pre_speech_buffer) > 16000:
                                del self._pre_speech_buffer[:-16000]

                except Exception as e:
                    logger.error(f"[LIVE][session={self.session_id}] Error decoding audio chunk: {e}")

    async def handle_audio_chunk(self, chunk: bytes):
        """Processes a raw 16kHz Int16 PCM audio chunk received from WebSocket."""
        if not chunk:
            return

        self.last_audio_time = time.time()
        rms = calculate_pcm_rms(chunk)

        # 1. Barge-in check: if AI is speaking and user speaks deliberately
        if self.turn_manager.get_state() in ("SPEAKING", "PROCESSING") and len(chunk) > 300:
            if rms > 1200:
                logger.info(f"[LIVE][session={self.session_id}] Barge-in detected (RMS={rms:.0f}), interrupting AI")
                await self.interrupt()

        # 2. If turn currently processing, drop/skip audio until reset
        if self._turn_in_progress:
            return

        # 3. Voice Activity Detection (RMS threshold 250 for responsive detection)
        if rms >= 250:
            self._speech_onset_frames += 1
            if not self._has_voice_in_turn and self._speech_onset_frames >= 2:
                self._has_voice_in_turn = True
                self._current_turn_id = f"turn_{int(time.time() * 1000)}"
                logger.info(
                    f"[LIVE][session={self.session_id}][turn={self._current_turn_id}] "
                    f"SPEECH_ONSET detected (RMS={rms:.0f})"
                )
                self._speech_buffer.clear()
                self._speech_buffer.extend(self._pre_speech_buffer)
                self.turn_manager.transition_to("USER_SPEAKING", "Speech onset detected")
                await self.send_status("USER_SPEAKING", "Hearing your voice...")

            if self._has_voice_in_turn:
                self._last_voice_time = time.time()
                self._speech_buffer.extend(chunk)
        else:
            if self._has_voice_in_turn:
                self._speech_buffer.extend(chunk)
            else:
                self._speech_onset_frames = max(0, self._speech_onset_frames - 1)
                self._pre_speech_buffer.extend(chunk)
                if len(self._pre_speech_buffer) > 16000:
                    del self._pre_speech_buffer[:-16000]

    async def finalize_user_speech(self):
        """Forces turn execution on explicit audio_end signal."""
        if not self._turn_in_progress and len(self._speech_buffer) >= 3200:
            turn_id = self._current_turn_id or f"turn_{int(time.time() * 1000)}"
            pcm_bytes = bytes(self._speech_buffer)
            self._speech_buffer.clear()
            self._pre_speech_buffer.clear()
            self._has_voice_in_turn = False
            self._speech_onset_frames = 0
            asyncio.create_task(self.execute_turn(pcm_bytes=pcm_bytes, turn_id=turn_id))

    async def interrupt(self):
        """Immediately cancels active LLM streaming and TTS playback."""
        logger.info(f"[LIVE][session={self.session_id}] Interrupting live session")
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
        self._speech_buffer.clear()
        self._pre_speech_buffer.clear()
        self._has_voice_in_turn = False
        self._speech_onset_frames = 0
        self.turn_manager.transition_to("LISTENING", "Interrupted by user")
        await self.send_status("LISTENING", "Listening...")

    async def _monitor_silence(self):
        """Monitors audio buffer and triggers turn ONLY after confirmed speech followed by silence."""
        while self.is_active:
            await asyncio.sleep(0.05)
            if not self._has_voice_in_turn or self._turn_in_progress:
                continue

            pause_duration = time.time() - self._last_voice_time
            # User spoke and has now stopped speaking for silence_threshold_s with >= ~250ms of audio
            if pause_duration >= self.silence_threshold_s and len(self._speech_buffer) >= 8000:
                turn_id = self._current_turn_id or f"turn_{int(time.time() * 1000)}"
                pcm_bytes = bytes(self._speech_buffer)
                duration_s = len(pcm_bytes) / 32000.0
                logger.info(
                    f"[LIVE][session={self.session_id}][turn={turn_id}] SPEECH_OFFSET: "
                    f"Pause={pause_duration:.2f}s, Utterance={len(pcm_bytes)} bytes (~{duration_s:.2f}s)"
                )
                self._has_voice_in_turn = False
                self._speech_buffer.clear()
                self._pre_speech_buffer.clear()
                self._speech_onset_frames = 0
                asyncio.create_task(self.execute_turn(pcm_bytes=pcm_bytes, turn_id=turn_id))

    async def finalize_user_speech(self):
        """Finalizes buffered user speech and triggers turn execution."""
        if not self._turn_in_progress and (self._has_voice_in_turn or len(self._speech_buffer) >= 3200):
            turn_id = self._current_turn_id or f"turn_{int(time.time() * 1000)}"
            pcm_bytes = bytes(self._speech_buffer)
            self._speech_buffer.clear()
            self._has_voice_in_turn = False
            self._speech_onset_frames = 0
            await self.execute_turn(pcm_bytes=pcm_bytes, turn_id=turn_id)

    async def send_greeting(self, text: Optional[str] = None):
        """
        Synthesizes and delivers an initial spoken greeting when the live voice session connects.
        """
        if self._greeting_sent:
            return
        self._greeting_sent = True

        greeting_text = text or (
            "வணக்கம்! நான் HSBot. நான் உங்களுக்கு எவ்வாறு உதவ முடியும்?"
            if self.language == "ta"
            else "Hello! I am HSBot. How can I help you today?"
        )
        turn_id = f"greeting_{int(time.time() * 1000)}"
        self.generation_id += 1
        turn_gen_id = self.generation_id

        logger.info(f"[LIVE][session={self.session_id}] Delivering greeting: '{greeting_text}'")

        try:
            # 1. Send assistant transcript to frontend
            await self.websocket.send_json({
                "type": "transcript",
                "role": "assistant",
                "text": greeting_text,
                "isFinal": True,
                "turnId": turn_id,
            })
            self.conversation_history.append({"role": "assistant", "content": greeting_text})

            # 2. Transition state to SPEAKING
            self.turn_manager.transition_to("SPEAKING", "Greeting user")
            await self.send_status("SPEAKING", "HSBot speaking...")

            chunk_index = 0
            async for pcm_chunk in self.voice_engine.stream_synthesize(greeting_text, voice=self.voice):
                if self.generation_id != turn_gen_id or not self.is_active:
                    logger.info(f"[LIVE][session={self.session_id}] Greeting interrupted, aborting audio stream")
                    break
                if not pcm_chunk:
                    continue
                audio_b64 = base64.b64encode(pcm_chunk).decode("ascii")
                await self.websocket.send_json({
                    "type": "audio_chunk",
                    "audio": audio_b64,
                    "sampleRate": 24000,
                    "index": chunk_index,
                    "turnId": turn_id,
                    "generationId": turn_gen_id,
                })
                chunk_index += 1
        except Exception as e:
            logger.error(f"[LIVE][session={self.session_id}] Error streaming greeting audio: {e}")
        finally:
            # 3. Transition back to LISTENING once finished if still active and on same generation
            if self.generation_id == turn_gen_id and self.is_active:
                self.turn_manager.transition_to("LISTENING", "Greeting complete")
                await self.send_status("LISTENING", "Listening...")

    async def execute_turn(
        self,
        text: Optional[str] = None,
        pcm_bytes: Optional[bytes] = None,
        turn_id: Optional[str] = None,
    ):
        """
        Executes an overlapped speech turn:
        USER STOPS SPEAKING -> STREAMING ASR -> FINAL TRANSCRIPT -> STREAMING LLM -> PHRASE BUFFER -> STREAMING TTS -> SPEAKER
        """
        if self._turn_in_progress:
            return

        turn_id = turn_id or f"turn_{int(time.time() * 1000)}"
        self._turn_in_progress = True
        self._first_audio_sent = False
        self._current_turn_id = turn_id
        self.generation_id += 1
        turn_gen_id = self.generation_id

        try:
            # 1. ASR Step (if text not provided)
            if not text and pcm_bytes:
                self.turn_manager.transition_to("PROCESSING", "Transcribing speech")
                await self.send_status("PROCESSING", f"Transcribing speech ({self.language.upper()})...")
                t_asr_start = time.time()
                logger.info(f"[LIVE][session={self.session_id}][turn={turn_id}][lang={self.language}] ASR_START ({len(pcm_bytes)} bytes)")

                try:
                    # 6.0 second fail-fast timeout for ASR
                    text = await asyncio.wait_for(
                        self.voice_engine.transcribe(pcm_bytes, self.sample_rate),
                        timeout=6.0,
                    )
                except TamilVoiceUnavailableError as e:
                    logger.warning(f"[LIVE][session={self.session_id}][turn={turn_id}] Tamil ASR unavailable: {e.message}")
                    await self.websocket.send_json({
                        "type": "error",
                        "code": e.code,
                        "message": e.message,
                        "turnId": turn_id,
                    })
                    self.turn_manager.transition_to("LISTENING", "Tamil ASR unavailable")
                    await self.send_status("LISTENING", "Listening (EN)...")
                    self._turn_in_progress = False
                    return
                except asyncio.TimeoutError:
                    logger.error(f"[LIVE][session={self.session_id}][turn={turn_id}] ASR_TIMEOUT (>6.0s)")
                    text = ""
                except Exception as e:
                    logger.error(f"[LIVE][session={self.session_id}][turn={turn_id}] ASR_ERROR: {e}")
                    text = ""

                t_asr_end = time.time()
                asr_latency_ms = (t_asr_end - t_asr_start) * 1000

                if not text or not text.strip():
                    logger.info(
                        f"[LIVE][session={self.session_id}][turn={turn_id}] "
                        f"ASR_COMPLETE: No speech recognized in {asr_latency_ms:.1f}ms"
                    )
                    self.turn_manager.transition_to("LISTENING", "No speech detected")
                    await self.send_status("LISTENING", "Listening...")
                    self._turn_in_progress = False
                    return

                logger.info(
                    f"[LIVE][session={self.session_id}][turn={turn_id}] "
                    f"ASR_COMPLETE in {asr_latency_ms:.1f}ms: '{text}'"
                )

            if not text or not text.strip():
                self.turn_manager.transition_to("LISTENING", "Empty utterance")
                await self.send_status("LISTENING", "Listening...")
                self._turn_in_progress = False
                return

            # Check race condition (Section 16)
            if self.generation_id != turn_gen_id:
                logger.info(f"[LIVE][session={self.session_id}][turn={turn_id}] Stale generation {turn_gen_id}, dropping")
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
                "turnId": turn_id,
                "generationId": turn_gen_id,
            })
            self.conversation_history.append({"role": "user", "content": user_text})

            # Transition to PROCESSING (Thinking)
            self.turn_manager.transition_to("PROCESSING", "Streaming NVIDIA LLM")
            await self.send_status("PROCESSING", "Thinking (NVIDIA LLM)...")

            # 2. Setup Overlapped LLM + TTS Pipeline
            self._tts_queue = asyncio.Queue()

            # Start TTS Consumer Task
            self._tts_task = asyncio.create_task(
                self._tts_consumer(self._tts_queue, self._t_asr_final, turn_id, turn_gen_id)
            )

            # Run LLM Producer in this coroutine
            full_reply = await self._llm_producer(
                user_text, self._tts_queue, self._t_asr_final, turn_id, turn_gen_id
            )

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
                    "turnId": turn_id,
                })
                self.conversation_history.append({"role": "assistant", "content": full_reply})

        except asyncio.CancelledError:
            logger.info(f"[LIVE][session={self.session_id}][turn={turn_id}] Turn cancelled by interruption")
        except Exception as e:
            logger.error(f"[LIVE][session={self.session_id}][turn={turn_id}] Error during live turn: {e}", exc_info=True)
            self.turn_manager.handle_error(str(e))
        finally:
            self._turn_in_progress = False
            if self.turn_manager.get_state() not in ("IDLE", "ERROR"):
                self.turn_manager.transition_to("LISTENING", "Turn complete")
                await self.send_status("LISTENING", "Listening...")

    async def _llm_producer(
        self,
        user_text: str,
        tts_queue: asyncio.Queue,
        t_asr_final: float,
        turn_id: str,
        turn_gen_id: int,
    ) -> str:
        """Streams LLM tokens, applies phrase buffer, and feeds sentences immediately into tts_queue."""
        full_text = ""
        token_buffer = ""
        first_token_received = False

        logger.info(f"[LIVE][session={self.session_id}][turn={turn_id}][gen={turn_gen_id}][lang={self.language}] LLM_START")

        # Isolated prompt instruction for non-English sessions (Section 10)
        prompt_instruction = self.voice_engine.get_prompt_instruction()
        llm_input = f"{prompt_instruction}\n\n{user_text}" if prompt_instruction else user_text

        try:
            async for token in live_llm.stream_reply(llm_input, self.conversation_history):
                # Race condition drop: if language was switched or user interrupted
                if self.generation_id != turn_gen_id:
                    logger.info(f"[LIVE][session={self.session_id}][turn={turn_id}] Stale LLM stream {turn_gen_id}, dropping")
                    break

                if not first_token_received:
                    first_token_received = True
                    self._t_llm_first = time.time()
                    asr_to_llm_ms = (self._t_llm_first - t_asr_final) * 1000
                    logger.info(
                        f"[LIVE][session={self.session_id}][turn={turn_id}] "
                        f"LLM_FIRST_TOKEN in {asr_to_llm_ms:.1f}ms"
                    )
                    await self.websocket.send_json({
                        "type": "timing",
                        "metric": "asr_to_llm_first_token_ms",
                        "value": round(asr_to_llm_ms, 1),
                        "turnId": turn_id,
                    })

                full_text += token
                token_buffer += token

                await self.websocket.send_json({
                    "type": "llm_chunk",
                    "text": token,
                    "turnId": turn_id,
                })

                # Check sentence boundary
                s_match = SENTENCE_SPLIT_REGEX.match(token_buffer)
                if s_match:
                    ready_sentence = s_match.group(1).strip()
                    token_buffer = s_match.group(2) or ""
                    if len(ready_sentence) >= 2:
                        await tts_queue.put(ready_sentence)
                    continue

                # Check clause boundary if we have accumulated >= 3 words for faster audio turn-around
                words = token_buffer.split()
                if len(words) >= 3:
                    c_match = CLAUSE_SPLIT_REGEX.match(token_buffer)
                    if c_match:
                        ready_clause = c_match.group(1).strip()
                        token_buffer = c_match.group(2) or ""
                        if len(ready_clause) >= 2:
                            await tts_queue.put(ready_clause)

            # Flush remaining token buffer
            remaining = token_buffer.strip()
            if remaining and self.generation_id == turn_gen_id:
                await tts_queue.put(remaining)

            # Signal end of phrases to TTS consumer
            await tts_queue.put(None)
            logger.info(f"[LIVE][session={self.session_id}][turn={turn_id}] LLM_COMPLETE: '{full_text[:60]}...'")
            return full_text.strip()

        except asyncio.CancelledError:
            await tts_queue.put(None)
            raise

    async def _tts_consumer(self, tts_queue: asyncio.Queue, t_asr_final: float, turn_id: str, turn_gen_id: int):
        """Pulls phrases from queue and streams synthesized audio chunks to WebSocket immediately."""
        chunk_index = 0

        try:
            while True:
                phrase = await tts_queue.get()
                if phrase is None:  # End of turn sentinel
                    break

                clean_phrase = phrase.strip()
                if not clean_phrase or self.generation_id != turn_gen_id:
                    continue

                try:
                    async for pcm_chunk in self.voice_engine.stream_synthesize(clean_phrase, voice=self.voice):
                        if self.generation_id != turn_gen_id:
                            logger.info(f"[LIVE][session={self.session_id}][turn={turn_id}] Stale TTS chunk {turn_gen_id}, dropping")
                            break

                        if not pcm_chunk:
                            continue

                        if not self._first_audio_sent:
                            self._first_audio_sent = True
                            t_first_audio = time.time()
                            llm_to_tts_ms = (t_first_audio - self._t_llm_first) * 1000 if self._t_llm_first else 0.0
                            asr_to_speaker_ms = (t_first_audio - t_asr_final) * 1000
                            logger.info(
                                f"[LIVE][session={self.session_id}][turn={turn_id}] "
                                f"TTS_FIRST_AUDIO in {llm_to_tts_ms:.1f}ms"
                            )
                            logger.info(
                                f"[LIVE][session={self.session_id}][turn={turn_id}] "
                                f"TOTAL_TURN_LATENCY = {asr_to_speaker_ms:.1f}ms"
                            )

                            self.turn_manager.transition_to("SPEAKING", "First audio chunk ready")
                            await self.send_status("SPEAKING", "NVIDIA Voice Speaking...")

                            await self.websocket.send_json({
                                "type": "timing",
                                "metric": "llm_first_token_to_tts_first_audio_ms",
                                "value": round(llm_to_tts_ms, 1),
                                "turnId": turn_id,
                            })
                            await self.websocket.send_json({
                                "type": "timing",
                                "metric": "total_latency_ms",
                                "value": round(asr_to_speaker_ms, 1),
                                "turnId": turn_id,
                            })

                        audio_b64 = base64.b64encode(pcm_chunk).decode("ascii")
                        await self.websocket.send_json({
                            "type": "audio_chunk",
                            "audio": audio_b64,
                            "sampleRate": 24000,
                            "index": chunk_index,
                            "turnId": turn_id,
                            "generationId": turn_gen_id,
                        })
                        chunk_index += 1

                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.error(f"[LIVE][session={self.session_id}][turn={turn_id}] Error streaming TTS phrase '{clean_phrase[:30]}': {e}")

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
        self._speech_buffer.clear()
        self._pre_speech_buffer.clear()
        self.turn_manager.reset()
        logger.info(f"[LIVE][session={self.session_id}] Cleaned up live session")

