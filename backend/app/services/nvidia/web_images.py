import httpx
import logging
from typing import Optional
from urllib.parse import quote

logger = logging.getLogger("nvidia.web_images")

COMMONS_API = "https://commons.wikimedia.org/w/api.php"

HEADERS = {"User-Agent": "HSBot/1.0 (https://github.com/25it038-beep/Hs-chatbot; contact: hsbot@example.com)"}


class WebImageSearch:
    """Keyless image search backed by Wikimedia Commons."""

    async def search(self, query: str, limit: int = 6) -> list[dict]:
        if not query or not query.strip():
            return []
        try:
            params = {
                "action": "query",
                "generator": "search",
                "gsrsearch": query,
                "gsrnamespace": "6",
                "gsrlimit": str(min(limit, 10)),
                "prop": "imageinfo",
                "iiprop": "url|mime",
                "iiurlwidth": "480",
                "format": "json",
                "origin": "*",
            }
            async with httpx.AsyncClient(timeout=15.0, headers=HEADERS) as client:
                resp = await client.get(COMMONS_API, params=params)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            logger.warning("Web image search failed: %s", e)
            return []

        pages = data.get("query", {}).get("pages", {})
        if not pages:
            return []

        results = []
        for page in pages.values():
            info = (page.get("imageinfo") or [{}])[0]
            url = (info.get("thumburl") or info.get("url") or "").split("?")[0]
            mime = info.get("mime", "")
            if not url:
                continue
            if mime and not mime.startswith("image/"):
                continue
            results.append({
                "title": page.get("title", "").replace("File:", ""),
                "url": url,
                "full_url": (info.get("url") or "").split("?")[0],
            })
            if len(results) >= limit:
                break
        return results

    def extract_query(self, message: str) -> str:
        """Strip common intent phrases, keeping the search subject."""
        import re
        text = message.strip()
        patterns = [
            r"(?i)^(show|display|find|search|get|fetch|send|want|give|need)\s+(me\s+)?(some\s+|any\s+|the\s+|a\s+|an\s+)?(images?|pictures?|photos?|pics?|image)\s+(of|for)\s+",
            r"(?i)^(images?|pictures?|photos?|pics?|image)\s+(of|for)\s+",
            r"(?i)^(an\s+|a\s+|the\s+)?(image|picture|photo|pic)\s+of\s+",
            r"(?i)^(show|display|find|search|get|fetch|send|want|give|need)\s+(me\s+)?(images?|pictures?|photos?|pics?|image)\s+",
            r"(?i)^(web\s+)?images?\s+of\s+",
        ]
        for p in patterns:
            text = re.sub(p, "", text)
        text = re.sub(r"(?i)\s+(images?|pictures?|photos?|pics?)\s*$", "", text)
        text = re.sub(r"(?i)^\s*(?:(?:please|pls|can you|could you)\s+)*(?:show|display|find|search|get|fetch|send|want|give|need)\s+(?:me\s+)?(?:some\s+|any\s+|the\s+|a\s+|an\s+)?", "", text)
        text = re.sub(r"(?i)^\s*(please|pls|can you|could you)\s+", "", text).strip(" .,:;!?")
        return text or message.strip()


web_image_search = WebImageSearch()