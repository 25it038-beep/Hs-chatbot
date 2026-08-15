"""Selenium dynamic-page fallback (section 27).

Selenium is NOT a search engine and never the default. It only activates
when the fast HTTP fetch chain failed or returned too little content:

    Search API -> cache -> HTTP fetch -> extract -> [Selenium] -> rerank -> LLM

Design:
- Lazy bounded browser pool (MAX_WORKERS drivers, each reused up to
  MAX_PAGES_PER_BROWSER then restarted). Selenium is blocking/sync, so every
  driver call runs in a worker thread via asyncio.to_thread; callers always
  bound it with asyncio.wait_for so a stuck browser can never block the chat.
- Headless Chrome with a lean profile (no images/extensions/downloads,
  no-sandbox for containers, eager load strategy). JavaScript stays ON —
  that is the entire point of the fallback.
- Explicit WebDriverWait for content selectors or document readyState —
  no arbitrary sleeps.
- SSRF / abuse guards: only http(s), blocks private/loopback/file hosts via
  the existing is_safe_url; page-size caps; driver.quit() in try/finally.
- Per-URL Redis/process cache with freshness scoping (news/current queries
  get short TTLs); a cached page never reopens a browser.
- Observability: every call reports the latency breakdown (http/startup/
  load/extract) so the fallback cannot silently become the slowest stage.
"""

import asyncio
import hashlib
import logging
import threading
import time
from typing import Optional

from .cache import retrieval_cache
from .config import retrieval_config as cfg
from .extractor import extract_meta, extract_text
from .security import is_safe_url

logger = logging.getLogger("retrieval.selenium")

try:  # Feature-detect: missing selenium degrades to "disabled", never crashes.
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    _SELENIUM_AVAILABLE = True
except Exception:  # pragma: no cover - environment without selenium
    webdriver = None  # type: ignore[assignment]
    _SELENIUM_AVAILABLE = False

# --------------------------------------------------------------------------
# Metrics
# --------------------------------------------------------------------------

_stats = {
    "calls": 0,
    "success": 0,
    "failures": 0,
    "http_only": 0,
    "selenium_used": 0,
    "selenium_failures": 0,
    "cache_hits": 0,
    "total_selenium_ms": 0.0,
    "started_drivers": 0,
    "quit_drivers": 0,
}
_stats_lock = threading.Lock()


def _bump(key: str, delta=1) -> None:
    with _stats_lock:
        _stats[key] = _stats.get(key, 0) + delta


def get_stats() -> dict:
    with _stats_lock:
        return dict(_stats)


def is_selenium_available() -> bool:
    return _SELENIUM_AVAILABLE and cfg.SELENIUM_ENABLED


# --------------------------------------------------------------------------
# Browser pool
# --------------------------------------------------------------------------

class _BrowserSlot:
    """One headless Chrome, reused up to MAX_PAGES_PER_BROWSER then replaced."""

    __slots__ = ("driver", "pages_used", "in_use")

    def __init__(self, driver) -> None:
        self.driver = driver
        self.pages_used = 0
        self.in_use = False


_pool: list[_BrowserSlot] = []
_pool_lock = threading.Lock()
_shutdown_flag = False


def _chrome_options() -> Optional[Options]:
    if not _SELENIUM_AVAILABLE:
        return None
    opts = Options()
    if cfg.SELENIUM_HEADLESS:
        opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--disable-background-networking")
    opts.add_argument("--disable-default-apps")
    opts.add_argument("--disable-sync")
    opts.add_argument("--no-first-run")
    opts.add_argument("--disable-notifications")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--disable-features=Translate,OptimizationHints,MediaRouter")
    opts.add_argument("--window-size=1280,900")
    opts.add_argument("--lang=en-US,en")
    if cfg.SELENIUM_BLOCK_IMAGES:
        # Images are not needed for text extraction; JS stays enabled.
        opts.add_argument("--blink-settings=imagesEnabled=false")
    opts.add_argument(f"--user-agent={cfg.USER_AGENT}")
    # Eager: return as soon as the DOM is ready; JS still executes.
    opts.page_load_strategy = "eager"
    prefs = {
        "download.prompt_for_download": False,
        "download.default_directory": "/tmp/selenium-downloads",
        "profile.default_content_setting_values.automatic_downloads": 2,
        "profile.default_content_setting_values.notifications": 2,
        "profile.default_content_setting_values.popups": 2,
        "safebrowsing.enabled": True,
    }
    opts.add_experimental_option("prefs", prefs)
    # Selenium Manager (bundled since 4.6) resolves the driver binary
    # automatically — no manual chromedriver downloads.
    return opts


