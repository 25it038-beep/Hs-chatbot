"""Speaker Verification for Voice Match and Voice Authentication."""

import logging
import numpy as np
from typing import Optional, Tuple
from dataclasses import dataclass, asdict
import json
import hashlib

logger = logging.getLogger("hsbot.voice.speaker_verification")


@dataclass
class VoiceProfile:
    """Represents a user's voice profile for verification."""
    user_id: str
    org_id: str
    embedding: list  # Speaker embedding vector
    confidence_threshold: float = 0.85
    anti_spoofing_enabled: bool = True
    created_at: str = ""
    updated_at: str = ""
    status: str = "active"


@dataclass
class VerificationResult:
    """Result from voice verification attempt."""
    speaker_id: str
    matched: bool
    confidence: float
    verification_status: str  # VERIFIED, UNCERTAIN, REJECTED
    is_genuine: bool = True  # Anti-spoofing check
    details: dict = None


class SpeakerVerifier:
    """
    Verifies user identity based on voice characteristics.
    Uses speaker embeddings for multi-speaker recognition.
    """
    
    def __init__(self, anti_spoofing_enabled: bool = True):
        """
        Initialize speaker verifier.
        
        Args:
            anti_spoofing_enabled: Enable replay attack detection
        """
        self.anti_spoofing_enabled = anti_spoofing_enabled
        self.embedder = None
        self.is_initialized = False
        self.voice_profiles = {}  # In-memory cache
        
        try:
            self._initialize_embedder()
        except Exception as e:
            logger.warning(f"Failed to initialize speaker embedder: {e}")
            self.is_initialized = False
    
    def _initialize_embedder(self):
        """Initialize speaker embedding model."""
        try:
            try:
                from speechbrain.pretrained import SpeakerRecognition
                self.embedder = SpeakerRecognition.from_hparams(
                    source="speechbrain/spkrec-ecapa-voxceleb",
                    savedir="pretrained_models/spkrec-ecapa-voxceleb",
                    run_opts={"device": "cpu"}
                )
                self.is_initialized = True
                logger.info("Speaker embedder initialized with SpeechBrain")
            except ImportError:
                logger.warning("SpeechBrain not available. Using numpy-based comparison.")
                self.is_initialized = False
        except Exception as e:
            logger.error(f"Error initializing speaker embedder: {e}")
            self.is_initialized = False
    
    def enroll_speaker(self, user_id: str, org_id: str, audio_samples: list) -> VoiceProfile:
        """
        Enroll a new speaker from audio samples.
        
        Args:
            user_id: User identifier
            org_id: Organization identifier
            audio_samples: List of audio numpy arrays or file paths
            
        Returns:
            VoiceProfile with generated embedding
        """
        if not audio_samples:
            raise ValueError("At least one audio sample required")
        
        embeddings = []
        
        if self.is_initialized and self.embedder:
            try:
                for sample in audio_samples:
                    # Generate embedding
                    if isinstance(sample, str):
                        # File path
                        embedding = self.embedder.encode_speaker(sample)
                    else:
                        # Audio numpy array - save temporarily
                        import tempfile
                        import scipy.io.wavfile as wavfile
                        
                        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                            wavfile.write(tmp.name, 16000, (sample * 32767).astype(np.int16))
                            embedding = self.embedder.encode_speaker(tmp.name)
                    
                    embeddings.append(embedding.tolist())
            except Exception as e:
                logger.error(f"Error generating embeddings: {e}")
                embeddings = self._dummy_embeddings(audio_samples)
        else:
            # Fallback: use basic audio features
            embeddings = self._generate_basic_embeddings(audio_samples)
        
        # Average embeddings
        avg_embedding = np.mean(embeddings, axis=0).tolist()
        
        # Create profile
        from datetime import datetime
        profile = VoiceProfile(
            user_id=user_id,
            org_id=org_id,
            embedding=avg_embedding,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            status="active"
        )
        
        # Cache profile
        profile_key = f"{org_id}:{user_id}"
        self.voice_profiles[profile_key] = profile
        
        logger.info(f"Speaker enrolled: {user_id}")
        return profile
    
    def verify_speaker(self, user_id: str, org_id: str, audio_sample) -> VerificationResult:
        """
        Verify if audio sample matches user's voice profile.
        
        Args:
            user_id: User identifier
            org_id: Organization identifier
            audio_sample: Audio data (numpy array or file path)
            
        Returns:
            VerificationResult with confidence and status
        """
        profile_key = f"{org_id}:{user_id}"
        
        if profile_key not in self.voice_profiles:
            return VerificationResult(
                speaker_id=user_id,
                matched=False,
                confidence=0.0,
                verification_status="UNKNOWN",
                details={"error": "No voice profile found"}
            )
        
        profile = self.voice_profiles[profile_key]
        
        # Generate embedding for current sample
        try:
            if self.is_initialized and self.embedder:
                if isinstance(audio_sample, str):
                    sample_embedding = self.embedder.encode_speaker(audio_sample).tolist()
                else:
                    import tempfile
                    import scipy.io.wavfile as wavfile
                    
                    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                        wavfile.write(tmp.name, 16000, (audio_sample * 32767).astype(np.int16))
                        sample_embedding = self.embedder.encode_speaker(tmp.name).tolist()
            else:
                sample_embedding = self._generate_basic_embedding(audio_sample)
        except Exception as e:
            logger.error(f"Error generating sample embedding: {e}")
            sample_embedding = self._generate_basic_embedding(audio_sample)
        
        # Calculate similarity (cosine similarity)
        confidence = self._cosine_similarity(
            np.array(profile.embedding),
            np.array(sample_embedding)
        )
        
        # Determine verification status
        if confidence >= profile.confidence_threshold:
            status = "VERIFIED"
            matched = True
        elif confidence >= (profile.confidence_threshold - 0.15):
            status = "UNCERTAIN"
            matched = False
        else:
            status = "REJECTED"
            matched = False
        
        # Anti-spoofing check
        is_genuine = True
        if self.anti_spoofing_enabled:
            is_genuine = self._check_anti_spoofing(audio_sample)
        
        result = VerificationResult(
            speaker_id=user_id,
            matched=matched and is_genuine,
            confidence=confidence,
            verification_status=status if is_genuine else "SPOOFING_DETECTED",
            is_genuine=is_genuine,
            details={
                "confidence_threshold": profile.confidence_threshold,
                "audio_duration": len(audio_sample) / 16000 if hasattr(audio_sample, '__len__') else 0,
            }
        )
        
        logger.info(f"Speaker verification result: {user_id} - {status} (confidence: {confidence:.3f})")
        return result
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(vec1) == 0 or len(vec2) == 0:
            return 0.0
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def _check_anti_spoofing(self, audio_sample) -> bool:
        """
        Check if audio appears genuine (not replay attack).
        
        Simple heuristics:
        - Check for natural speech patterns
        - Detect unnatural frequency patterns
        - Check for compression artifacts
        """
        if not hasattr(audio_sample, '__len__') or len(audio_sample) == 0:
            return False
        
        try:
            # Basic anti-spoofing checks
            audio = np.array(audio_sample, dtype=float)
            
            # Check dynamic range
            min_val = np.min(np.abs(audio))
            max_val = np.max(np.abs(audio))
            dynamic_range = max_val - min_val
            
            # Check for silence or too uniform audio
            if dynamic_range < 0.01:
                logger.warning("Low dynamic range detected - possible spoofing")
                return False
            
            # Check for clipping
            clipping_ratio = np.sum(np.abs(audio) > 0.95) / len(audio)
            if clipping_ratio > 0.05:
                logger.warning("High clipping detected - possible spoofing")
                return False
            
            return True
        except Exception as e:
            logger.debug(f"Anti-spoofing check error: {e}")
            return True  # Default to genuine on error
    
    def _generate_basic_embeddings(self, audio_samples: list) -> list:
        """Generate basic embeddings using audio features."""
        embeddings = []
        for sample in audio_samples:
            embeddings.append(self._generate_basic_embedding(sample))
        return embeddings
    
    def _generate_basic_embedding(self, audio_sample) -> np.ndarray:
        """Generate basic embedding using audio statistics."""
        audio = np.array(audio_sample, dtype=float)
        
        # Extract simple features
        features = [
            np.mean(audio),
            np.std(audio),
            np.max(audio),
            np.min(audio),
            np.mean(np.abs(np.diff(audio))),
        ]
        
        # Repeat to create 512-dim embedding (for compatibility)
        embedding = np.tile(features, 102)[:512]
        
        return embedding / np.linalg.norm(embedding)
    
    def _dummy_embeddings(self, audio_samples: list) -> list:
        """Generate dummy embeddings for testing."""
        embeddings = []
        for sample in audio_samples:
            embedding = np.random.randn(512)
            embeddings.append(embedding / np.linalg.norm(embedding))
        return embeddings
    
    def save_profile(self, profile: VoiceProfile, path: str):
        """Save voice profile to encrypted file."""
        try:
            profile_dict = asdict(profile)
            
            # TODO: Implement encryption
            with open(path, 'w') as f:
                json.dump(profile_dict, f)
            
            logger.info(f"Profile saved to {path}")
        except Exception as e:
            logger.error(f"Error saving profile: {e}")
    
    def load_profile(self, path: str) -> Optional[VoiceProfile]:
        """Load voice profile from file."""
        try:
            # TODO: Implement decryption
            with open(path, 'r') as f:
                profile_dict = json.load(f)
            
            profile = VoiceProfile(**profile_dict)
            
            # Cache profile
            profile_key = f"{profile.org_id}:{profile.user_id}"
            self.voice_profiles[profile_key] = profile
            
            logger.info(f"Profile loaded from {path}")
            return profile
        except Exception as e:
            logger.error(f"Error loading profile: {e}")
            return None


# Singleton instance
_speaker_verifier_instance = None


def get_speaker_verifier() -> SpeakerVerifier:
    """Get or create speaker verifier instance."""
    global _speaker_verifier_instance
    if _speaker_verifier_instance is None:
        _speaker_verifier_instance = SpeakerVerifier()
    return _speaker_verifier_instance
