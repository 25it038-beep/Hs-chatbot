"""Main Voice Listener for HSBot always-listening architecture."""

import logging
import asyncio
import threading
import numpy as np
from typing import Optional, Callable, List
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import queue

from .vad import get_vad_detector
from .wake_word import get_wake_word_detector
from .speaker_verification import get_speaker_verifier

logger = logging.getLogger("hsbot.voice.listener")


class ListenerState(Enum):
    """States for the voice listener."""
    STOPPED = "stopped"
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    COMMAND_ACTIVE = "command_active"


@dataclass
class VoiceCommand:
    """Represents a voice command detected by the listener."""
    wake_word: str
    speaker_id: Optional[str]
    speaker_confidence: float
    command_text: str
    audio_data: np.ndarray
    timestamp: datetime
    is_verified: bool


class VoiceListener:
    """
    Main voice listener that monitors microphone and processes voice commands.
    Runs as a background service.
    """
    
    def __init__(self, 
                 sample_rate: int = 16000,
                 chunk_duration_ms: int = 100,
                 enable_speaker_verification: bool = True):
        """
        Initialize voice listener.
        
        Args:
            sample_rate: Audio sample rate in Hz
            chunk_duration_ms: Duration of audio chunks in milliseconds
            enable_speaker_verification: Enable voice match feature
        """
        self.sample_rate = sample_rate
        self.chunk_size = int(sample_rate * chunk_duration_ms / 1000)
        self.enable_speaker_verification = enable_speaker_verification
        
        # Initialize components
        self.vad = get_vad_detector()
        self.wake_word_detector = get_wake_word_detector()
        self.speaker_verifier = get_speaker_verifier() if enable_speaker_verification else None
        
        # State management
        self.state = ListenerState.STOPPED
        self.is_running = False
        self.listener_thread = None
        self.audio_stream = None
        
        # Audio buffering
        self.audio_buffer = []
        self.buffer_max_chunks = 160  # ~1.6 seconds for 100ms chunks
        self.command_queue = queue.Queue()
        
        # Callbacks
        self.on_wake_word = None
        self.on_command = None
        self.on_error = None
        self.on_state_change = None
        self.on_verification = None
        self.command_handler = None

        # Event bus (thread-safe): subscribers get every listener event
        self._subscribers: List[queue.Queue] = []
        self._subscribers_lock = threading.Lock()
        
        # Configuration
        self.continuous_conversation_enabled = False
        self.continuous_timeout = 10  # seconds
        self.last_command_time = None
        self.wake_word_required = False  # always-listening by default (no wake word)
        
        # Microphone setup
        self.microphone_enabled = True
        self.default_device = None
        
        logger.info("Voice listener initialized")
    
    def start(self):
        """Start the voice listener."""
        if self.is_running:
            logger.warning("Voice listener already running")
            return
        
        try:
            self.is_running = True
            self._set_state(ListenerState.IDLE)
            
            # Start listener thread
            self.listener_thread = threading.Thread(target=self._listen_loop, daemon=True)
            self.listener_thread.start()
            
            logger.info("Voice listener started")
        except Exception as e:
            logger.error(f"Error starting voice listener: {e}")
            self._handle_error(e)
            self.is_running = False
    
    def stop(self):
        """Stop the voice listener."""
        self.is_running = False
        self._set_state(ListenerState.STOPPED)
        
        if self.listener_thread:
            self.listener_thread.join(timeout=5)
        
        logger.info("Voice listener stopped")
    
    def set_microphone_enabled(self, enabled: bool):
        """Enable or disable microphone."""
        self.microphone_enabled = enabled
        if not enabled:
            self._set_state(ListenerState.IDLE)
        logger.info(f"Microphone {'enabled' if enabled else 'disabled'}")
    
    def set_continuous_conversation(self, enabled: bool, timeout: int = 10):
        """
        Enable or disable continuous conversation mode.
        
        Args:
            enabled: Enable continuous conversation
            timeout: Timeout in seconds before returning to passive mode
        """
        self.continuous_conversation_enabled = enabled
        self.continuous_timeout = timeout
        logger.info(f"Continuous conversation mode: {enabled}")

    def set_wake_word_required(self, required: bool):
        """Toggle wake-word gating. False = always-listening (commands captured directly)."""
        self.wake_word_required = required
        logger.info(f"Wake word required: {required}")
    
    def register_callback(self, event_type: str, callback: Callable):
        """
        Register event callback.
        
        Args:
            event_type: Type of event ('wake_word', 'command', 'error', 'state_change')
            callback: Callback function
        """
        if event_type == 'wake_word':
            self.on_wake_word = callback
        elif event_type == 'command':
            self.on_command = callback
        elif event_type == 'error':
            self.on_error = callback
        elif event_type == 'state_change':
            self.on_state_change = callback
        elif event_type == 'verification':
            self.on_verification = callback

    def subscribe(self) -> queue.Queue:
        """Subscribe to listener events. Returns a thread-safe queue."""
        q: queue.Queue = queue.Queue(maxsize=500)
        with self._subscribers_lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: queue.Queue):
        with self._subscribers_lock:
            try:
                self._subscribers.remove(q)
            except ValueError:
                pass

    def _emit(self, event: dict):
        """Publish an event to all subscribers (called from the listener thread)."""
        event["timestamp"] = event.get("timestamp") or datetime.now().isoformat()
        with self._subscribers_lock:
            subs = list(self._subscribers)
        for q in subs:
            try:
                q.put_nowait(event)
            except queue.Full:
                try:
                    q.get_nowait()
                    q.put_nowait(event)
                except Exception:
                    pass

    def set_command_handler(self, handler: Callable):
        """Set a handler invoked for every detected voice command (thread-safe bridge)."""
        self.command_handler = handler

    def _run_command_handler(self, command: "VoiceCommand"):
        if self.command_handler:
            try:
                self.command_handler(command)
            except Exception as e:
                logger.error(f"Voice command handler error: {e}")
    
    def _listen_loop(self):
        """Main listening loop (runs in separate thread)."""
        try:
            import pyaudio
            
            # Initialize PyAudio
            p = pyaudio.PyAudio()
            
            # Open microphone stream
            stream = p.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size,
                input_device_index=self.default_device,
            )
            
            logger.info("Audio stream opened")
            self.audio_stream = stream
            
            while self.is_running and self.microphone_enabled:
                try:
                    # Read audio chunk
                    audio_chunk = stream.read(self.chunk_size, exception_on_overflow=False)
                    audio_data = np.frombuffer(audio_chunk, dtype=np.float32)
                    
                    # Process audio
                    self._process_audio_chunk(audio_data)
                    
                except Exception as e:
                    logger.debug(f"Error reading audio: {e}")
                    continue
            
            # Cleanup
            stream.stop_stream()
            stream.close()
            p.terminate()
            
        except ImportError:
            logger.error("PyAudio not available. Install with: pip install pyaudio")
            self._handle_error("PyAudio not available")
        except Exception as e:
            logger.error(f"Error in listen loop: {e}")
            self._handle_error(e)
        finally:
            self.audio_stream = None
            self._set_state(ListenerState.STOPPED)
    
    def _process_audio_chunk(self, audio_data: np.ndarray):
        """Process a single audio chunk."""
        if self.state == ListenerState.STOPPED:
            return
        
        # Add to buffer
        self.audio_buffer.append(audio_data)
        if len(self.audio_buffer) > self.buffer_max_chunks:
            self.audio_buffer.pop(0)
        
        # Detect voice activity
        is_speech, confidence = self.vad.detect_voice_activity(audio_data)
        
        if self.state == ListenerState.IDLE:
            if is_speech and confidence > 0.3:
                self._set_state(ListenerState.LISTENING)
                logger.debug("Voice activity detected")
        
        elif self.state == ListenerState.LISTENING:
            if not is_speech:
                if self.wake_word_required:
                    # Wake word gated: only commands after "wake up"/"hey hs"
                    self._check_for_wake_word()
                    self._set_state(ListenerState.IDLE)
                else:
                    # Always-listening: process speech directly as a command
                    self._process_command_audio()
                    self._set_state(ListenerState.IDLE)
        
        elif self.state == ListenerState.COMMAND_ACTIVE:
            if not is_speech:
                # Process command audio
                self._process_command_audio()
                self._check_continuous_mode()
    
    def _check_for_wake_word(self):
        """Check buffered audio for wake word."""
        if not self.audio_buffer:
            return
        
        try:
            # Combine audio chunks
            combined_audio = np.concatenate(self.audio_buffer)
            
            # Try to recognize speech
            import speech_recognition as sr
            
            # Create AudioData object
            audio_bytes = (combined_audio * 32767).astype(np.int16).tobytes()
            audio_data = sr.AudioData(audio_bytes, self.sample_rate, 2)
            
            # Recognize
            recognized_text = self._recognize_speech(audio_data)
            
            if recognized_text:
                # Check for wake word
                detected, matched_word = self.wake_word_detector.detect_wake_word(
                    recognized_text
                )
                
                if detected:
                    self._on_wake_word_detected(matched_word, recognized_text)
        except Exception as e:
            logger.debug(f"Error checking for wake word: {e}")
    
    def _on_wake_word_detected(self, wake_word: str, recognized_text: str):
        """Handle wake word detection."""
        logger.info(f"Wake word detected: {wake_word}")
        self._set_state(ListenerState.COMMAND_ACTIVE)
        
        # Perform speaker verification if enabled
        speaker_id = None
        speaker_confidence = 0.0
        is_verified = True
        
        if self.enable_speaker_verification and self.speaker_verifier:
            try:
                # TODO: Get current user ID from context
                # result = self.speaker_verifier.verify_speaker(user_id, org_id, ...)
                # speaker_id = result.speaker_id
                # speaker_confidence = result.confidence
                # is_verified = result.matched
                pass
            except Exception as e:
                logger.warning(f"Speaker verification error: {e}")
        
        self._emit({
            "type": "wake_word",
            "wake_word": wake_word,
            "recognized_text": recognized_text,
            "speaker_id": speaker_id,
            "speaker_confidence": speaker_confidence,
            "is_verified": is_verified,
            "timestamp": datetime.now().isoformat(),
        })
        
        # Call callback
        if self.on_wake_word:
            self.on_wake_word({
                'wake_word': wake_word,
                'speaker_id': speaker_id,
                'speaker_confidence': speaker_confidence,
                'is_verified': is_verified,
                'timestamp': datetime.now(),
            })
        
        self.last_command_time = datetime.now()
    
    def _process_command_audio(self):
        """Process buffered audio as command."""
        if not self.audio_buffer:
            return
        
        try:
            # Combine audio chunks
            combined_audio = np.concatenate(self.audio_buffer)
            
            # Recognize speech
            import speech_recognition as sr
            
            audio_bytes = (combined_audio * 32767).astype(np.int16).tobytes()
            audio_data = sr.AudioData(audio_bytes, self.sample_rate, 2)
            
            command_text = self._recognize_speech(audio_data)
            
            if command_text:
                # Create command object
                command = VoiceCommand(
                    wake_word=self.wake_word_detector.get_active_wake_word_phrase(),
                    speaker_id=None,
                    speaker_confidence=0.0,
                    command_text=command_text,
                    audio_data=combined_audio,
                    timestamp=datetime.now(),
                    is_verified=True,
                )
                
                # Add to queue
                self.command_queue.put(command)
                
                self._emit({
                    "type": "command",
                    "command_text": command_text,
                    "speaker_confidence": command.speaker_confidence,
                    "is_verified": command.is_verified,
                    "timestamp": datetime.now().isoformat(),
                })
                
                # Call callback
                if self.on_command:
                    self.on_command(command)

                # Bridge to the automation engine / chat
                self._run_command_handler(command)
                
                logger.info(f"Command received: {command_text}")
        except Exception as e:
            logger.error(f"Error processing command audio: {e}")
    
    def _check_continuous_mode(self):
        """Check if we should return to continuous conversation mode."""
        if not self.continuous_conversation_enabled:
            self._set_state(ListenerState.IDLE)
            return
        
        if self.last_command_time:
            elapsed = (datetime.now() - self.last_command_time).total_seconds()
            if elapsed > self.continuous_timeout:
                self._set_state(ListenerState.IDLE)
                logger.info("Continuous conversation timeout, returning to passive mode")
            else:
                self._set_state(ListenerState.COMMAND_ACTIVE)
                logger.debug("Continuous conversation mode active")
    
    def _recognize_speech(self, audio_data) -> Optional[str]:
        """Recognize speech from audio data."""
        try:
            import speech_recognition as sr
            
            recognizer = sr.Recognizer()
            text = recognizer.recognize_google(audio_data)
            return text
        except sr.UnknownValueError:
            logger.debug("Could not understand audio")
            return None
        except sr.RequestError as e:
            logger.warning(f"Speech recognition error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in speech recognition: {e}")
            return None
    
    def _set_state(self, new_state: ListenerState):
        """Change listener state."""
        if self.state != new_state:
            old_state = self.state
            self.state = new_state
            logger.debug(f"State change: {old_state.value} → {new_state.value}")
            
            self._emit({
                "type": "state_change",
                "old_state": old_state.value,
                "new_state": new_state.value,
                "timestamp": datetime.now().isoformat(),
            })
            
            if self.on_state_change:
                self.on_state_change({
                    'old_state': old_state.value,
                    'new_state': new_state.value,
                    'timestamp': datetime.now(),
                })
    
    def _handle_error(self, error: Exception):
        """Handle listener error."""
        logger.error(f"Voice listener error: {error}")
        self._emit({
            "type": "error",
            "error": str(error),
            "timestamp": datetime.now().isoformat(),
        })
        if self.on_error:
            self.on_error({
                'error': str(error),
                'timestamp': datetime.now(),
            })
    
    def get_state(self) -> str:
        """Get current listener state."""
        return self.state.value
    
    def get_command(self, timeout: float = 1.0) -> Optional[VoiceCommand]:
        """
        Get next command from queue.
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            VoiceCommand or None
        """
        try:
            return self.command_queue.get(timeout=timeout)
        except queue.Empty:
            return None


# Singleton instance
_voice_listener_instance = None


def get_voice_listener() -> VoiceListener:
    """Get or create voice listener instance."""
    global _voice_listener_instance
    if _voice_listener_instance is None:
        _voice_listener_instance = VoiceListener()
    return _voice_listener_instance