def _start_driver():
    opts = _chrome_options()
    if opts is None:
        raise RuntimeError("selenium package unavailable")
    service = Service(log_output=None)
    driver = webdriver.Chrome(options=opts, service=service)
    driver.set_page_load_timeout(cfg.SELENIUM_PAGE_LOAD_TIMEOUT_S)
    driver.set_script_timeout(cfg.SELENIUM_SCRIPT_TIMEOUT_S)
    return driver


def _acquire_slot() -> Optional[_BrowserSlot]:
    """Sync acquire (called inside worker threads). Reuses warm browsers."""
    global _shutdown_flag
    with _pool_lock:
        if _shutdown_flag:
            return None
        for slot in _pool:
            if not slot.in_use and slot.pages_used < cfg.SELENIUM_MAX_PAGES_PER_BROWSER:
                slot.in_use = True
                return slot
        if len(_pool) < cfg.SELENIUM_MAX_WORKERS:
            try:
                driver = _start_driver()
            except Exception as e:
                logger.warning("failed to start chrome driver: %s", e)
                return None
            _bump("started_drivers")
            slot = _BrowserSlot(driver)
            _pool.append(slot)
            slot.in_use = True
            return slot
        return None  # pool saturated — skip rather than queue


def _release_slot(slot: Optional[_BrowserSlot], restart: bool = False) -> None:
    if slot is None:
        return
    with _pool_lock:
        if restart or slot.pages_used >= cfg.SELENIUM_MAX_PAGES_PER_BROWSER:
            try:
                slot.driver.quit()
            except Exception:
                pass
            _bump("quit_drivers")
            try:
                _pool.remove(slot)
            except ValueError:
                pass
        else:
            slot.in_use = False


# --------------------------------------------------------------------------
# Page cache (URL-scoped, freshness-aware)
# --------------------------------------------------------------------------

