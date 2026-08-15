"""Search providers (sections 2, 17, 20).

Primary: DuckDuckGo (text / news / images) via ddgs.
Image: DuckDuckGo images + Wikimedia Commons.
Fallback chain handled by the orchestrator; every provider is isolated so a
failure degrades to partial results instead of failing the request.
"""

import asyncio
import re
import time
from dataclasses import dataclass, field
from typing import Optional

from loguru import logger

from .config import retrieval_config as cfg


@dataclass
class SearchResult:
    title: str = ""
    url: str = ""
    body: str = ""
    source: str = "ddgs"  # provider tag
    kind: str = "web"  # web | news | images | videos | docs
    image_url: str = ""  # filled for images
    published: str = ""
    score: float = 0.0
    extra: dict = field(default_factory=dict)


class SearchProvider:
    async def search(self, query: str, limit: int, kind: str) -> list[SearchResult]:
        raise NotImplementedError


def _run_sync(fn, *args):
    return asyncio.get_event_loop().run_in_executor(None, fn, *args)


class DDGSProvider(SearchProvider):
    async def search(self, query: str, limit: int, kind: str) -> list[SearchResult]:
        from ddgs import DDGS

        kind = "web" if kind not in ("web", "news", "videos") else kind

        async def _attempt():
            def _do():
                with DDGS() as ddgs:
                    if kind == "news":
                        return list(ddgs.news(query, max_results=limit))
                    if kind == "videos":
                        return list(ddgs.videos(query, max_results=limit))
                    return list(ddgs.text(query, max_results=limit))

            return await asyncio.wait_for(_run_sync(_do), timeout=cfg.SEARCH_TIMEOUT_S)

        t0 = time.perf_counter()
        try:
            rows = await _attempt()
        except Exception as e:
            # Retry only when ddgs failed FAST (network blip); a slow
            # timeout smells like rate-limiting, retrying burns the budget.
            if time.perf_counter() - t0 < 2.5:
                await asyncio.sleep(0.4)
                try:
                    rows = await _attempt()
                except Exception as e2:
                    logger.warning("ddgs.{} search failed for {!r} (retried): {}", kind, query, e2)
                    return []
            else:
                logger.warning("ddgs.{} search failed for {!r} (timeout): {}", kind, query, e)
                return []

        results = []
        for r in rows or []:
            url = (r.get("href") or r.get("url") or r.get("page") or "").strip()
            title = (r.get("title") or "").strip()
            body = (r.get("body") or r.get("description") or "").strip()
            if not url or (not title and not body):
                continue
            if not re.match(r"^https?://", url):
                continue
            results.append(
                SearchResult(
                    title=title[:200],
                    url=url[:500],
                    body=body[:500],
                    source="ddgs",
                    kind="videos" if kind == "videos" else "news" if kind == "news" else "web",
                    published=(r.get("date") or r.get("published") or ""),
                )
            )
            if len(results) >= limit:
                break
        return results


class DDGSImageProvider(SearchProvider):
    async def search(self, query: str, limit: int, kind: str) -> list[SearchResult]:
        from ddgs import DDGS

        try:
            def _do():
                with DDGS() as ddgs:
                    return list(ddgs.images(query, max_results=limit))

            rows = await asyncio.wait_for(_run_sync(_do), timeout=cfg.SEARCH_TIMEOUT_S)
        except Exception as e:
            logger.warning("ddgs.images failed for {!r}: {}", query, e)
            return []

        results = []
        for r in rows or []:
            url = (r.get("image") or "").split("?")[0]
            src_page = (r.get("url") or "").strip()
            title = (r.get("title") or "").strip()
            if not url or not re.match(r"^https?://", url):
                continue
            results.append(
                SearchResult(
                    title=title[:200],
                    url=src_page[:500],
                    body="",
                    source="ddgs-images",
                    kind="images",
                    image_url=url,
                )
            )
            if len(results) >= limit:
                break
        return results


