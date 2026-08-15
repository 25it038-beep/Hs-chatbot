"""Facade for the retrieval pipeline (keeps the legacy WebSearchService API).

Legacy callers (nvidia_api.py, chat.py) keep working unchanged:
- needs_web_search(query)          -> lightweight route check
- search(query, max_results, with_images) -> context string (or None)
- search_with_images(query)        -> (context, images_markdown)
- fetch_images_markdown(query)     -> images_markdown
Plus optional `status_cb` for staged streaming progress (section 14).
"""

import asyncio
import re
from typing import Awaitable, Callable, Optional

from app.services.retrieval import retrieval_orchestrator
from app.services.retrieval.router import classify


def extract_image_subject(query: str) -> str:
    """Strip intent clauses, keeping the image-search subject (e.g. 'Explain quantum
    computing and show relevant images' -> 'quantum computing')."""
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


def _needs_web_search(query: str) -> bool:
    if not query or not query.strip():
        return False
    return classify(query)["needs_search"]


async def _noop_videos() -> str:
    return ""


class WebSearchService:
    """Delegates to the retrieval orchestrator. Same public API as before."""

    def __init__(self, max_results: int = 5, cache_days: int = 1):
        self.max_results = max_results
        self.cache_days = cache_days

    @staticmethod
    def needs_web_search(query: str) -> bool:
        return _needs_web_search(query)

    async def search(
        self,
        query: str,
        max_results: Optional[int] = None,
        with_images: bool = False,
        with_videos: bool = False,
        status_cb: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> Optional[str]:
        if not query or not query.strip():
            return None
        result = await retrieval_orchestrator.retrieve(
            query,
            with_images=with_images,
            with_videos=with_videos,
            status_cb=status_cb,
            max_results=max_results or self.max_results,
        )
        return result.context

    async def search_with_images(
        self,
        query: str,
        max_results: Optional[int] = None,
        with_videos: bool = False,
        status_cb: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> tuple[Optional[str], str]:
        if not query or not query.strip():
            return None, ""
        result = await retrieval_orchestrator.retrieve(
            query,
            with_images=True,
            with_videos=with_videos,
            status_cb=status_cb,
            max_results=max_results or self.max_results,
        )
        return result.context, result.images_md

    async def fetch_images_markdown(
        self,
        query: str,
        max_results: Optional[int] = None,
        status_cb: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> str:
        if not query or not query.strip():
            return ""
        result = await retrieval_orchestrator.retrieve(
            query,
            with_images=True,
            status_cb=status_cb,
            max_results=max_results or self.max_results,
        )
        return result.images_md

    async def retrieve_for_chat(
        self,
        message: str,
        *,
        force_images: bool,
        with_videos: bool = False,
        status_cb: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> tuple[Optional[str], str, str]:
        """Run the full chat-path retrieval: (web_context, images_markdown, videos_markdown).

        force_images=True -> web search (if needed) and image search run in
        parallel; the image subject is extracted from the message.
        with_videos=True  -> videos run in the same parallel search when the
        video intent is required/recommended (section 26).
        """
        if force_images:
            img_query = extract_image_subject(message)
            if self.needs_web_search(message):
                ctx, md, vids = await asyncio.gather(
                    self.search(message, with_images=False, with_videos=with_videos, status_cb=status_cb),
                    self.fetch_images_markdown(img_query, status_cb=status_cb),
                    self.fetch_videos_markdown(message, status_cb=status_cb) if with_videos else _noop_videos(),
                )
                return ctx, md, vids
            videos_md = await self.fetch_videos_markdown(message, status_cb=status_cb) if with_videos else ""
            return None, await self.fetch_images_markdown(img_query, status_cb=status_cb), videos_md
        ctx, md, vids = await self._retrieve_via(message, with_images=True, with_videos=with_videos, status_cb=status_cb)
        return ctx, md, vids

    async def fetch_videos_markdown(
        self,
        query: str,
        max_results: Optional[int] = None,
        status_cb: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> str:
        """Videos-only retrieval: real video links formatted as markdown (section 26)."""
        from app.services.retrieval.videos import video_retriever

        if not query or not query.strip():
            return ""
        return await video_retriever.retrieve_markdown(query, status_cb)

    async def _retrieve_via(
        self,
        query: str,
        *,
        with_images: bool,
        with_videos: bool,
        status_cb: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> tuple[Optional[str], str, str]:
        result = await retrieval_orchestrator.retrieve(
            query,
            with_images=with_images,
            with_videos=with_videos,
            status_cb=status_cb,
        )
        return result.context, result.images_md, result.videos_md
