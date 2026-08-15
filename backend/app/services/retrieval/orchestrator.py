"""Retrieval orchestrator (sections 1-21).

Pipeline: normalize -> cache lookup -> route -> querygen -> parallel search
-> dedupe+rank -> selective parallel fetch -> extract -> rerank -> images
(parallel) -> build context -> cache write.

Every stage is measured (section 15); failures degrade to partial results
(section 6); freshness bypasses stale reads (sections 7, 12).
"""

import asyncio
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Optional

from loguru import logger

from . import router as retrouter
from .cache import retrieval_cache
from .config import retrieval_config as cfg
from .fetcher import PageFetcher
from .imagefilter import filter_relevant
from .normalize import cache_scope, normalize_query
from .observability import StageTimer, build_perf
from .providers import SearchResult, provider_pool
from .querygen import generate_queries, generate_video_queries
from .ranker import dedupe_results, score_results, select_top
from .reranker import build_evidence
from .videos import (
    VideoResult,
    VideoRetriever,
    dedupe_videos,
    filter_videos,
    format_videos_md,
    rank_videos,
)

StatusCallback = Optional[Callable[[str], Awaitable[None]]]

_DEPTH = {"simple": cfg.TOP_RESULTS_SIMPLE, "medium": cfg.TOP_RESULTS_MEDIUM, "complex": cfg.TOP_RESULTS_MAX}


@dataclass
class RetrievalResult:
    context: Optional[str]
    images_md: str
    videos_md: str = ""
    videos: list[VideoResult] = field(default_factory=list)
    sources: list[dict] = field(default_factory=list)
    perf: dict = field(default_factory=dict)
    from_cache: bool = False
    query: str = ""


