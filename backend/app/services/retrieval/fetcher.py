"""Parallel page fetcher (sections 5, 6, 16, 21).

One shared httpx.AsyncClient with connection pooling + keep-alive.
Per-request timeout, manual redirect validation (SSRF-safe), retry for
transient failures, size caps, failure isolation.
"""

import asyncio
import re
from typing import Optional
from urllib.parse import urljoin

import httpx
from loguru import logger

from .config import retrieval_config as cfg
from .providers import tavily_extractor
from .security import is_safe_url
from .selenium_fetcher import fetch_dynamic, get_cached_page, is_selenium_available

_CLIENT: Optional[httpx.AsyncClient] = None
_CLIENT_LOCK = asyncio.Lock()


async def _get_client() -> httpx.AsyncClient:
    global _CLIENT
    if _CLIENT is not None:
        return _CLIENT
    async with _CLIENT_LOCK:
        if _CLIENT is None:
            _CLIENT = httpx.AsyncClient(
                timeout=httpx.Timeout(
                    cfg.FETCH_TIMEOUT_S,
                    connect=cfg.CONNECT_TIMEOUT_S,
                    read=cfg.FETCH_TIMEOUT_S,
                    write=5.0,
                    pool=5.0,
                ),
                limits=httpx.Limits(max_connections=cfg.MAX_FETCH_CONCURRENCY + 4, max_keepalive_connections=cfg.MAX_FETCH_CONCURRENCY),
                headers={
                    "User-Agent": cfg.USER_AGENT,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate",
                },
                follow_redirects=False,
                trust_env=False,
            )
    return _CLIENT


async def shutdown() -> None:
    global _CLIENT
    if _CLIENT is not None:
        await _CLIENT.aclose()
        _CLIENT = None


def _check_content_type(ct: str) -> bool:
    ct = (ct or "").lower()
    if not ct or "html" in ct or "text" in ct or "xml" in ct or "json" in ct or "markdown" in ct:
        return True
    return False


