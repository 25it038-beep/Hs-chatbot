"""Fast and Pro web search engine (sections 5, 8, 10, 11, 12, 42)."""

import asyncio
import time
from typing import Awaitable, Callable, Optional

from app.services.retrieval.providers import provider_pool
from app.services.retrieval.videos import VideoRetriever, dedupe_videos, filter_videos, format_videos_md, rank_videos
from app.web.cache import search_cache
from app.web.citation import build_research_context, format_sources_markdown
from app.web.conflict import ConflictDetector
from app.web.deduplication import deduplicate_sources
from app.web.evidence import EvidenceEngine
from app.web.models import SearchMode, SearchRequest, SearchResultBundle
from app.web.query_planner import QueryPlanner
from app.web.search_router import determine_search_mode
from app.web.source_ranker import SourceRanker
from app.web.source_reader import SourceReader

StatusCallback = Optional[Callable[[str], Awaitable[None]]]


class WebSearchService:
    """Perplexity-level Web Search Service supporting FAST and PRO search modes."""

    def __init__(self):
        self._planner = QueryPlanner()
        self._ranker = SourceRanker()
        self._reader = SourceReader()
        self._evidence_engine = EvidenceEngine()
        self._conflict_detector = ConflictDetector()
        self._pool = provider_pool
        self._videos = VideoRetriever(pool=self._pool)

    async def _notify(self, cb: StatusCallback, msg: str) -> None:
        if cb:
            try:
                await cb(msg)
            except Exception:
                pass

    @staticmethod
    def needs_web_search(query: str) -> bool:
        mode, _ = determine_search_mode(query)
        return mode != SearchMode.NONE

    async def search(
        self,
        query: str,
        mode: Optional[SearchMode] = None,
        max_sources: int = 6,
        with_images: bool = False,
        with_videos: bool = False,
        status_cb: StatusCallback = None,
        chat_history: Optional[list] = None,
        location: Optional[str] = None,
        as_of: Optional[str] = None,
    ) -> SearchResultBundle:
        start_t = time.time()
        await self._notify(status_cb, "Analyzing question & planning search...")

        # 1. Determine mode and constraints
        effective_mode, constraints = determine_search_mode(query, user_override=mode.value if mode else None)
        if location and not constraints.get("region"):
            constraints["region"] = location

        if effective_mode == SearchMode.NONE:
            return SearchResultBundle(
                mode=SearchMode.NONE,
                original_query=query,
                resolved_query=query,
                structured_context="",
                duration_ms=(time.time() - start_t) * 1000,
            )

        # 2. Check cache
        cached = search_cache.get(query, effective_mode.value, constraints.get("region"))
        if cached:
            return cached

        # 3. Plan multi-angle queries
        queries = self._planner.plan_queries(
            query,
            mode=effective_mode,
            constraints=constraints,
            chat_history=chat_history,
        )

        await self._notify(status_cb, f"Searching {len(queries)} query angles...")

        # 4. Parallel search execution
        search_jobs = [self._pool.text(q, limit=12, kind="web") for q in queries]
        if "latest" in query.lower() or "news" in query.lower() or "today" in query.lower():
            search_jobs.append(self._pool.news(queries[0], limit=10))

        raw_results_nested = await asyncio.gather(*search_jobs, return_exceptions=True)
        raw_candidates = []
        for res in raw_results_nested:
            if isinstance(res, list):
                raw_candidates.extend(res)

        if not raw_candidates:
            return SearchResultBundle(
                mode=effective_mode,
                original_query=query,
                resolved_query=queries[0] if queries else query,
                structured_context="",
                duration_ms=(time.time() - start_t) * 1000,
            )

        # 5. Deduplicate and rank sources
        deduped = deduplicate_sources(raw_candidates)
        ranked_sources = self._ranker.rank_and_select(
            deduped,
            query=query,
            max_sources=max_sources,
            max_per_domain=2,
        )

        await self._notify(status_cb, f"Reading evidence from {len(ranked_sources)} authoritative sources...")

        # 6. Deep source reading & evidence extraction
        passages_map = await self._reader.read_sources(ranked_sources, query=query, budget_s=7.0)
        evidence = self._evidence_engine.assemble_evidence(passages_map, ranked_sources)

        # 7. Discrepancy & conflict detection
        conflicts = self._conflict_detector.detect_conflicts(evidence, ranked_sources)

        await self._notify(status_cb, "Cross-checking facts & synthesizing answer...")

        # 8. Video search (if requested)
        videos_md = ""
        if with_videos:
            try:
                vid_rows = await self._videos.search(queries[0], max_results=4)
                if vid_rows:
                    ranked_vids = rank_videos(dedupe_videos(filter_videos(vid_rows, query)), query)
                    videos_md = format_videos_md(ranked_vids, limit=3)
            except Exception:
                pass

        # 9. Build structured citation context
        structured_context = build_research_context(ranked_sources, evidence, conflicts)
        sources_md = format_sources_markdown(ranked_sources)

        bundle = SearchResultBundle(
            mode=effective_mode,
            original_query=query,
            resolved_query=queries[0] if queries else query,
            structured_context=structured_context,
            sources=ranked_sources,
            sources_md=sources_md,
            evidence=evidence,
            conflicts=conflicts,
            videos_md=videos_md,
            duration_ms=(time.time() - start_t) * 1000,
        )

        search_cache.set(query, effective_mode.value, bundle, region=constraints.get("region"))
        return bundle