def _page_cache_key(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()  # noqa: S324 - cache key, not security


async def _page_cache_get(url: str, scope: str) -> Optional[dict]:
    try:
        return await retrieval_cache.get(_page_cache_key(url), scope)
    except Exception:
        return None


async def _page_cache_set(url: str, scope: str, entry: dict) -> None:
    try:
        await retrieval_cache.set(_page_cache_key(url), scope, entry)
    except Exception:
        pass


async def get_cached_page(url: str, scope: str = "general") -> Optional[dict]:
    """Public page-cache probe (used by the fetcher before spending budget)."""
    return await _page_cache_get(url, scope)


# --------------------------------------------------------------------------
# Rendering (sync, runs in worker threads)
# --------------------------------------------------------------------------

def _render_sync(url: str, slot: _BrowserSlot) -> dict:
    """Blocking render+extract for one URL."""
    driver = slot.driver
    t0 = time.perf_counter()
    try:
        driver.get(url)
    except Exception as e:  # page-load timeout / navigation failure
        return {"success": False, "error": f"selenium-nav:{type(e).__name__}", "selenium_ms": (time.perf_counter() - t0) * 1000}

    # Explicit wait: content selector present OR DOM complete; then a short
    # bounded settle window so late-rendered text can appear.
    try:
        WebDriverWait(driver, cfg.SELENIUM_PAGE_LOAD_TIMEOUT_S).until(
            EC.any_of(
                EC.presence_of_element_located((By.CSS_SELECTOR, cfg.SELENIUM_CONTENT_SELECTOR)),
                lambda d: bool(d.execute_script("return document.readyState") == "complete"),
            )
        )
        if cfg.SELENIUM_WAIT_SETTLE_S > 0:
            end = time.perf_counter() + min(cfg.SELENIUM_WAIT_SETTLE_S, cfg.SELENIUM_TOTAL_TIMEOUT_S)
            last_len = 0
            while time.perf_counter() < end:
                try:
                    body_len = len(driver.execute_script("return document.body ? document.body.innerText : ''") or "")
                except Exception:
                    body_len = 0
                if body_len > 0 and body_len == last_len:
                    break
                last_len = body_len
                time.sleep(0.15)
    except Exception:
        pass  # selector never appeared — still extract whatever rendered

    try:
        title = driver.title or ""
        page_source = driver.page_source or ""
    except Exception:
        page_source, title = "", ""
    extract_start = time.perf_counter()
    content = extract_text(page_source) if page_source else ""
    extraction_ms = (time.perf_counter() - extract_start) * 1000
    slot.pages_used += 1

    if not content or len(content) < cfg.SELENIUM_MIN_CONTENT_CHARS:
        return {
            "success": False,
            "error": "selenium-thin-content",
            "title": title,
            "content": "",
            "extraction_ms": extraction_ms,
            "selenium_ms": (time.perf_counter() - t0) * 1000,
        }
    return {
        "success": True,
        "title": title[:300],
        "content": content,
        "canonical": url,
        "extraction_ms": extraction_ms,
        "selenium_ms": (time.perf_counter() - t0) * 1000,
    }


# --------------------------------------------------------------------------
# Public async API
# --------------------------------------------------------------------------

_sems: dict[int, asyncio.Semaphore] = {}


async def _get_sem() -> asyncio.Semaphore:
    """Per-event-loop semaphore: asyncio primitives bind to a loop on first
    use, and uvicorn tests/reloads can create several loops over time."""
    loop = asyncio.get_running_loop()
    key = id(loop)
    sem = _sems.get(key)
    if sem is None:
        sem = asyncio.Semaphore(cfg.SELENIUM_MAX_WORKERS)
        _sems[key] = sem
    return sem


async def fetch_dynamic(
    url: str,
    *,
    scope: str = "general",
) -> dict:
    """Selenium-only render path. Returns the structured result dict."""
    _bump("calls")
    t0 = time.perf_counter()
    out: dict = {
        "success": False,
        "url": url,
        "title": "",
        "content": None,
        "method": "selenium",
        "fallback_used": True,
        "latency_ms": 0.0,
        "breakdown": {"http_fetch_ms": 0.0, "selenium_ms": 0.0, "extraction_ms": 0.0},
        "error": None,
    }

    if not _SELENIUM_AVAILABLE or not cfg.SELENIUM_ENABLED:
        out["error"] = "selenium-disabled"
        out["latency_ms"] = (time.perf_counter() - t0) * 1000
        return out
    if not is_safe_url(url):
        out["error"] = "blocked"
        out["latency_ms"] = (time.perf_counter() - t0) * 1000
        return out

    # 1. Page cache (URL-scoped; news/current scope = short TTL via ttl_for)
    cached = await _page_cache_get(url, scope)
    if cached and cached.get("content"):
        _bump("cache_hits")
        out.update(
            {
                "success": True,
                "title": cached.get("title", ""),
                "content": cached["content"],
                "method": cached.get("method", "selenium"),
                "fallback_used": cached.get("fallback_used", True),
                "latency_ms": (time.perf_counter() - t0) * 1000,
                "error": None,
                "from_cache": True,
            }
        )
        return out

    # 2. Bounded async render (worker thread + hard total timeout).
    # Startup (driver acquire; may download chromedriver on first run) gets
    # its own grace so a cold browser never burns the page budget. The slot
    # lifecycle is owned entirely by _render's finally, so a caller that
    # times out cannot race another thread on the same driver.
    sem = await _get_sem()
    holder: list[Optional[_BrowserSlot]] = [None]

    def _acquire_into() -> None:
        holder[0] = _acquire_slot()

    async def _reclaim_late_start() -> None:
        # Startup timed out but the thread is still starting a driver; claim
        # it once it finishes so a browser can never leak in_use in the pool.
        while holder[0] is None:
            await asyncio.sleep(0.2)
        _release_slot(holder[0], restart=True)

    async with sem:
        startup_ok = True
        try:
            await asyncio.wait_for(
                asyncio.to_thread(_acquire_into), timeout=cfg.SELENIUM_STARTUP_TIMEOUT_S
            )
        except (asyncio.TimeoutError, TimeoutError):
            startup_ok = False
            asyncio.create_task(_reclaim_late_start())
        slot = holder[0]
        if not startup_ok or slot is None:
            out["error"] = "selenium-pool-saturated"
            out["latency_ms"] = (time.perf_counter() - t0) * 1000
            return out

        def _render() -> dict:
            result: dict = {"success": False, "error": "selenium-unknown"}
            try:
                result = _render_sync(url, slot)
            except Exception as e:
                result = {"success": False, "error": f"selenium:{type(e).__name__}"}
            finally:
                _release_slot(slot, restart=not result.get("success"))
            return result

        try:
            result = await asyncio.wait_for(asyncio.to_thread(_render), timeout=cfg.SELENIUM_TOTAL_TIMEOUT_S)
        except (asyncio.TimeoutError, TimeoutError):
            # The thread keeps running and releases its slot when done.
            result = {"success": False, "error": "selenium-timeout"}
        except Exception as e:
            result = {"success": False, "error": f"selenium:{type(e).__name__}"}

    _bump("selenium_used")
    if result.get("success"):
        _bump("success")
        _bump("total_selenium_ms", result.get("selenium_ms", 0.0))
        out.update(
            {
                "success": True,
                "title": result.get("title", ""),
                "content": result["content"],
                "error": None,
            }
        )
        out["breakdown"]["selenium_ms"] = result.get("selenium_ms", 0.0)
        out["breakdown"]["extraction_ms"] = result.get("extraction_ms", 0.0)
        try:
            await _page_cache_set(url, scope, {
                "url": url,
                "canonical": result.get("canonical", url),
                "title": result.get("title", ""),
                "content": result["content"],
                "method": "selenium",
                "fallback_used": True,
                "fetched_at": time.time(),
                "content_hash": hashlib.sha1(result["content"].encode("utf-8")).hexdigest(),
            })
        except Exception:
            pass
    else:
        _bump("failures")
        _bump("selenium_failures")
        out["error"] = result.get("error", "selenium-unknown")
        out["breakdown"]["selenium_ms"] = result.get("selenium_ms", 0.0)

    out["latency_ms"] = (time.perf_counter() - t0) * 1000
    return out


async def fetch_resource(
    url: str,
    use_browser_fallback: bool = True,
    scope: str = "general",
) -> dict:
    """Clean public interface: HTTP first, Selenium fallback (see module doc).

    Returns structured data per the API contract, e.g.
    {"success": true, "url": ..., "title": ..., "content": ...,
     "method": "http" | "selenium", "fallback_used": bool, "latency_ms": int}
    """
    from .fetcher import fetch_page

    t0 = time.perf_counter()
    http_ms = 0.0
    # Cache short-circuit (avoids the HTTP round-trip too)
    if use_browser_fallback:
        cached = await _page_cache_get(url, scope)
        if cached and cached.get("content"):
            _bump("cache_hits")
            return {
                "success": True,
                "url": url,
                "title": cached.get("title", ""),
                "content": cached["content"],
                "method": cached.get("method", "http"),
                "fallback_used": cached.get("fallback_used", False),
                "latency_ms": (time.perf_counter() - t0) * 1000,
                "from_cache": True,
            }
    try:
        content, final_url, err = await asyncio.wait_for(
            fetch_page(url), timeout=cfg.FETCH_TIMEOUT_S + cfg.CONNECT_TIMEOUT_S + 2
        )
    except (asyncio.TimeoutError, TimeoutError):
        content, final_url, err = None, url, "timeout"
    http_ms = (time.perf_counter() - t0) * 1000

    if content and len(content) >= cfg.SELENIUM_MIN_HTML_CHARS:
        return {
            "success": True,
            "url": url,
            "title": extract_meta(content).get("title", ""),
            "content": extract_text(content),
            "method": "http",
            "fallback_used": False,
            "latency_ms": http_ms,
            "breakdown": {"http_fetch_ms": http_ms, "selenium_ms": 0.0, "extraction_ms": 0.0},
        }

    _bump("http_only")
    if not use_browser_fallback or not _SELENIUM_AVAILABLE or not cfg.SELENIUM_ENABLED:
        return {
            "success": False,
            "url": url,
            "title": "",
            "content": None,
            "method": "http",
            "fallback_used": False,
            "latency_ms": http_ms,
            "error": err or "thin-content",
        }

    dyn = await fetch_dynamic(url, scope=scope)
    dyn["breakdown"]["http_fetch_ms"] = http_ms
    dyn["latency_ms"] = (time.perf_counter() - t0) * 1000
    return dyn


async def shutdown() -> None:
    """Quit every browser. Called from the FastAPI lifespan on shutdown."""
    global _shutdown_flag
    with _pool_lock:
        _shutdown_flag = True
        slots, _pool[:] = _pool[:], []
    for slot in slots:
        try:
            slot.driver.quit()
        except Exception:
            pass
        _bump("quit_drivers")
