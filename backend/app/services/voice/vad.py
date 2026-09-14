"""Voice Activity Detection using Silero VAD."""

import logging
import numpy as np
from typing import Tuple
import warnings

logger = logging.getLogger("hsbot.voice.vad")


class VoiceActivityDetector:
    """
    Detects voice activity in audio streams using Silero VAD.
    Lightweight, on-device processing.
    """
    
    def __init__(self, threshold: float = 0.5, sample_rate: int = 16000):
        """
        Initialize VAD detector.
        
        Args:
            threshold: Confidence threshold for speech detection (0-1)
            sample_rate: Audio sample rate in Hz
        """
        self.threshold = threshold
        self.sample_rate = sample_rate
        self.model = None
        self.utils = None
        self.is_initialized = False
        
        try:
            self._initialize_model()
        except Exception as e:
            logger.warning(f"Failed to initialize Silero VAD: {e}. VAD will be disabled.")
    
    def _initialize_model(self):
        """Initialize Silero VAD model."""
        try:
            torch = __import__('torch')
            
            # Load Silero VAD
            model, utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                onnx=False,
            )
            
            self.model = model
            self.utils = utils
            self.is_initialized = True
            logger.info("Silero VAD initialized successfully")
        except ImportError:
            logger.warning("PyTorch not available. VAD will be basic threshold-based.")
            self.is_initialized = False
        except Exception as e:
            logger.error(f"Error initializing VAD model: {e}")
            self.is_initialized = False
    
    def detect_voice_activity(self, audio_chunk: np.ndarray) -> Tuple[bool, float]:
        """
        Detect if audio chunk contains speech.
        
        Args:
            audio_chunk: Audio samples (numpy array)
            
        Returns:
            Tuple of (is_speech, confidence)
        """
        if not self.is_initialized or self.model is None:
            return self._basic_vad(audio_chunk)
        
        try:
            torch = __import__('torch')
            
            # Convert to torch tensor
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                audio_tensor = torch.tensor(audio_chunk, dtype=torch.float32)
            
            # Get speech probability
            speech_prob = self.model(audio_tensor, self.sample_rate).item()
            
            is_speech = speech_prob >= self.threshold
            return is_speech, speech_prob
        except Exception as e:
            logger.debug(f"Error in VAD detection: {e}")
            return self._basic_vad(audio_chunk)
    
    def _basic_vad(self, audio_chunk: np.ndarray) -> Tuple[bool, float]:
        """
        Basic VAD using energy threshold.
        Fallback when ML model is not available.
        """
        if len(audio_chunk) == 0:
            return False, 0.0
        
        # Calculate RMS energy
        rms_energy = np.sqrt(np.mean(audio_chunk ** 2))
        
        # Normalize to 0-1 range (assuming 16-bit audio)
        max_amplitude = 32768
        normalized_energy = min(rms_energy / max_amplitude, 1.0)
        
        # Simple threshold-based detection
        is_speech = normalized_energy >= (self.threshold * 0.1)
        
        return is_speech, normalized_energy
    
    def is_speech(self, audio_chunk: np.ndarray) -> bool:
        """
        Quick check if audio contains speech.
        
        Args:
            audio_chunk: Audio samples
            
        Returns:
            True if speech is detected
        """
        is_speech, _ = self.detect_voice_activity(audio_chunk)
        return is_speech
    
    def get_confidence(self, audio_chunk: np.ndarray) -> float:
        """
        Get confidence score for speech detection.
        
        Args:
            audio_chunk: Audio samples
            
        Returns:
            Confidence score (0-1)
        """
        _, confidence = self.detect_voice_activity(audio_chunk)
        return confidence


# Singleton instance
_vad_instance = None


def get_vad_detector(threshold: float = 0.5, sample_rate: int = 16000) -> VoiceActivityDetector:
    """Get or create VAD detector instance."""
    global _vad_instance
    if _vad_instance is None:
        _vad_instance = VoiceActivityDetector(threshold, sample_rate)
    return _vad_instance
