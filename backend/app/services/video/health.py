"""Video generation system health and readiness verification."""

import logging
from typing import Dict, Any
from app.services.video.router import video_router
from app.services.video.models import model_registry

logger = logging.getLogger("hsbot.video.health")


class VideoHealthChecker:
    """Verifies system readiness and provider status for video generation."""

    @classmethod
    async def get_system_health(cls, running_jobs_count: int = 0) -> Dict[str, Any]:
        provider_health = await video_router.check_health()
        any_healthy = any(p["healthy"] for p in provider_health.values())

        return {
            "status": "healthy" if any_healthy else "degraded",
            "active_models": len(model_registry.list_models()),
            "running_jobs": running_jobs_count,
            "providers": provider_health,
        }


video_health = VideoHealthChecker()
