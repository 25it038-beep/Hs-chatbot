"""Selenium dynamic-page fallback tests (section 27 spec cases).

All tests mock the browser layer (selenium_fetcher._render_sync /
_acquire_slot / _release_slot) so no real Chrome is required — the fallback
must be verifiable in CI. Tests cover: HTTP-first ordering, error taxonomy
gating, thin-content detection, cache, budget, pool saturation, timeouts,
scope TTL wiring, shutdown, and the disabled path.
"""

import asyncio
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.retrieval import selenium_fetcher as sf
from app.services.retrieval.config import retrieval_config as cfg
from app.services.retrieval.fetcher import PageFetcher, page_fetcher


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------

def _fake_slot(driver=None) -> SimpleNamespace:
    return SimpleNamespace(driver=driver, pages_used=0, in_use=False)


@pytest.fixture(autouse=True)
def _reset_state():
    with sf._pool_lock:
        sf._pool[:] = []
        sf._shutdown_flag = False
    with sf._stats_lock:
        for k in sf._stats:
            sf._stats[k] = 0.0 if k.endswith("ms") else 0
    sf.retrieval_cache._memory._data.clear()  # isolate per-test page cache
    yield


@pytest.fixture
def fake_render(monkeypatch):
    """Patch the sync render step; return value decided per-test.
    Also stubs is_safe_url (no DNS in tests) while keeping the SSRF-samples
    blocked so the safety tests still exercise the guard."""

    def _patch(result):
        monkeypatch.setattr(sf, "_render_sync", lambda url, slot: dict(result))
        monkeypatch.setattr(sf, "_acquire_slot", lambda: _fake_slot())
        monkeypatch.setattr(sf, "_release_slot", lambda slot, restart=False: None)
        monkeypatch.setattr(
            sf,
            "is_safe_url",
            lambda url: url.startswith("https://")
            and not any(b in url for b in ("127.0.0.1", "localhost", "192.168", "file:")),
        )
        return sf

    return _patch


def _render_ok(text="Rendered body with enough characters " * 20, title="Selenium Page"):
    return {"success": True, "title": title, "content": text, "canonical": "https://x.test/", "extraction_ms": 1.0, "selenium_ms": 50.0}


# --------------------------------------------------------------------------
# 1. Disabled paths
# --------------------------------------------------------------------------

async def test_selenium_disabled_env(fake_render):
    fake_render(_render_ok())
    with patch.object(sf.cfg, "SELENIUM_ENABLED", False):
        out = await sf.fetch_dynamic("https://x.test/page")
        assert out["success"] is False
        assert out["error"] == "selenium-disabled"
        assert out["fallback_used"] is True
        assert sf._stats["selenium_used"] == 0


async def test_selenium_missing_package(monkeypatch):
    monkeypatch.setattr(sf, "_SELENIUM_AVAILABLE", False)
    out = await sf.fetch_dynamic("https://x.test/page")
    assert out["error"] == "selenium-disabled"


# --------------------------------------------------------------------------
# 2. URL safety (SSRF)
# --------------------------------------------------------------------------

async def test_unsafe_url_blocked_before_browser(fake_render):
    fake_render(_render_ok())
    for bad in ("http://127.0.0.1/admin", "http://localhost:8080", "file:///etc/passwd", "http://192.168.1.10/x"):
        out = await sf.fetch_dynamic(bad)
        assert out["success"] is False, bad
        assert out["error"] == "blocked", bad
        assert sf._stats["selenium_used"] == 0, bad


# --------------------------------------------------------------------------
# 3. Success / failure / timeout paths
# --------------------------------------------------------------------------

async def test_selenium_success(fake_render):
    fake_render(_render_ok())
    out = await sf.fetch_dynamic("https://x.test/page")
    assert out["success"] is True
    assert out["method"] == "selenium"
    assert out["fallback_used"] is True
    assert "Rendered body" in out["content"]
    assert out["title"] == "Selenium Page"
    assert sf._stats["success"] == 1
    assert sf._stats["selenium_used"] == 1


