"""Universal Artifact Engine V2 (§3, §8, §15, §30).
Real, validated, production-grade file creation for General Chat.
"""

from app.services.universal_artifacts.contracts import (
    OutputIntent,
    ArtifactCategory,
    ArtifactSpec,
    ArtifactMetadata,
    ValidationResult,
)
from app.services.universal_artifacts.registry import ArtifactFormatRegistryV2
from app.services.universal_artifacts.intent_engine import (
    ResponseOutputIntentEngine,
    output_intent_engine,
)
from app.services.universal_artifacts.engine import (
    UniversalArtifactEngineV2,
)
from app.services.universal_artifacts.validator import ArtifactValidator
from app.services.universal_artifacts.converters import ArtifactConverter
from app.services.universal_artifacts.version_manager import ArtifactVersionManager
from app.services.universal_artifacts.synthesizer import UniversalArtifactSynthesizer

__all__ = [
    "OutputIntent",
    "ArtifactCategory",
    "ArtifactSpec",
    "ArtifactMetadata",
    "ValidationResult",
    "ArtifactFormatRegistryV2",
    "ResponseOutputIntentEngine",
    "output_intent_engine",
    "UniversalArtifactEngineV2",
    "ArtifactValidator",
    "ArtifactConverter",
    "ArtifactVersionManager",
    "UniversalArtifactSynthesizer",
]
