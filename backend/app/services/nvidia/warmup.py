import asyncio
import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger("nvidia.warmup")

_warmup_loop_task: Optional[asyncio.Task] = None

KEEP_WARM_INTERVAL = 30.0


async def _ping_model(provider, model_key: str) -> None:
    """Send a minimal request so NVIDIA keeps the model warm on later calls."""
    try:
        await asyncio.wait_for(
            provider.generate(
                messages=[{"role": "user", "content": "ping"}],
                model=model_key,
                max_tokens=1,
                temperature=0.0,
            ),
            timeout=60.0,
        )
        logger.info("Model warmup OK: %s", model_key)
    except asyncio.TimeoutError:
        logger.warning("Model warmup timed out: %s", model_key)
    except Exception as e:  # noqa: BLE001
        logger.warning("Model warmup failed for %s: %s", model_key, e)


def _get_targets() -> set[str]:
    from app.services.nvidia.config import TASK_ROUTES

    targets = set()
    for task in ("chat", "coding", "reasoning"):
        route = TASK_ROUTES.get(task, {})
        default = route.get("default")
        if default:
            targets.add(default)
        for fb in route.get("fallback", []):
            targets.add(fb)
    targets.discard(None)
    return targets


async def warmup_default_models(provider=None) -> None:
    """Warm the default chat model once. Fast models respond quickly; slow
    ones (glm) time out after 60s and are left to cool — NVIDIA cold-starts
    them on demand with router fallback kicking in."""
    if not settings.nvidia_api_keys:
        logger.info("No NVIDIA API keys configured; skipping warmup")
        return

    from app.services.nvidia.chat import NvidiaChatProvider

    provider = provider or NvidiaChatProvider()
    await asyncio.gather(*(_ping_model(provider, m) for m in _get_targets()))


async def _keep_warm_loop() -> None:
    """Periodically ping the fast default chat model to prevent NVIDIA
    cold-start latency. Only llama-3.1-70b is kept hot; slower models are
    warmed once at startup and on demand (router fallback)."""
    from app.services.nvidia.config import TASK_ROUTES

    from app.services.nvidia.chat import NvidiaChatProvider

    provider = NvidiaChatProvider()
    while True:
        try:
            fast = TASK_ROUTES.get("chat", {}).get("default")
            if fast:
                await _ping_model(provider, fast)
        except Exception as e:  # noqa: BLE001
            logger.warning("Keep-warm cycle error: %s", e)
        await asyncio.sleep(KEEP_WARM_INTERVAL)


async def start_warmup() -> None:
    """Start the background warmup without blocking server startup."""
    global _warmup_loop_task
    if _warmup_loop_task and not _warmup_loop_task.done():
        return

    async def _run() -> None:
        try:
            await warmup_default_models()
        except Exception as e:  # noqa: BLE001
            logger.warning("Startup warmup error: %s", e)
        try:
            await _keep_warm_loop()
        except asyncio.CancelledError:
            return
        except Exception as e:  # noqa: BLE001
            logger.warning("Keep-warm loop stopped: %s", e)

    _warmup_loop_task = asyncio.create_task(_run())


async def stop_warmup() -> None:
    global _warmup_loop_task
    if _warmup_loop_task:
        _warmup_loop_task.cancel()
        try:
            await _warmup_loop_task
        except (asyncio.CancelledError, Exception):  # noqa: BLE001
            pass
        _warmup_loop_task = None