class WikimediaImageProvider(SearchProvider):
    """Keyless Commons search — titles must match query keywords (relevance gate)."""

    API = "https://commons.wikimedia.org/w/api.php"
    HEADERS = {
        "User-Agent": "HSBot/1.0 (https://github.com/25it038-beep/Hs-chatbot; contact: hsbot@example.com)"
    }

    async def search(self, query: str, limit: int, kind: str) -> list[SearchResult]:
        import httpx

        try:
            async with httpx.AsyncClient(timeout=8.0, headers=self.HEADERS) as client:
                resp = await client.get(
                    self.API,
                    params={
                        "action": "query",
                        "generator": "search",
                        "gsrsearch": query,
                        "gsrnamespace": "6",
                        "gsrlimit": str(min(limit * 3, 20)),
                        "prop": "imageinfo",
                        "iiprop": "url|mime",
                        "iiurlwidth": "480",
                        "format": "json",
                    },
                )
                resp.raise_for_status()
                pages = resp.json().get("query", {}).get("pages", {})
        except Exception as e:
            logger.warning("wikimedia image search failed for {!r}: {}", query, e)
            return []

        keywords = [k for k in re.split(r"[\s,]+", query.lower()) if len(k) > 2]
        results = []
        for page in pages.values():
            info = (page.get("imageinfo") or [{}])[0]
            url = (info.get("thumburl") or info.get("url") or "").split("?")[0]
            mime = info.get("mime", "")
            title = page.get("title", "").replace("File:", "")
            if not url or (mime and not mime.startswith("image/")):
                continue
            if keywords and not any(k in title.lower() for k in keywords):
                continue
            results.append(
                SearchResult(
                    title=title.strip()[:200],
                    url="",
                    body="",
                    source="wikimedia",
                    kind="images",
                    image_url=url,
                )
            )
            if len(results) >= limit:
                break
        return results


class TavilyProvider(SearchProvider):
    """Primary text/news provider (sections 2, 12, 20).

    Reliable, scored results with published dates. Two API keys: the primary
    is used until it is rejected (401/403) or exhausted (429/5xx), then the
    fallback key takes over for the rest of the process lifetime.
    """

    URL = "https://api.tavily.com/search"
    _active_key: Optional[str] = None
    _lock = asyncio.Lock()

    async def _get_key(self) -> str:
        if TavilyProvider._active_key is None:
            async with TavilyProvider._lock:
                if TavilyProvider._active_key is None:
                    TavilyProvider._active_key = cfg.TAVILY_API_KEY
        return TavilyProvider._active_key

    async def _rotate(self) -> str:
        async with TavilyProvider._lock:
            if TavilyProvider._active_key == cfg.TAVILY_API_KEY and cfg.TAVILY_FALLBACK_API_KEY:
                logger.warning("tavily: rotating to fallback API key")
                TavilyProvider._active_key = cfg.TAVILY_FALLBACK_API_KEY
            return TavilyProvider._active_key

    async def search(self, query: str, limit: int, kind: str) -> list[SearchResult]:
        import httpx

        key = await self._get_key()
        payload = {
            "query": query,
            "max_results": min(limit, cfg.TAVILY_MAX_RESULTS),
            "search_depth": "basic",
            "include_answer": False,
        }
        if kind == "news":
            payload["topic"] = "news"
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=cfg.TAVILY_TIMEOUT_S) as client:
                    resp = await client.post(self.URL, json=payload, headers=headers)
                if resp.status_code in (401, 403, 429):
                    if resp.status_code != 429:  # 429 = key fine, limit hit; retry once
                        logger.warning("tavily key rejected (http {}), rotating", resp.status_code)
                        key = await self._rotate()
                        headers["Authorization"] = f"Bearer {key}"
                        continue
                    if attempt == 0:
                        await asyncio.sleep(0.5)
                        continue
                    logger.warning("tavily rate limited (429) for {!r}", query)
                    return []
                resp.raise_for_status()
                data = resp.json()
                break
            except Exception as e:
                logger.warning("tavily search failed for {!r}: {}", query, e)
                return []

        results = []
        for r in data.get("results", []):
            url = (r.get("url") or "").strip()
            title = (r.get("title") or "").strip()
            content = (r.get("content") or "").strip()
            if not url or (not title and not content):
                continue
            res = SearchResult(
                title=title[:200],
                url=url[:500],
                body=content[:500],
                source="tavily",
                kind="web" if kind != "news" else "news",
                published=(r.get("published_date") or ""),
            )
            res.extra["tavily_score"] = float(r.get("score") or 0.0)
            results.append(res)
            if len(results) >= min(limit, cfg.TAVILY_MAX_RESULTS):
                break
        if not results:
            logger.warning("tavily returned zero results for {!r} (kind={})", query, kind)
        return results