async def test_selenium_failure_preserves_error(fake_render):
    fake_render({"success": False, "error": "selenium-thin-content", "content": ""})
    out = await sf.fetch_dynamic("https://x.test/page")
    assert out["success"] is False
    assert out["error"] == "selenium-thin-content"
    assert sf._stats["selenium_failures"] == 1


async def test_selenium_navigation_failure(fake_render):
    fake_render({"success": False, "error": "selenium-nav:TimeoutException", "selenium_ms": 8000})
    out = await sf.fetch_dynamic("https://x.test/page")
    assert out["error"] == "selenium-nav:TimeoutException"
    assert out["breakdown"]["selenium_ms"] == 8000


async def test_selenium_hard_timeout(monkeypatch):
    def _hanging_render(url, slot):  # runs in a worker thread; sleeps past the bound
        time.sleep(1.5)
        return dict(_render_ok())

    monkeypatch.setattr(sf, "_render_sync", _hanging_render)
    monkeypatch.setattr(sf, "_acquire_slot", lambda: _fake_slot())
    monkeypatch.setattr(sf, "_release_slot", lambda slot, restart=False: None)
    monkeypatch.setattr(
        sf,
        "is_safe_url",
        lambda url: url.startswith("https://") and "127.0.0.1" not in url,
    )
    with patch.object(sf.cfg, "SELENIUM_TOTAL_TIMEOUT_S", 0.05):
        out = await sf.fetch_dynamic("https://x.test/page")
    assert out["success"] is False
    assert out["error"] == "selenium-timeout"


async def test_pool_saturated_skips(fake_render, monkeypatch):
    fake_render(_render_ok())
    monkeypatch.setattr(sf, "_acquire_slot", lambda: None)
    out = await sf.fetch_dynamic("https://x.test/page")
    assert out["success"] is False
    assert out["error"] == "selenium-pool-saturated"


# --------------------------------------------------------------------------
# 4. Cache
# --------------------------------------------------------------------------

async def test_cache_hit_skips_browser(fake_render, monkeypatch):
    fake_render(_render_ok())
    await sf.fetch_dynamic("https://x.test/cached")
    assert sf._stats["selenium_used"] == 1
    calls = {"render": 0}
    monkeypatch.setattr(sf, "_render_sync", lambda url, slot: calls.update(render=calls["render"] + 1) or _render_ok())
    out = await sf.fetch_dynamic("https://x.test/cached")
    assert out["success"] is True
    assert out.get("from_cache") is True
    assert calls["render"] == 0
    assert sf._stats["cache_hits"] >= 1


async def test_cache_miss_renders(fake_render):
    fake_render(_render_ok())
    out = await sf.fetch_dynamic("https://x.test/fresh")
    assert out.get("from_cache") is None
    assert sf._stats["selenium_used"] == 1


# --------------------------------------------------------------------------
# 5. HTTP-first resource path
# --------------------------------------------------------------------------

async def test_fetch_resource_http_first(monkeypatch):
    html = "<html><head><title>Static</title></head><body><p>Plenty of static content for the fast path. " * 50 + "</p></body></html>"
    monkeypatch.setattr(
        "app.services.retrieval.fetcher.fetch_page",
        AsyncMock(return_value=(html, "https://x.test/", None)),
    )
    out = await sf.fetch_resource("https://x.test/")
    assert out["success"] is True
    assert out["method"] == "http"
    assert out["fallback_used"] is False
    assert "static content" in out["content"]


async def test_fetch_resource_http_thin_falls_to_browser(fake_render, monkeypatch):
    fake_render(_render_ok())
    monkeypatch.setattr(
        "app.services.retrieval.fetcher.fetch_page",
        AsyncMock(return_value=("<div id='app'></div>", "https://x.test/spa", None)),
    )
    out = await sf.fetch_resource("https://x.test/spa")
    assert out["success"] is True
    assert out["method"] == "selenium"
    assert out["fallback_used"] is True


