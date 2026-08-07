import asyncio
import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger("nvidia.warmup")

_warmup_task: Optional[asyncio.Task] = None


async def _warmup_model(provider, model_key: str) -> None:
    """Send a minimal request so NVIDIA keeps the model warm on later calls."""
    try:
        await provider.generate(
            messages=[{"role": "user", "content": "ping"}],
            model=model_key,
            max_tokens=1,
            temperature=0.1,
        )
        logger.info("Model warmup complete: %s", model_key)
    except Exception as e:  # noqa: BLE001
        logger.warning("Model warmup failed for %s: %s", model_key, e)


async def warmup_default_models() -> None:
    """Warm the default chat/coding/reasoning models in the background."""
    if not settings.nvidia_api_keys:
        logger.info("No NVIDIA API keys configured; skipping warmup")
        return

    from app.services.nvidia.chat import NvidiaChatProvider
    from app.services.nvidia.config import TASK_ROUTES

    provider = NvidiaChatProvider()

    targets = set()
    for task in ("chat", "coding", "reasoning"):
        route = TASK_ROUTES.get(task, {})
        default = route.get("default")
        if default:
            targets.add(default)
        for fb in route.get("fallback", []):
            targets.add(fb)
    targets.discard(None)

    await asyncio.gather(*(_warmup_model(provider, m) for m in targets))


async def start_warmup() -> None:
    """Start the background warmup without blocking server startup."""
    global _warmup_task
    if _warmup_task and not _warmup_task.done():
        return

    async def _run() -> None:
        try:
            await warmup_default_models()
        except Exception as e:  # noqa: BLE001
            logger.warning("Background warmup error: %s", e)

    _warmup_task = asyncio.create_task(_run())


async def stop_warmup() -> None:
    global _warmup_task
    if _warmup_task:
        _warmup_task.cancel()
        try:
            await _warmup_task
        except (asyncio.CancelledError, Exception):  # noqa: BLE001
            pass
        _warmup_task = None