class WikipediaProvider(SearchProvider):
    """Keyless fallback text provider (section 20) — runs concurrently with DDGS."""

    API = "https://en.wikipedia.org/w/api.php"

    async def search(self, query: str, limit: int, kind: str) -> list[SearchResult]:
        import httpx

        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                resp = await client.get(
                    self.API,
                    params={
                        "action": "query",
                        "list": "search",
                        "srsearch": query,
                        "srlimit": str(min(limit, 12)),
                        "format": "json",
                        "utf8": "1",
                    },
                )
                resp.raise_for_status()
                hits = resp.json().get("query", {}).get("search", [])
        except Exception as e:
            logger.warning("wikipedia search failed for {!r}: {}", query, e)
            return []

        results = []
        for h in hits:
            title = (h.get("title") or "").strip()
            snippet = re.sub(r"<[^>]+>", "", h.get("snippet") or "").strip()
            if not title:
                continue
            results.append(
                SearchResult(
                    title=title[:200],
                    url=f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"[:500],
                    body=snippet[:400],
                    source="wikipedia",
                    kind="web",
                )
            )
            if len(results) >= limit:
                break
        return results


_TEXT_PROVIDER = DDGSProvider()
_WIKI_PROVIDER = WikipediaProvider()
_TAVILY_PROVIDER = TavilyProvider()
_IMAGE_PROVIDERS: list[SearchProvider] = [DDGSImageProvider(), WikimediaImageProvider()]


class ProviderPool:
    """Runs provider searches with a concurrency cap (section 17).

    Tavily (primary), DDGS and Wikipedia each get their OWN semaphore so a
    slow or blocked provider can never starve the others (sections 2, 20).
    """

    def __init__(self) -> None:
        self._sem_tavily = asyncio.Semaphore(cfg.MAX_TAVILY_CONCURRENCY)
        self._sem_ddgs = asyncio.Semaphore(cfg.MAX_SEARCH_CONCURRENCY)
        self._sem_wiki = asyncio.Semaphore(min(cfg.MAX_SEARCH_CONCURRENCY, 2))
        self._sem_images = asyncio.Semaphore(cfg.MAX_IMAGE_CONCURRENCY)

    async def _run(self, prov: SearchProvider, sem: asyncio.Semaphore, query: str, limit: int, kind: str) -> list[SearchResult]:
        async with sem:
            return await prov.search(query, limit, kind)

    async def text(self, query: str, limit: int, kind: str = "web") -> list[SearchResult]:
        # Progressive completion (section 6): wait until the PRIMARY (Tavily)
        # has answered, then give secondaries a short grace window. Slow or
        # blocked providers are cancelled so they can never stall the answer.
        t0 = time.perf_counter()
        label = {_TAVILY_PROVIDER: "tavily", _TEXT_PROVIDER: "ddgs", _WIKI_PROVIDER: "wikipedia"}
        tasks = {
            asyncio.create_task(self._run(p, sem, query, limit, kind)): p
            for p, sem in (
                (_TAVILY_PROVIDER, self._sem_tavily),
                (_TEXT_PROVIDER, self._sem_ddgs),
                (_WIKI_PROVIDER, self._sem_wiki),
            )
        }
        deadline = t0 + cfg.SEARCH_TIMEOUT_S
        pending: set = set(tasks)
        tavily_done = False
        while pending and not tavily_done:
            _, pending = await asyncio.wait(
                pending, timeout=max(deadline - time.perf_counter(), 0.05), return_when=asyncio.FIRST_COMPLETED
            )
            tavily_done = any(
                label[tasks[t]] == "tavily" and t.done() and not t.cancelled() for t in tasks
            )
        # Grace window for secondaries, or squeeze the remaining budget when
        # the primary failed/returned empty.
        primary_ok = False
        for t, p in tasks.items():
            if label[p] == "tavily" and t.done() and not t.cancelled():
                try:
                    primary_ok = bool(t.result())
                except Exception:
                    primary_ok = False
                break
        if pending:
            grace = 1.5 if primary_ok else max(deadline - time.perf_counter(), 0.05)
            _, pending = await asyncio.wait(pending, timeout=grace)
        for t in pending:
            t.cancel()
        order = [t for t in tasks]
        batches = []
        for t in order:
            try:
                batches.append(t.result() or [])
            except Exception:
                batches.append([])
        merged = [r for batch in batches for r in batch]
        if not batches or not batches[0]:
            for r in merged:
                if r.source == "wikipedia":
                    r.source = "wikipedia-fallback"
        return merged

    async def images(self, query: str, limit: int) -> list[SearchResult]:
        outs = await asyncio.gather(
            *(self._run(p, self._sem_images, query, limit, "images") for p in _IMAGE_PROVIDERS)
        )
        return [r for batch in outs for r in batch]

    async def news(self, query: str, limit: int) -> list[SearchResult]:
        return await self.text(query, limit, "news")

    async def videos(self, query: str, limit: int) -> list[SearchResult]:
        return await self._run(_TEXT_PROVIDER, self._sem_ddgs, query, limit, "videos")


provider_pool = ProviderPool()