async def test_fetch_resource_http_failure_falls_to_browser(fake_render, monkeypatch):
    fake_render(_render_ok())
    monkeypatch.setattr(
        "app.services.retrieval.fetcher.fetch_page",
        AsyncMock(return_value=(None, None, "network-TimeoutException")),
    )
    out = await sf.fetch_resource("https://x.test/bot")
    assert out["method"] == "selenium"
    assert out["success"] is True


async def test_fetch_resource_no_browser_flag(fake_render, monkeypatch):
    fake_render(_render_ok())
    monkeypatch.setattr(
        "app.services.retrieval.fetcher.fetch_page",
        AsyncMock(return_value=(None, None, "network-TimeoutException")),
    )
    out = await sf.fetch_resource("https://x.test/bot", use_browser_fallback=False)
    assert out["success"] is False
    assert out["error"] == "network-TimeoutException"


# --------------------------------------------------------------------------
# 6. PageFetcher integration (error taxonomy gating)
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "err, expects_selenium",
    [
        ("network-TimeoutException", True),   # retryable -> browser
        ("http-403", True),                   # bot-blocked -> browser
        ("blocked", False),                   # unsafe URL -> never
        ("404", False),                       # gone -> never
        ("too-large", False),                 # oversized -> never
        ("unsupported-type", False),          # not a page -> never
        ("http-500", False),                  # server fault, not page fault
    ],
)
async def test_fetcher_taxonomy(monkeypatch, err, expects_selenium):
    calls = {"selenium": 0}

    async def _fetch_page(url, retries=None):
        return (None, url, err)

    async def _fake_fetch_dynamic(url, scope="general"):
        calls["selenium"] += 1
        return dict(_render_ok())

    monkeypatch.setattr("app.services.retrieval.fetcher.fetch_page", _fetch_page)
    monkeypatch.setattr("app.services.retrieval.fetcher.fetch_dynamic", _fake_fetch_dynamic)
    monkeypatch.setattr("app.services.retrieval.fetcher.get_cached_page", AsyncMock(return_value=None))
    with patch.object(cfg, "TAVILY_EXTRACT_ENABLED", False):
        results = await PageFetcher(concurrency=4).fetch_many(["https://x.test/a"])
    assert calls["selenium"] == (1 if expects_selenium else 0), err
    if expects_selenium:
        assert results[0]["content"] is not None
        assert results[0]["method"] == "selenium"
    else:
        assert results[0]["error"] == err


async def test_fetcher_thin_content_goes_to_selenium(monkeypatch):
    calls = {"selenium": 0}

    async def _fetch_page(url, retries=None):
        return ("<div id='app'>JS shell</div>", url, None)  # thin

    async def _fake_fetch_dynamic(url, scope="general"):
        calls["selenium"] += 1
        return dict(_render_ok())

    monkeypatch.setattr("app.services.retrieval.fetcher.fetch_page", _fetch_page)
    monkeypatch.setattr("app.services.retrieval.fetcher.fetch_dynamic", _fake_fetch_dynamic)
    monkeypatch.setattr("app.services.retrieval.fetcher.get_cached_page", AsyncMock(return_value=None))
    results = await PageFetcher(concurrency=4).fetch_many(["https://x.test/spa"])
    assert calls["selenium"] == 1
    assert results[0]["content"] is not None


