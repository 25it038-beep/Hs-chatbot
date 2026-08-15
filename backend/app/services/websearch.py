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
        status_cb: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> Optional[str]:
        if not query or not query.strip():
            return None
        result = await retrieval_orchestrator.retrieve(
            query,
            with_images=with_images,
            status_cb=status_cb,
            max_results=max_results or self.max_results,
        )
        return result.context

    async def search_with_images(
        self,
        query: str,
        max_results: Optional[int] = None,
        status_cb: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> tuple[Optional[str], str]:
        if not query or not query.strip():
            return None, ""
        result = await retrieval_orchestrator.retrieve(
            query,
            with_images=True,
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
        status_cb: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> tuple[Optional[str], str]:
        """Run the full chat-path retrieval: (web_context, images_markdown).

        force_images=True -> web search (if needed) and image search run in
        parallel; the image subject is extracted from the message.
        """
        if force_images:
            img_query = extract_image_subject(message)
            if self.needs_web_search(message):
                ctx, md = await asyncio.gather(
                    self.search(message, with_images=False, status_cb=status_cb),
                    self.fetch_images_markdown(img_query, status_cb=status_cb),
                )
                return ctx, md
            return None, await self.fetch_images_markdown(img_query, status_cb=status_cb)
        return await self.search_with_images(message, status_cb=status_cb)