class RetrievalOrchestrator:
    def __init__(self, pool=None) -> None:
        self._pool = pool if pool is not None else provider_pool
        self._fetcher = PageFetcher()
        self._videos = VideoRetriever(pool=self._pool)

    async def _notify(self, cb: StatusCallback, msg: str) -> None:
        if cb is not None:
            try:
                await cb(msg)
            except Exception:
                pass

    async def retrieve(
        self,
        query: str,
        *,
        with_images: bool = False,
        with_videos: bool = False,
        force_fresh: bool = False,
        status_cb: StatusCallback = None,
        max_results: Optional[int] = None,
    ) -> RetrievalResult:
        timer = StageTimer()
        timer.start("routing")

        route = retrouter.classify(query)
        current = route["current"]
        complexity = route["complexity"]
        types = route["types"]
        video_intent = retrouter.classify_video_intent(query)
        timer.stop("routing")

        if not route["needs_search"]:
            return RetrievalResult(context=None, images_md="", perf=build_perf(timer), query=query)

        normalized = normalize_query(query)
        scope = "news" if "news" in types and current else cache_scope(query)
        timer.start("cache")
        cached = None if force_fresh or current else await retrieval_cache.get(normalized, scope)
        timer.stop("cache")

        if cached and cached.get("context") is not None:
            # Cached context: reuse it. If images were requested but are not
            # cached, refresh ONLY the images — never refetch the pipeline.
            cached_images = cached.get("images_md") or ""
            if with_images and not cached_images:
                await self._notify(status_cb, "Fetching relevant images...")
                timer.start("images")
                cached_images = await self._search_images(query, [normalized], status_cb)
                timer.stop("images")
                cached["images_md"] = cached_images
                try:
                    await retrieval_cache.set(normalized, scope, cached)
                except Exception:
                    pass
            logger.debug("retrieval cache HIT scope={} query={!r}", scope, query)
            perf = build_perf(timer, extra={"cache_ms": timer.elapsed.get("cache", 0.0), "from_cache": True})
            return RetrievalResult(
                context=cached.get("context"),
                images_md=cached_images,
                videos_md=cached.get("videos_md") or "",
                sources=cached.get("sources", []),
                perf=perf,
                from_cache=True,
                query=query,
            )

        # ── Query generation ──
        timer.start("querygen")
        queries = generate_queries(query, complexity)
        timer.stop("querygen")
        await self._notify(status_cb, "Searching the web for updated data...")

        # ── Parallel search (section 2) ──
        timer.start("search")
        need_news = "news" in types or current
        need_videos = with_videos and video_intent in ("required", "recommended")
        limit = max_results or min(cfg.CANDIDATES_PER_PROVIDER, 30)

        results_lists: list[list[SearchResult]] = []
        video_task = None
        try:
            async with asyncio.timeout(cfg.SEARCH_TIMEOUT_S + 2):
                search_jobs = [self._pool.text(q, limit, "web") for q in queries]
                if need_news:
                    search_jobs.append(self._pool.news(queries[0], min(limit, 20)))
                results_lists = await asyncio.gather(*search_jobs)
        except (TimeoutError, asyncio.TimeoutError):
            results_lists = []
        timer.stop("search")
        if need_videos:
            # Video search runs as its OWN task (parallel with the fetch phase
            # below) so it never competes with the text providers for the
            # Tavily/DDGS semaphores (section 26).
            video_task = asyncio.create_task(
                self._videos.search(generate_video_queries(query)[0], cfg.VIDEO_CANDIDATES)
            )

        candidates: list[SearchResult] = []
        for idx, rl in enumerate(results_lists):
            if rl is None:
                continue
            q = queries[idx] if idx < len(queries) else queries[0]
            for r in rl:
                r.extra["query"] = q
                candidates.append(r)

        if not candidates:
            logger.warning("search returned zero candidates for {!r}", query)
            if video_task is not None:
                video_task.cancel()
            return RetrievalResult(context=None, images_md="", perf=build_perf(timer), query=query)

        # ── Dedupe + rank + select (sections 4, 13, 18) ──
        timer.start("ranking")
        deduped = dedupe_results(candidates)
        ranked = score_results(deduped, query, current=current, complexity=complexity)
        top = select_top(ranked, _DEPTH[complexity])
        timer.stop("ranking")
        await self._notify(status_cb, f"Found {len(deduped)} sources, reading the most relevant...")

        # ── Parallel page fetching + extraction under one global deadline ──
        # (section 6: one slow source must never block the answer)
        # Images run concurrently with page fetches (sections 2, 11).
        fetched: list[dict] = []
        context: Optional[str] = None
        sources: list[dict] = []
        images_md = ""
        urls = [r.url for r in top if r.url]
        timer.start("fetch")
        image_task = None
        if with_images or "images" in types:
            image_task = asyncio.create_task(self._search_images(query, queries, status_cb))
        if urls:
            deadline = max(cfg.GLOBAL_TIMEOUT_S - max(timer.elapsed.get("search", 0.0) / 1000, 1.0), 2.0)
            try:
                # Inner budget is slightly tighter than the outer deadline so
                # completed pages survive when a slow page burns the budget.
                async with asyncio.timeout(deadline):
                    fetched = await self._fetcher.fetch_many(urls, budget_s=deadline - 0.5, scope=scope)
            except (TimeoutError, asyncio.TimeoutError):
                logger.warning("global fetch deadline exceeded for {!r} ({}/{} fetched)", query, len(fetched), len(urls))
        if image_task is not None:
            try:
                images_md = await asyncio.wait_for(image_task, timeout=cfg.SEARCH_TIMEOUT_S + 2)
            except Exception:
                images_md = ""
        timer.stop("fetch")

        # ── Extract + rerank (sections 9, 10) ──
        timer.start("extraction")
        timer.start("reranking")
        context, sources = build_evidence(fetched, query)
        timer.stop("extraction")
        timer.stop("reranking")

        # ── Videos (section 26): collect the parallel video task results after
        # the fetch phase so the bursty video search never delays the context.
        videos_md = ""
        video_list: list[VideoResult] = []
        if need_videos and video_task is not None:
            try:
                video_rows = await asyncio.wait_for(
                    asyncio.shield(video_task), timeout=cfg.SEARCH_TIMEOUT_S + 2
                )
            except Exception:
                video_rows = []
            if video_rows:
                await self._notify(status_cb, "Finding relevant videos...")
                video_list = rank_videos(dedupe_videos(filter_videos(video_rows, query)), query)
                videos_md = format_videos_md(video_list, cfg.MAX_VIDEOS)

        # ── Cache write (section 7) ──
        if context or videos_md:
            await retrieval_cache.set(normalized, scope, {
                "context": context,
                "images_md": images_md,
                "videos_md": videos_md,
                "sources": sources,
            })

        perf = build_perf(timer, extra={"cache_ms": timer.elapsed.get("cache", 0.0)})
        logger.info("retrieval done query={!r} stages={}", query, perf)
        return RetrievalResult(
            context=context,
            images_md=images_md,
            videos_md=videos_md,
            videos=video_list,
            sources=sources,
            perf=perf,
            query=query,
        )

    async def _search_images(self, query: str, queries: list[str], status_cb: StatusCallback) -> str:
        await self._notify(status_cb, "Fetching relevant images...")
        timer_start = None
        try:
            async with asyncio.timeout(cfg.SEARCH_TIMEOUT_S + 2):
                results = await self._pool.images(queries[0], cfg.MAX_IMAGES * 4)
        except (TimeoutError, asyncio.TimeoutError):
            return ""
        if not results:
            return ""
        relevant = filter_relevant(results, queries[0]) or filter_relevant(results, query)
        seen: set[str] = set()
        md_parts: list[str] = []
        for r in relevant:
            key = (r.image_url or r.url).split("?")[0]
            if key in seen:
                continue
            seen.add(key)
            md_parts.append(f"![{r.title.strip()[:120] or 'image'}]({key})")
            if len(md_parts) >= cfg.MAX_IMAGES:
                break
        return "\n\n".join(md_parts)


retrieval_orchestrator = RetrievalOrchestrator()
