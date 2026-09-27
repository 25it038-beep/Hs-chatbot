"""Video model router and provider dispatcher."""

from typing import Dict, Tuple, Optional
from app.services.video.providers.base import BaseVideoProvider
from app.services.video.providers.wan import NvidiaWanVideoProvider
from app.services.video.providers.cosmos import NvidiaCosmosVideoProvider
from app.services.video.models import model_registry


class VideoRouter:
    """Routes video requests to the correct provider implementation."""

    def __init__(self):
        self._providers: Dict[str, BaseVideoProvider] = {
            "wan-ai/wan2.2": NvidiaWanVideoProvider("wan-ai/wan2.2"),
            "nvidia/cosmos3-nano": NvidiaCosmosVideoProvider("nvidia/cosmos3-nano"),
        }

    def get_provider(self, model_id: str) -> BaseVideoProvider:
        if model_id in self._providers:
            return self._providers[model_id]

        if "cosmos" in model_id.lower():
            provider = NvidiaCosmosVideoProvider(model_id)
            self._providers[model_id] = provider
            return provider

        # Default to Wan provider
        return self._providers["wan-ai/wan2.2"]

    async def check_health(self) -> Dict[str, dict]:
        """Probes all registered video model providers."""
        results = {}
        for mid, provider in self._providers.items():
            healthy, msg = await provider.probe_health()
            results[mid] = {
                "model_id": mid,
                "provider": provider.provider_name,
                "healthy": healthy,
                "status": "ready" if healthy else "unavailable",
                "message": msg,
            }
        return results


video_router = VideoRouter()
