"""Abstract Base Provider for Video Generation."""

from abc import ABC, abstractmethod
from typing import Optional, Tuple, Dict, Any


class BaseVideoProvider(ABC):
    """Abstract interface implemented by all video generation providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the provider service."""
        pass

    @property
    @abstractmethod
    def model_id(self) -> str:
        """Model identifier."""
        pass

    @abstractmethod
    async def generate_video(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        width: int = 1280,
        height: int = 720,
        duration_seconds: int = 5,
        fps: int = 24,
        seed: Optional[int] = None,
        reference_image_bytes: Optional[bytes] = None,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> bytes:
        """
        Executes video generation against the provider endpoint.
        Returns raw MP4 video bytes.
        Raises RuntimeError or ValueError on API rejection/failure.
        """
        pass

    @abstractmethod
    async def probe_health(self) -> Tuple[bool, str]:
        """
        Checks connectivity, API key validity, and service availability.
        Returns: (is_healthy, status_message)
        """
        pass