async def _fetch_once(client: httpx.AsyncClient, url: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Returns (html_or_text, final_url, error)."""
    if not is_safe_url(url):
        return None, None, "blocked"
    current = url
    for _ in range(cfg.MAX_REDIRECTS):
        try:
            async with client.stream("GET", current) as resp:
                if resp.status_code in (301, 302, 303, 307, 308):
                    loc = resp.headers.get("location")
                    if not loc:
                        return None, current, f"redirect-no-location-{resp.status_code}"
                    next_url = urljoin(current, loc)
                    if next_url.startswith(("data:", "javascript:", "file:", "gopher:")):
                        return None, current, "blocked-scheme"
                    if not is_safe_url(next_url):
                        return None, current, "blocked-redirect"
                    current = next_url
                    continue
                if resp.status_code == 404:
                    return None, current, "404"
                if resp.status_code >= 500:
                    return None, current, f"http-{resp.status_code}"
                if not _check_content_type(resp.headers.get("content-type", "")):
                    return None, current, "unsupported-type"
                length = resp.headers.get("content-length")
                if length and int(length) > cfg.MAX_PAGE_BYTES:
                    return None, current, "too-large"
                chunks: list[bytes] = []
                total = 0
                async for chunk in resp.aiter_bytes():
                    total += len(chunk)
                    if total > cfg.MAX_PAGE_BYTES:
                        return None, current, "too-large"
                    chunks.append(chunk)
                raw = b"".join(chunks)
                charset = resp.encoding or "utf-8"
                try:
                    text = raw.decode(charset, errors="replace")
                except LookupError:
                    text = raw.decode("utf-8", errors="replace")
                return text[: cfg.MAX_PAGE_BYTES], current, None
        except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError, httpx.RemoteProtocolError) as e:
            return None, current, f"network-{type(e).__name__}"
        except httpx.HTTPStatusError as e:
            return None, current, f"http-{e.response.status_code}"
        except Exception as e:
            return None, current, type(e).__name__
    return None, current, "too-many-redirects"


async def fetch_page(url: str, retries: Optional[int] = None) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Fetch one page. Returns (content, final_url, error). Failure isolated."""
    client = await _get_client()
    tries = cfg.FETCH_RETRIES if retries is None else retries
    for attempt in range(tries + 1):
        try:
            content, final_url, err = await asyncio.wait_for(
                _fetch_once(client, url), timeout=cfg.FETCH_TIMEOUT_S + cfg.CONNECT_TIMEOUT_S + 2
            )
        except asyncio.TimeoutError:
            err, content, final_url = "timeout", None, url
            content = None
        if content is not None or err in ("blocked", "404", "blocked-scheme", "blocked-redirect", "unsupported-type", "too-large", "too-many-redirects"):
            return content, final_url, err
        if attempt < tries:
            await asyncio.sleep(0.25 * (attempt + 1))
    return None, url, err


_EXTRACT_SKIP = {
    "blocked",
    "blocked-scheme",
    "blocked-redirect",
    "404",
    "too-large",
    "too-many-redirects",
    "timeout",
    "deadline",
    "unsupported-type",
}


def _extract_candidate(err: Optional[str]) -> bool:
    """Only bot-blocked/malformed failures are worth a Tavily extract retry."""
    return bool(err) and err not in _EXTRACT_SKIP and not err.startswith("http-5")


def _selenium_candidate(content: Optional[str], err: Optional[str]) -> bool:
    """Selenium only for JS-rendered/bot-blocked/thin pages, never for
    404/unsafe/oversized ones (a browser changes none of those)."""
    if not cfg.SELENIUM_ENABLED or not is_selenium_available():
        return False
    if err is not None:
        return _extract_candidate(err)
    # HTTP succeeded but body too thin to answer — classic SPA/JS shell.
    return content is not None and len(content) < cfg.SELENIUM_MIN_HTML_CHARS


class PageFetcher:
    def __init__(self, concurrency: Optional[int] = None) -> None:
        self._sem = asyncio.Semaphore(concurrency or cfg.MAX_FETCH_CONCURRENCY)
        self._extract_left = cfg.TAVILY_EXTRACT_MAX
        self._selenium_left = cfg.SELENIUM_MAX_FALLBACKS

    async def fetch_many(
        self,
        urls: list[str],
        budget_s: Optional[float] = None,
        scope: str = "general",
    ) -> list[dict]:
        """Fetch in parallel; on deadline, keep finished pages, drop the rest.

        Uses asyncio.wait so a slow page can never discard the fast results
        (section 6: partial results beat no results). Pages the direct fetch
        cannot read (bot-blocked / JS-heavy / thin shells) fall back to
        Tavily /extract, then to a headless-browser render (section 27) —
        both capped per request so neither budget is ever exhausted.
        `scope` (news/current/general/docs) drives page-cache freshness.
        """
        self._extract_left = cfg.TAVILY_EXTRACT_MAX
        self._selenium_left = cfg.SELENIUM_MAX_FALLBACKS

        async def _one(url: str):
            async with self._sem:
                content, final_url, err = await fetch_page(url)
                if content is None and cfg.TAVILY_EXTRACT_ENABLED and self._extract_left > 0 and _extract_candidate(err):
                    self._extract_left -= 1
                    try:
                        extracted = await asyncio.wait_for(
                            tavily_extractor.extract_single(url),
                            timeout=cfg.TAVILY_EXTRACT_TIMEOUT_S + 2,
                        )
                    except asyncio.TimeoutError:
                        extracted = None
                    except Exception:
                        extracted = None
                    if extracted:
                        content, final_url, err = extracted, url, None

                # Headless-browser fallback (section 27): only for pages the
                # fast path provably can't read, budgeted and time-boxed.
                used_selenium = False
                if (
                    self._selenium_left > 0
                    and _selenium_candidate(content, err)
                    and await get_cached_page(url, scope) is None
                ):
                    self._selenium_left -= 1
                    used_selenium = True
                    try:
                        dyn = await asyncio.wait_for(
                            fetch_dynamic(url, scope=scope),
                            timeout=cfg.SELENIUM_TOTAL_TIMEOUT_S + 2,
                        )
                    except (asyncio.TimeoutError, TimeoutError):
                        dyn = {"success": False}
                    except Exception:
                        dyn = {"success": False}
                    if dyn.get("success"):
                        content, final_url, err = dyn["content"], dyn.get("url") or url, None
                return {
                    "url": url,
                    "final_url": final_url or url,
                    "content": content,
                    "error": err,
                    "method": "selenium" if used_selenium and err is None else "http",
                }

        tasks = {asyncio.create_task(_one(u)): u for u in urls}
        done, pending = await asyncio.wait(tasks, timeout=budget_s)
        for t in pending:
            t.cancel()
        results: list[dict] = []
        for t, url in tasks.items():
            try:
                results.append(t.result())
            except (asyncio.CancelledError, asyncio.TimeoutError):
                results.append({"url": url, "final_url": url, "content": None, "error": "deadline"})
            except Exception:
                results.append({"url": url, "final_url": url, "content": None, "error": "failed"})
        return results


page_fetcher = PageFetcher()
