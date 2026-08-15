import asyncio
import re
import time
from datetime import date
from typing import Optional

_QUERY_CACHE: dict[str, dict] = {}


def extract_image_subject(query: str) -> str:
    """Strip a trailing 'and show relevant images' clause, keeping the research subject."""
    q = query.strip()
    q = re.sub(
        r"(?i)\s+(?:and|also|plus|then)\s+(?:show|display|include|add|get|find)\s+"
        r"(?:me\s+)?(?:some\s+|relevant\s+|related\s+)?(?:images?|pictures?|photos?|pics?)\s*[.?!]*$",
        "",
        q,
    )
    return q.strip() or query.strip()


async def _noop() -> list:
    return []


def _needs_web_search(query: str) -> bool:
    if not query or not query.strip():
        return False
    q = query.lower().strip()
    if q.startswith(("/search", "/web", "/news")):
        return True

    recency = [
        r"\btoday\b", r"\btomorrow\b", r"\byesterday\b", r"\btonight\b",
        r"\bnow\b", r"\bcurent\b", r"\bcurrent\b", r"\blatest\b", r"\brecent\b",
        r"\bbreaking\b", r"\bnews\b", r"\bheadline\b", r"\bupdate\b",
        r"\bweather\b", r"\bforecast\b", r"\btemperature\b",
        r"\bprice\b", r"\bprices\b", r"\bquote\b", r"\bquotes\b", r"\bstock\b",
        r"\bstocks\b", r"\bmarket\b", r"\bcrypto\b", r"\bbitcoin\b", r"\beth\b",
        r"\bfixtures\b", r"\bscore\b", r"\bresult\b", r"\bschedule\b",
        r"\bthis week\b", r"\bthis month\b", r"\bthis year\b",
        r"\bwhat happened\b", r"\bwhat's new\b", r"\bwhat is new\b",
        r"\bstatus of\b", r"\brelease\b", r"\bannouncement\b", r"\blaunch\b",
        r"\bversion\b", r"\bchange log\b", r"\bchangelog\b",
        r"\bper cent\b", r"\bpercent\b", r"%\b",
        r"\bwho (is|are|was|were) the (?:new |current |present )?(?:cm|chief minister|president|prime minister|pm|minister|mayor|governor|ceo|chairman|chairperson|secretary|director|captain|coach|leader|head|king|queen|winner)\b",
        r"\bwho (?:is|are|won|became|become|took over|replaced)\b",
        r"\bwho (?:won|is leading|is ahead)\b",
        r"\bcurrent (?:cm|chief minister|president|leader|status|price|rate|position)\b",
        r"\bnew (?:cm|government|law|policy|rule|update)\b",
    ]
    if any(re.search(p, q) for p in recency):
        return True

    year_matches = re.findall(r"\b(?:19|20)\d{2}\b", q)
    current_year = date.today().year
    if any(int(y) >= current_year - 1 for y in year_matches):
        return True

    return False


class WebSearchService:
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
    ) -> Optional[str]:
        if not query or not query.strip():
            return None

        limit = max_results or self.max_results
        today = date.today().isoformat()
        cache_key = f"{today}|{query.strip().lower()}|img={int(with_images)}"
        cached = _QUERY_CACHE.get(cache_key)
        if cached:
            return cached["context"]

        loop = asyncio.get_event_loop()
        try:
            text_results, image_results = await asyncio.gather(
                asyncio.wait_for(
                    loop.run_in_executor(None, self._search_sync, query, limit),
                    timeout=20.0,
                ),
                asyncio.wait_for(
                    loop.run_in_executor(None, self._images_sync, query, limit) if with_images else _noop(),
                    timeout=20.0,
                ),
            )
        except (asyncio.TimeoutError, Exception):
            return None

        if not text_results and not image_results:
            return None

        context_parts = []
        for r in text_results or []:
            title = (r.get("title") or "").strip()
            body = (r.get("body") or "").strip()
            url = (r.get("href") or "").strip()
            if not title and not body:
                continue
            entry = f"- {title}: {body}" if body else f"- {title}"
            if url:
                entry += f" ({url})"
            context_parts.append(entry)

        if not context_parts:
            return None

        context = (
            f"[WEB SEARCH RESULTS from {today} - IMPORTANT: Today's date is {today}. "
            f"You MUST base your answer on these search results below (they are the most up-to-date data). "
            f"Answer using ONLY these results - do NOT use your training knowledge for facts, dates, prices, "
            f"or events newer than {today}. If the results don't contain the answer, say so. "
            f"Cite the source URL for each claim]:\n"
            + "\n".join(context_parts)
        )

        if image_results:
            images_md = "\n\n".join(f"![{alt}]({u})" for alt, u in image_results)
            context = (
                f"{context}\n\n[RELEVANT IMAGES - You MUST include these images in your answer. "
                f"At the end of your answer, paste the markdown image links below exactly as shown]:\n{images_md}"
            )

        _QUERY_CACHE[cache_key] = {"context": context, "date": today}
        return context

    async def search_with_images(self, query: str, max_results: Optional[int] = None) -> tuple[Optional[str], str]:
        """Returns (context, images_markdown). Images are guaranteed regardless of LLM behavior."""
        context = await self.search(query, max_results=max_results, with_images=True)
        images_md = await self.fetch_images_markdown(query, max_results)
        return context, images_md

    async def fetch_images_markdown(self, query: str, max_results: Optional[int] = None) -> str:
        """Fetch only the images for a query as markdown."""
        if not query or not query.strip():
            return ""
        limit = max_results or self.max_results
        loop = asyncio.get_event_loop()
        try:
            images = await asyncio.wait_for(
                loop.run_in_executor(None, self._images_sync, query, limit),
                timeout=20.0,
            )
        except (asyncio.TimeoutError, Exception):
            return ""
        if not images:
            return ""
        return "\n\n".join(f"![{alt}]({u})" for alt, u in images)

    def _search_sync(self, query: str, limit: int) -> list[dict]:
        from ddgs import DDGS
        with DDGS() as ddgs:
            return list(ddgs.text(query, max_results=limit))

    def _images_sync(self, query: str, limit: int) -> list[tuple[str, str]]:
        """Fetch images via Wikimedia Commons — file titles must match the
        query, so results are on-topic (unlike generic image indexes)."""
        try:
            import httpx
            resp = httpx.get(
                "https://commons.wikimedia.org/w/api.php",
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
                headers={"User-Agent": "HSBot/1.0 (https://github.com/25it038-beep/Hs-chatbot; contact: hsbot@example.com)"},
                timeout=15.0,
            )
            resp.raise_for_status()
            pages = resp.json().get("query", {}).get("pages", {})
        except Exception:
            return []

        keywords = [k for k in re.split(r"[\s,]+", query.lower()) if len(k) > 2]
        results = []
        for page in pages.values():
            info = (page.get("imageinfo") or [{}])[0]
            url = (info.get("thumburl") or info.get("url") or "").split("?")[0]
            mime = info.get("mime", "")
            title = page.get("title", "").replace("File:", "")
            if not url:
                continue
            if mime and not mime.startswith("image/"):
                continue
            title_l = title.lower()
            if keywords and not any(k in title_l for k in keywords):
                continue
            results.append((title.strip()[:80], url))
            if len(results) >= limit:
                break
        return results
