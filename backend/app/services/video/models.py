"""Video model registry, resolution mapping, and capability definitions."""

from typing import Dict, List, Optional, Tuple
from app.services.video.schemas import VideoModelCapability, VideoMode


class VideoModelRegistry:
    """Registry of verified NVIDIA video generation models and constraints."""

    _MODELS: Dict[str, VideoModelCapability] = {
        "wan-ai/wan2.2": VideoModelCapability(
            model_id="wan-ai/wan2.2",
            name="Wan 2.2 Video (NVIDIA NIM)",
            provider="nvidia",
            modes=[VideoMode.TEXT_TO_VIDEO.value, VideoMode.IMAGE_TO_VIDEO.value],
            resolutions=["480p", "720p"],
            aspect_ratios=["16:9", "9:16", "1:1"],
            durations=[5, 8],
            default_fps=24,
            description="High-fidelity diffusion video generation model supporting text and image conditioning.",
            status="available"
        ),
        "nvidia/cosmos3-nano": VideoModelCapability(
            model_id="nvidia/cosmos3-nano",
            name="Cosmos 3 Nano (NVIDIA Foundation)",
            provider="nvidia",
            modes=[VideoMode.TEXT_TO_VIDEO.value, VideoMode.IMAGE_TO_VIDEO.value],
            resolutions=["720p", "1080p"],
            aspect_ratios=["16:9", "9:16", "1:1", "4:3"],
            durations=[3, 5, 10],
            default_fps=24,
            description="NVIDIA Cosmos physical AI world model for cinematic video synthesis with physics-aware motion.",
            status="available"
        ),
    }

    @classmethod
    def get_model(cls, model_id: str) -> Optional[VideoModelCapability]:
        return cls._MODELS.get(model_id)

    @classmethod
    def list_models(cls) -> List[VideoModelCapability]:
        return list(cls._MODELS.values())

    @classmethod
    def default_model_id(cls) -> str:
        return "wan-ai/wan2.2"

    @classmethod
    def is_valid_model(cls, model_id: str) -> bool:
        return model_id in cls._MODELS

    @classmethod
    def calculate_dimensions(cls, resolution: str, aspect_ratio: str) -> Tuple[int, int]:
        """Calculates pixel dimensions (width, height) aligned to 16-pixel macroblocks."""
        res_map = {
            "480p": {
                "16:9": (848, 480),
                "9:16": (480, 848),
                "1:1": (480, 480),
                "4:3": (640, 480),
            },
            "720p": {
                "16:9": (1280, 720),
                "9:16": (720, 1280),
                "1:1": (720, 720),
                "4:3": (960, 720),
            },
            "1080p": {
                "16:9": (1920, 1080),
                "9:16": (1080, 1920),
                "1:1": (1080, 1080),
                "4:3": (1440, 1080),
            },
        }

        dim = res_map.get(resolution, {}).get(aspect_ratio)
        if dim:
            return dim
        return (1280, 720)


model_registry = VideoModelRegistry()
