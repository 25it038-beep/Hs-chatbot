import asyncio
import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger("nvidia.warmup")

_warmup_loop_task: Optional[asyncio.Task] = None

# NVIDIA serverless models idle out in ~1-2 min; 4-minute pings meant the
# default model was almost always cold. Every 30s keeps TTFT at ~2-4s.
KEEP_WARM_INTERVAL = 30.0


async def _ping_model(provider, model_key: str) -> bool:
    """Send a minimal request so NVIDIA keeps the model warm on later calls.
    Returns True if successful, False otherwise."""
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
        return True
    except asyncio.TimeoutError:
        logger.warning("Model warmup timed out: %s", model_key)
    except Exception as e:  # noqa: BLE001
        logger.warning("Model warmup failed for %s: %s", model_key, e)
    return False


async def warmup_default_models(provider=None) -> None:
    """Warm the default models once. Non-blocking - failures are logged but don't block."""
    if not settings.nvidia_api_keys:
        logger.info("No NVIDIA API keys configured; skipping warmup")
        return

    from app.services.nvidia.config import TASK_ROUTES
    from app.services.nvidia.chat import NvidiaChatProvider

    provider = provider or NvidiaChatProvider()
    targets = set()
    for task in ("chat", "coding", "reasoning"):
        route = TASK_ROUTES.get(task, {})
        if route.get("default"):
            targets.add(route["default"])
        for fb in route.get("fallback", []):
            targets.add(fb)
    targets.discard(None)
    
    # Warm up models concurrently, don't fail if any fail
    results = await asyncio.gather(*(_ping_model(provider, m) for m in targets), return_exceptions=True)
    successful = sum(1 for r in results if r is True)
    logger.info("Model warmup completed: %d/%d successful", successful, len(targets))


async def _keep_warm_loop() -> None:
    """Periodically ping the fast default chat model to avoid cold-start
    latency. Fast responses come from SambaNova's DeepSeek-V3.2, so NVIDIA
    keep-warm is limited to the chat default (GLM) if configured."""
    from app.services.nvidia.config import TASK_ROUTES
    from app.services.nvidia.chat import NvidiaChatProvider

    provider = NvidiaChatProvider()
    fast = None
    if settings.nvidia_api_keys:
        fast = TASK_ROUTES.get("chat", {}).get("default")
    consecutive_failures = 0
    while True:
        try:
            if fast:
                from app.services.nvidia.key_manager import key_manager
                key = key_manager.get_key()
                if key is None or key.is_rate_limited or not key.is_active:
                    await asyncio.sleep(KEEP_WARM_INTERVAL)
                    continue
                await _ping_model(provider, fast)
                consecutive_failures = 0
        except Exception as e:  # noqa: BLE001
            consecutive_failures += 1
            logger.warning("Keep-warm cycle error: %s", e)
        # Exponential backoff on failures
        await asyncio.sleep(KEEP_WARM_INTERVAL * min(2 ** consecutive_failures, 8))


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