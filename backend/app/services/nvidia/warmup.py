import asyncio
import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger("nvidia.warmup")

_warmup_loop_task: Optional[asyncio.Task] = None

# NVIDIA serverless models idle out in ~1-2 min; 4-minute pings meant the
# default model was almost always cold. Every 30s keeps TTFT at ~2-4s.
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


async def warmup_default_models(provider=None) -> None:
    """Warm the default GLM chat model once. GLM cold-starts on NVIDIA in
    ~165s so the warmup may time out; the router fallback still resolves
    coding/reasoning tasks to available models."""
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
    await asyncio.gather(*(_ping_model(provider, m) for m in targets))


async def _keep_warm_loop() -> None:
    """Periodically ping the default chat model so it never idles out.
    Pings OVERLAP: the next ping fires KEEP_WARM_INTERVAL after the previous
    one *started* (not after it finished), so a slow cold-start ping cannot
    create a >60s gap that lets the NVIDIA instance idle out."""
    from app.services.nvidia.config import TASK_ROUTES
    from app.services.nvidia.chat import NvidiaChatProvider

    provider = NvidiaChatProvider()
    fast = None
    if settings.nvidia_api_keys:
        fast = TASK_ROUTES.get("chat", {}).get("default")
    while True:
        try:
            if fast:
                from app.services.nvidia.key_manager import key_manager
                key = key_manager.get_key()
                if key is None or key.is_rate_limited or not key.is_active:
                    await asyncio.sleep(KEEP_WARM_INTERVAL)
                    continue
                ping_task = asyncio.create_task(_ping_model(provider, fast))
                # Give the ping the full interval; if it is still running when
                # the interval elapses, the next cycle starts a new ping anyway.
                try:
                    await asyncio.wait_for(asyncio.shield(ping_task), timeout=KEEP_WARM_INTERVAL)
                except asyncio.TimeoutError:
                    pass
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