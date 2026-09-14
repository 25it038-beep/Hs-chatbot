"""Wake Word Detection for HSBot voice activation."""

import logging
from typing import Optional, Dict, List
from dataclasses import dataclass

logger = logging.getLogger("hsbot.voice.wake_word")


@dataclass
class WakeWordConfig:
    """Configuration for wake word detection."""
    word: str
    sensitivity: float = 0.5  # 0-1, higher = more sensitive
    enabled: bool = True
    aliases: List[str] = None  # Alternative phrases


class WakeWordDetector:
    """
    Detects wake words in audio streams.
    Supports multiple wake words with configurable sensitivity.
    """
    
    # Default wake words
    DEFAULT_WAKE_WORDS = {
        "wakeup": WakeWordConfig(
            word="wake up",
            aliases=["wakeup", "wake up", "hey hs", "hs", "hey assistant", "hey hsbot"],
            sensitivity=0.5,
        ),
    }
    
    def __init__(self):
        """Initialize wake word detector."""
        self.recognizer = None
        self.is_initialized = False
        self.wake_words: Dict[str, WakeWordConfig] = {}
        self.active_wake_word = "wakeup"
        
        try:
            self._initialize_detector()
        except Exception as e:
            logger.warning(f"Failed to initialize wake word detector: {e}")
            self.is_initialized = False
    
    def _initialize_detector(self):
        """Initialize speech recognition system."""
        try:
            try:
                import speech_recognition as sr
                self.recognizer = sr.Recognizer()
                self.is_initialized = True
                logger.info("Wake word detector initialized with speech_recognition")
            except ImportError:
                logger.warning("speech_recognition not available. Using pattern matching.")
                self.is_initialized = False
        except Exception as e:
            logger.error(f"Error initializing wake word detector: {e}")
            self.is_initialized = False
    
    def add_wake_word(self, config: WakeWordConfig):
        """
        Add a wake word configuration.
        
        Args:
            config: WakeWordConfig object
        """
        key = config.word.lower().replace(" ", "_")
        self.wake_words[key] = config
        logger.info(f"Added wake word: {config.word}")
    
    def set_active_wake_word(self, word_key: str):
        """
        Set the active wake word.

        Args:
            word_key: Key of the wake word (e.g., 'wakeup')
        """
        if word_key in self.wake_words:
            self.active_wake_word = word_key
            logger.info(f"Active wake word set to: {word_key}")
        else:
            logger.warning(f"Wake word not found: {word_key}")
    
    def detect_wake_word(self, text: str) -> tuple[bool, str, float]:
        """
        Detect if text contains a wake word.
        
        Args:
            text: Recognized text from speech
            
        Returns:
            Tuple of (wake_word_detected, wake_word_matched, confidence)
        """
        if not text:
            return False, "", 0.0
        
        text_lower = text.lower().strip()
        
        # Check all configured wake words
        for key, config in self.wake_words.items():
            if not config.enabled:
                continue
            
            # Check exact word
            if config.word.lower() in text_lower:
                return True, config.word, min(0.95, config.sensitivity + 0.45)
            
            # Check aliases
            if config.aliases:
                for alias in config.aliases:
                    if alias.lower() in text_lower:
                        # Confidence based on match position and sensitivity
                        if text_lower.startswith(alias.lower()):
                            confidence = config.sensitivity + 0.5
                        else:
                            confidence = config.sensitivity + 0.3
                        return True, alias, min(0.95, confidence)
        
        return False, "", 0.0
    
    def process_audio_for_wake_word(self, audio_data) -> tuple[bool, Optional[str]]:
        """
        Process audio data for wake word detection.
        
        Args:
            audio_data: Raw audio data or AudioData object
            
        Returns:
            Tuple of (wake_word_detected, recognized_text)
        """
        if not self.is_initialized:
            return False, None
        
        try:
            import speech_recognition as sr
            
            # Convert audio data if needed
            if isinstance(audio_data, sr.AudioData):
                audio_input = audio_data
            else:
                # Assume it's raw bytes
                audio_input = audio_data
            
            # Recognize speech
            try:
                recognized_text = self.recognizer.recognize_google(audio_input)
                logger.debug(f"Recognized text: {recognized_text}")
                
                # Check for wake word
                detected, matched_word, confidence = self.detect_wake_word(recognized_text)
                
                if detected:
                    logger.info(f"Wake word detected: {matched_word} (confidence: {confidence:.2f})")
                    return True, recognized_text
                
                return False, recognized_text
            except sr.UnknownValueError:
                logger.debug("Could not understand audio")
                return False, None
            except sr.RequestError as e:
                logger.warning(f"Speech recognition service error: {e}")
                return False, None
        except Exception as e:
            logger.error(f"Error in wake word processing: {e}")
            return False, None
    
    def get_active_wake_word_phrase(self) -> str:
        """Get the currently active wake word phrase."""
        if self.active_wake_word in self.wake_words:
            return self.wake_words[self.active_wake_word].word
        return "wake up"
    
    def get_all_wake_words(self) -> List[str]:
        """Get list of all configured wake word phrases."""
        return [config.word for config in self.wake_words.values() if config.enabled]


# Singleton instance
_wake_word_detector_instance = None


def get_wake_word_detector() -> WakeWordDetector:
    """Get or create wake word detector instance."""
    global _wake_word_detector_instance
    if _wake_word_detector_instance is None:
        _wake_word_detector_instance = WakeWordDetector()
        
        # Add default wake words
        for config in _wake_word_detector_instance.DEFAULT_WAKE_WORDS.values():
            _wake_word_detector_instance.add_wake_word(config)
    
    return _wake_word_detector_instance