async def test_fetcher_budget_capped(monkeypatch):
    calls = {"selenium": 0}

    async def _fetch_page(url, retries=None):
        return (None, url, "http-403")

    async def _fake_fetch_dynamic(url, scope="general"):
        calls["selenium"] += 1
        return dict(_render_ok())

    monkeypatch.setattr("app.services.retrieval.fetcher.fetch_page", _fetch_page)
    monkeypatch.setattr("app.services.retrieval.fetcher.fetch_dynamic", _fake_fetch_dynamic)
    monkeypatch.setattr("app.services.retrieval.fetcher.get_cached_page", AsyncMock(return_value=None))
    with patch.object(cfg, "TAVILY_EXTRACT_ENABLED", False):
        with patch.object(cfg, "SELENIUM_MAX_FALLBACKS", 2):
            urls = [f"https://x.test/{i}" for i in range(6)]
            results = await PageFetcher(concurrency=6).fetch_many(urls)
    assert calls["selenium"] == 2
    ok = [r for r in results if r["content"] is not None]
    assert len(ok) == 2


async def test_fetcher_cached_page_not_re_rendered(monkeypatch):
    calls = {"selenium": 0}

    async def _fetch_page(url, retries=None):
        return (None, url, "http-403")

    async def _fake_fetch_dynamic(url, scope="general"):
        calls["selenium"] += 1
        return dict(_render_ok())

    async def _cached(url, scope="general"):
        return {"content": "cached page body", "title": "Cached", "method": "selenium", "fallback_used": True}

    monkeypatch.setattr("app.services.retrieval.fetcher.fetch_page", _fetch_page)
    monkeypatch.setattr("app.services.retrieval.fetcher.fetch_dynamic", _fake_fetch_dynamic)
    monkeypatch.setattr("app.services.retrieval.fetcher.get_cached_page", _cached)
    results = await PageFetcher(concurrency=4).fetch_many(["https://x.test/a"])
    assert calls["selenium"] == 0
    assert results[0]["error"] == "http-403"  # cache probe only; content still None (cache handled at dynamic layer)


# --------------------------------------------------------------------------
# 7. Scope TTL wiring + stats + shutdown
# --------------------------------------------------------------------------

async def test_scope_flows_to_cache(fake_render, monkeypatch):
    seen = {}

    async def _fake_set(key, scope, value):
        seen["scope"] = scope

    fake_render(_render_ok())
    monkeypatch.setattr(sf.retrieval_cache, "set", _fake_set)
    await sf.fetch_dynamic("https://x.test/newsy", scope="news")
    assert seen.get("scope") == "news"


async def test_stats_shape(fake_render):
    fake_render(_render_ok())
    await sf.fetch_dynamic("https://x.test/stats")
    s = sf.get_stats()
    for key in ("calls", "success", "failures", "selenium_used", "cache_hits", "started_drivers", "quit_drivers", "total_selenium_ms"):
        assert key in s


async def test_shutdown_quits_drivers(monkeypatch):
    fake = _fake_slot(driver=SimpleNamespace(quit=lambda: None))
    with sf._pool_lock:
        sf._pool.append(fake)
        sf._pool.append(_fake_slot(driver=SimpleNamespace(quit=lambda: None)))
    before = sf.get_stats()["quit_drivers"]
    await sf.shutdown()
    assert sf.get_stats()["quit_drivers"] == before + 2
    with sf._pool_lock:
        assert sf._pool == []
    await sf.shutdown()  # idempotent


# --------------------------------------------------------------------------
# 8. Concurrency: parallel renders do not exceed the worker bound
# --------------------------------------------------------------------------

async def test_concurrent_bounded_by_max_workers(fake_render, monkeypatch):
    fake_render(_render_ok())
    active = {"n": 0, "max": 0}
    lock = asyncio.Lock()

    def _tracking_render(url, slot):
        async def _body():
            async with lock:
                active["n"] += 1
                active["max"] = max(active["max"], active["n"])
            await asyncio.sleep(0.05)
            async with lock:
                active["n"] -= 1
            return dict(_render_ok())

        return asyncio.run(_body())

    monkeypatch.setattr(sf, "_render_sync", _tracking_render)
    results = await asyncio.gather(*[sf.fetch_dynamic(f"https://x.test/{i}") for i in range(6)])
    assert all(r["success"] for r in results)
    assert active["max"] <= cfg.SELENIUM_MAX_WORKERS
