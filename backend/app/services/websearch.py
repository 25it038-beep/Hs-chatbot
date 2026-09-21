"""Unified facade for the Perplexity-Level Web Search and Deep Research Engine.

Integrates:
- Fast Search (simple queries)
- Pro Search (comparative, multi-angle)
- Deep Research (iterative planning, gap-filling, comprehensive report synthesis)
- Reusable across Normal Chat, Agent Mode, Voice Mode, and Artifact Generation.
"""

import asyncio
import re
from typing import Awaitable, Callable, Optional, List, Dict

from app.web.models import SearchMode, SearchResultBundle
from app.web.research import ResearchService
from app.web.search import WebSearchService as WebSearchCore
from app.web.search_router import determine_search_mode


def extract_image_subject(query: str) -> str:
    """Strip intent clauses, keeping the image-search subject."""
    q = query.strip()
    q = re.sub(
        r"(?i)\s+(?:and|also|plus|then)\s+(?:show|display|include|add|get|find)\s+"
        r"(?:me\s+)?(?:some\s+|relevant\s+|related\s+)?(?:images?|pictures?|photos?|pics?)\s*[.?!]*$",
        "",
        q,
    )
    q = re.sub(
        r"(?i)^\s*(?:please\s+|pls\s+)?(?:(?:can you|could you)\s+)?"
        r"(?:explain|research|learn about|tell me about|what is|what are|how does|how do|"
        r"compare|contrast|analyze|describe|summarize)\s+",
        "",
        q,
    )
    q = re.sub(r"(?i)^\s*(?:an?\s+|the\s+)", "", q)
    return q.strip() or query.strip()


async def _noop_videos() -> str:
    return ""


class WebSearchService:
    """Unified Perplexity-level Web Search Service."""

    def __init__(self, max_results: int = 6, cache_days: int = 1):
        self.max_results = max_results
        self.cache_days = cache_days
        self._core = WebSearchCore()
        self._research = ResearchService()

    @staticmethod
    def needs_web_search(query: str) -> bool:
        mode, _ = determine_search_mode(query)
        return mode != SearchMode.NONE

    async def search(
        self,
        query: str,
        max_results: Optional[int] = None,
        with_images: bool = False,
        with_videos: bool = False,
        status_cb: Optional[Callable[[str], Awaitable[None]]] = None,
        location: Optional[str] = None,
        as_of: Optional[str] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> Optional[str]:
        if not query or not query.strip():
            return None

        mode, _ = determine_search_mode(query)
        if mode == SearchMode.DEEP:
            bundle = await self._research.conduct_research(
                query,
                depth="comprehensive",
                max_sources=max_results or 10,
                status_cb=status_cb,
                chat_history=chat_history,
            )
        else:
            bundle = await self._core.search(
                query,
                mode=mode,
                max_sources=max_results or self.max_results,
                with_images=with_images,
                with_videos=with_videos,
                status_cb=status_cb,
                chat_history=chat_history,
                location=location,
                as_of=as_of,
            )
        return bundle.structured_context or None

    async def search_with_images(
        self,
        query: str,
        max_results: Optional[int] = None,
        with_videos: bool = False,
        status_cb: Optional[Callable[[str], Awaitable[None]]] = None,
        location: Optional[str] = None,
        as_of: Optional[str] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> tuple[Optional[str], str]:
        if not query or not query.strip():
            return None, ""
        bundle = await self._core.search(
            query,
            max_sources=max_results or self.max_results,
            with_images=True,
            with_videos=with_videos,
            status_cb=status_cb,
            location=location,
            as_of=as_of,
            chat_history=chat_history,
        )
        return bundle.structured_context or None, bundle.images_md

    async def fetch_images_markdown(
        self,
        query: str,
        max_results: Optional[int] = None,
        status_cb: Optional[Callable[[str], Awaitable[None]]] = None,
        location: Optional[str] = None,
        as_of: Optional[str] = None,
    ) -> str:
        from app.services.retrieval import retrieval_orchestrator
        if not query or not query.strip():
            return ""
        result = await retrieval_orchestrator.retrieve(
            query,
            with_images=True,
            status_cb=status_cb,
            max_results=max_results or self.max_results,
            location=location,
            as_of=as_of,
        )
        return result.images_md

    async def retrieve_for_chat(
        self,
        message: str,
        *,
        force_images: bool,
        with_videos: bool = False,
        status_cb: Optional[Callable[[str], Awaitable[None]]] = None,
        location: Optional[str] = None,
        as_of: Optional[str] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> tuple[Optional[str], str, str]:
        """Run the full chat-path retrieval with Fast, Pro, or Deep Research."""
        mode, _ = determine_search_mode(message)

        if mode == SearchMode.DEEP:
            bundle = await self._research.conduct_research(
                message,
                depth="comprehensive",
                max_sources=12,
                status_cb=status_cb,
                chat_history=chat_history,
            )
            vids = await self.fetch_videos_markdown(message, status_cb=status_cb) if with_videos else ""
            return bundle.structured_context or None, "", vids

        if force_images:
            img_query = extract_image_subject(message)
            if self.needs_web_search(message):
                ctx, md, vids = await asyncio.gather(
                    self.search(
                        message,
                        with_images=False,
                        with_videos=with_videos,
                        status_cb=status_cb,
                        location=location,
                        as_of=as_of,
                        chat_history=chat_history,
                    ),
                    self.fetch_images_markdown(img_query, status_cb=status_cb, location=location, as_of=as_of),
                    self.fetch_videos_markdown(message, status_cb=status_cb) if with_videos else _noop_videos(),
                )
                return ctx, md, vids
            videos_md = await self.fetch_videos_markdown(message, status_cb=status_cb) if with_videos else ""
            return None, await self.fetch_images_markdown(img_query, status_cb=status_cb, location=location, as_of=as_of), videos_md

        bundle = await self._core.search(
            message,
            mode=mode,
            max_sources=self.max_results,
            with_images=True,
            with_videos=with_videos,
            status_cb=status_cb,
            location=location,
            as_of=as_of,
            chat_history=chat_history,
        )
        return bundle.structured_context or None, bundle.images_md, bundle.videos_md

    async def fetch_videos_markdown(
        self,
        query: str,
        max_results: Optional[int] = None,
        status_cb: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> str:
        from app.services.retrieval.videos import video_retriever
        if not query or not query.strip():
            return ""
        return await video_retriever.retrieve_markdown(query, status_cb)


__all__ = ["WebSearchService", "ResearchService", "extract_image_subject"]
