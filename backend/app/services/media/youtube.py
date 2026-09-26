"""Native YouTube Video Search and Playback Engine.
Provides YouTube Data API v3 search with resilient zero-failure fallbacks, query normalization,
language/region calibration, recency filtering, and follow-up reference resolution.
"""

import os
import re
import json
import time
import urllib.parse
from typing import Optional, List, Dict, Any, Tuple
import httpx
from loguru import logger

from app.config import settings
from app.services.media.models import YouTubeVideo, YouTubeSearchResponse


# Regular expressions for video intent detection
VIDEO_TRIGGER_RE = re.compile(
    r"\b(videos?|youtube|watch|songs?|music\s*videos?|soundtrack|trailers?|"
    r"clips?|footage|tutorials?|interviews?|lectures?|gaming\s*videos?)\b",
    re.I,
)

PLAY_ACTION_RE = re.compile(
    r"^(?:play|watch|open|show|listen\s+to|start)\b|"
    r"\b(?:play\s+the|play\s+this|play\s+me|play\s+song|play\s+video)\b",
    re.I,
)

FOLLOWUP_ORDINAL_RE = re.compile(
    r"\b(?:the\s+)?(first|1st|second|2nd|third|3rd|fourth|4th|fifth|5th|last)\s+(?:one|video|song|track|result)\b|"
    r"\bplay\s+(?:the\s+)?(first|1st|second|2nd|third|3rd|fourth|4th|fifth|5th)\b|"
    r"\b(?:video|song|result)\s+#?([1-5])\b",
    re.I,
)

LANGUAGE_MAP = {
    "tamil": ("ta", "IN"),
    "hindi": ("hi", "IN"),
    "telugu": ("te", "IN"),
    "malayalam": ("ml", "IN"),
    "kannada": ("kn", "IN"),
    "punjabi": ("pa", "IN"),
    "bengali": ("bn", "IN"),
    "marathi": ("mr", "IN"),
    "spanish": ("es", "ES"),
    "french": ("fr", "FR"),
    "german": ("de", "DE"),
    "japanese": ("ja", "JP"),
    "korean": ("ko", "KR"),
    "chinese": ("zh", "CN"),
    "english": ("en", "US"),
}

ORDINAL_MAP = {
    "first": 0, "1st": 0, "1": 0,
    "second": 1, "2nd": 1, "2": 1,
    "third": 2, "3rd": 2, "3": 2,
    "fourth": 3, "4th": 3, "4": 3,
    "fifth": 4, "5th": 4, "5": 4,
}


class YouTubeService:
    """Enterprise YouTube search, metadata retrieval, and playback coordination."""

    def __init__(self):
        self._cache: Dict[str, Tuple[float, YouTubeSearchResponse]] = {}
        self._cache_ttl = 900  # 15 minutes cache for standard queries

    @classmethod
    def detect_video_intent(cls, text: str) -> bool:
        """Determines whether a message is an explicit or high-confidence video search/play request."""
        if not text:
            return False
        clean = text.strip().lower()

        # Direct YouTube keyword or URL
        if "youtube" in clean or "youtu.be" in clean:
            return True

        # Follow-up play commands: "play the second one", "play song 1"
        if FOLLOWUP_ORDINAL_RE.search(clean):
            return True

        # Explicit commands: "show some videos", "find videos", "play this song", "show Tamil songs"
        if re.search(r"\b(show|find|search|play|listen\s+to|watch|get|give\s+me)\b", clean) and VIDEO_TRIGGER_RE.search(clean):
            return True

        # Songs / music video queries: "tamil songs", "ar rahman songs", "latest songs"
        if re.search(r"\b(?:tamil|hindi|telugu|malayalam|punjabi|english|pop|rock|hip-hop)?\s*(?:songs?|music\s*videos?|melody)\b", clean):
            return True

        # Video tutorials / lectures / trailers: "python tutorial on youtube", "movie trailer"
        if re.search(r"\b(tutorial|lecture|trailer|walkthrough|gameplay)\b.*\b(video|watch)\b", clean) or \
           re.search(r"\b(video|watch)\b.*\b(tutorial|lecture|trailer|walkthrough|gameplay)\b", clean):
            return True

        return False

    @classmethod
    def extract_video_query(cls, text: str) -> Dict[str, Any]:
        """Normalizes user prompt into targeted search query, language, region, recency, and count."""
        clean = text.strip()
        lower = clean.lower()

        # Extract requested count (default 5, up to 10)
        max_results = 5
        count_match = re.search(r"\b(?:show|find|get)\s+(\d{1,2})\s+(?:videos|songs|results)?\b", lower)
        if count_match:
            try:
                cnt = int(count_match.group(1))
                if 1 <= cnt <= 15:
                    max_results = cnt
            except ValueError:
                pass

        # Detect language and regional hints
        relevance_lang = None
        region_code = None
        for lang_name, (l_code, r_code) in LANGUAGE_MAP.items():
            if re.search(rf"\b{lang_name}\b", lower):
                relevance_lang = l_code
                region_code = r_code
                break

        # Detect recency / order
        order = "relevance"
        is_fresh = False
        if re.search(r"\b(latest|new|today|recent|newest|this\s+week)\b", lower):
            order = "date"
            is_fresh = True

        # Normalize the search query string by stripping command boilerplate
        q = lower
        q = re.sub(r"^(?:hsbot[,\s]+)?(?:please\s+)?(?:can\s+you\s+)?", "", q)
        q = re.sub(r"^(?:show\s+(?:me\s+)?(?:some\s+|a\s+|the\s+)?(?:videos?\s+)?(?:for\s+|of\s+|about\s+)?|find\s+(?:me\s+)?(?:some\s+|a\s+|the\s+)?(?:videos?\s+)?(?:for\s+|of\s+|about\s+)?|search\s+(?:for\s+)?|search\s+on\s+youtube\s+for|search\s+youtube\s+for|play\s+(?:me\s+)?(?:some\s+|a\s+|the\s+)?|watch\s+)", "", q)
        q = re.sub(r"^(?:for|of|about)\s+", "", q)
        q = re.sub(r"\b(?:on\s+youtube|in\s+youtube|from\s+youtube|on\s+yt)\b", "", q)
        q = re.sub(r"\b(?:videos?|clips?)\b", "", q)
        q = re.sub(r"\b(?:for\s+free|online)\b", "", q)
        q = re.sub(r"^(?:for|of|about)\s+", "", q)
        q = q.strip(" -:?,.!")

        if not q:
            # Fallback to topic based on language if prompt was bare "show some videos"
            q = f"{clean}"

        # If user asked for songs and query is just a language, make it "{Language} songs"
        if re.search(r"\b(song|music|songs)\b", lower) and "song" not in q and "music" not in q:
            q = f"{q} songs"

        # Refinement for official music when requested
        if re.search(r"\b(official|music\s*video)\b", lower) and "official" not in q:
            q = f"{q} official"

        q = " ".join(q.split())

        return {
            "query": q,
            "max_results": max_results,
            "relevance_lang": relevance_lang,
            "region_code": region_code,
            "order": order,
            "is_fresh": is_fresh,
        }

    async def search(
        self,
        query: str,
        max_results: int = 5,
        page_token: Optional[str] = None,
        order: str = "relevance",
        language: Optional[str] = None,
        region: Optional[str] = None,
        fresh: bool = False,
    ) -> YouTubeSearchResponse:
        """Executes YouTube video search via official API or resilient fallback with zero fake links."""
        q_clean = query.strip()
        cache_key = f"{q_clean}|{max_results}|{order}|{language}|{region}|{page_token}"

        # 1. Check in-memory cache unless fresh is requested
        if not fresh and cache_key in self._cache:
            ts, cached_resp = self._cache[cache_key]
            if time.time() - ts < self._cache_ttl:
                return cached_resp

        api_key = settings.youtube_api_key or os.getenv("YOUTUBE_API_KEY")
        results: List[YouTubeVideo] = []
        next_token: Optional[str] = None

        # 2. Primary: Official YouTube Data API v3 (if API key present)
        if api_key:
            try:
                results, next_token = await self._search_official_api(
                    api_key=api_key,
                    query=q_clean,
                    max_results=max_results,
                    page_token=page_token,
                    order=order,
                    language=language,
                    region=region,
                )
            except Exception as e:
                logger.warning(f"[YOUTUBE] Official API search error: {e}, falling back to scraping engine")
                results = []

        # 3. Fallback: Resilient YouTube Scraping / Web Engine (Zero Quota Dependency)
        if not results:
            results = await self._search_fallback(
                query=q_clean,
                max_results=max_results,
                language=language,
            )

        resp = YouTubeSearchResponse(
            query=q_clean,
            total_results=len(results),
            results=results,
            next_page_token=next_token,
        )

        if results and not fresh:
            self._cache[cache_key] = (time.time(), resp)

        return resp

    async def _search_official_api(
        self,
        api_key: str,
        query: str,
        max_results: int,
        page_token: Optional[str],
        order: str,
        language: Optional[str],
        region: Optional[str],
    ) -> Tuple[List[YouTubeVideo], Optional[str]]:
        """Queries official Google YouTube Data API v3 GET /youtube/v3/search."""
        url = "https://www.googleapis.com/youtube/v3/search"
        params: Dict[str, Any] = {
            "part": "snippet",
            "type": "video",
            "q": query,
            "maxResults": min(max_results, 25),
            "key": api_key,
            "order": order,
        }
        if page_token:
            params["pageToken"] = page_token
        if language:
            params["relevanceLanguage"] = language
        if region:
            params["regionCode"] = region

        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url, params=params)
            if resp.status_code != 200:
                raise RuntimeError(f"YouTube API returned HTTP {resp.status_code}: {resp.text[:200]}")

            data = resp.json()
            items = data.get("items", [])
            next_token = data.get("nextPageToken")

            videos: List[YouTubeVideo] = []
            for it in items:
                v_id = it.get("id", {}).get("videoId")
                if not v_id:
                    continue
                snip = it.get("snippet", {})
                title = snip.get("title", "YouTube Video")
                # Clean html entities in title (e.g. &amp;, &#39;)
                title = self._unescape_html(title)

                thumbnails = snip.get("thumbnails", {})
                thumb_url = (
                    thumbnails.get("high", {}).get("url")
                    or thumbnails.get("medium", {}).get("url")
                    or thumbnails.get("default", {}).get("url")
                    or f"https://img.youtube.com/vi/{v_id}/hqdefault.jpg"
                )

                channel = snip.get("channelTitle", "YouTube Channel")
                channel_id = snip.get("channelId", "")
                pub_date = snip.get("publishedAt", "")[:10]
                desc = snip.get("description", "")

                videos.append(
                    YouTubeVideo(
                        video_id=v_id,
                        title=title,
                        channel_title=channel,
                        channel_id=channel_id,
                        thumbnail_url=thumb_url,
                        published_at=pub_date,
                        description=desc,
                    )
                )

            return videos, next_token

    async def _search_fallback(
        self,
        query: str,
        max_results: int,
        language: Optional[str] = None,
    ) -> List[YouTubeVideo]:
        """Scrapes real YouTube video IDs directly from YouTube search results page."""
        videos: List[YouTubeVideo] = []
        encoded_q = urllib.parse.quote(query)
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
            ),
            "Accept-Language": f"{language or 'en-US'},en;q=0.9",
        }
        url = f"https://www.youtube.com/results?search_query={encoded_q}"

        try:
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=True, headers=headers) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    text = resp.text
                    # Extract ytInitialData json object embedded in script tag
                    match = re.search(r"var ytInitialData\s*=\s*({.+?});</script>", text)
                    if not match:
                        match = re.search(r"ytInitialData\s*=\s*({.+?});", text)

                    if match:
                        try:
                            data = json.loads(match.group(1))
                            videos = self._parse_yt_initial_data(data, max_results)
                        except Exception as e:
                            logger.debug(f"[YOUTUBE] Failed parsing ytInitialData: {e}")

                    # Regex fallback if JSON parsing failed
                    if not videos:
                        videos = self._parse_youtube_html_regex(text, max_results)
        except Exception as e:
            logger.warning(f"[YOUTUBE] Scraping fallback failed: {e}")

        # Secondary fallback: use retrieval video provider if scrape returned empty
        if not videos:
            try:
                from app.services.retrieval.videos import video_retriever
                v_results = await video_retriever.search(f"{query} youtube", limit=max_results * 2)
                for r in v_results:
                    # Extract 11-char YouTube ID
                    m = re.search(r"[?&]v=([\w-]{11})", r.url) or re.search(r"youtu\.be/([\w-]{11})", r.url)
                    if m:
                        vid = m.group(1)
                        if not any(v.video_id == vid for v in videos):
                            videos.append(
                                YouTubeVideo(
                                    video_id=vid,
                                    title=r.title,
                                    channel_title=r.host or "YouTube",
                                    thumbnail_url=f"https://img.youtube.com/vi/{vid}/hqdefault.jpg",
                                    duration=r.duration,
                                )
                            )
                    if len(videos) >= max_results:
                        break
            except Exception as e:
                logger.warning(f"[YOUTUBE] Secondary video retriever fallback error: {e}")

        return videos[:max_results]

    def _parse_yt_initial_data(self, data: Dict[str, Any], max_results: int) -> List[YouTubeVideo]:
        """Extracts videoRenderer objects from ytInitialData hierarchy."""
        videos: List[YouTubeVideo] = []
        try:
            contents = (
                data.get("contents", {})
                .get("twoColumnSearchResultsRenderer", {})
                .get("primaryContents", {})
                .get("sectionListRenderer", {})
                .get("contents", [])
            )
            for section in contents:
                item_section = section.get("itemSectionRenderer", {}).get("contents", [])
                for item in item_section:
                    vr = item.get("videoRenderer")
                    if not vr:
                        continue
                    v_id = vr.get("videoId")
                    if not v_id or len(v_id) != 11:
                        continue

                    title_runs = vr.get("title", {}).get("runs", [])
                    title = "".join(r.get("text", "") for r in title_runs) or "YouTube Video"

                    channel_runs = vr.get("ownerText", {}).get("runs", [])
                    channel = "".join(r.get("text", "") for r in channel_runs) or "YouTube Channel"

                    # Duration text
                    duration = vr.get("lengthText", {}).get("simpleText", "")

                    # Published time text
                    published = vr.get("publishedTimeText", {}).get("simpleText", "")

                    # Description snippet
                    desc_runs = vr.get("detailedMetadataSnippets", [{}])[0].get("snippetText", {}).get("runs", [])
                    desc = "".join(r.get("text", "") for r in desc_runs)

                    videos.append(
                        YouTubeVideo(
                            video_id=v_id,
                            title=title,
                            channel_title=channel,
                            thumbnail_url=f"https://img.youtube.com/vi/{v_id}/hqdefault.jpg",
                            published_at=published,
                            duration=duration,
                            description=desc,
                        )
                    )
                    if len(videos) >= max_results:
                        break
                if len(videos) >= max_results:
                    break
        except Exception:
            pass
        return videos

    def _parse_youtube_html_regex(self, html: str, max_results: int) -> List[YouTubeVideo]:
        """Extracts videoId and titles using regex matching from raw YouTube search response."""
        videos: List[YouTubeVideo] = []
        pattern = re.compile(r'href="/watch\?v=([\w-]{11})"[^>]*title="([^"]+)"')
        seen = set()
        for match in pattern.finditer(html):
            v_id, raw_title = match.groups()
            if v_id in seen:
                continue
            seen.add(v_id)
            title = self._unescape_html(raw_title)
            videos.append(
                YouTubeVideo(
                    video_id=v_id,
                    title=title,
                    channel_title="YouTube Channel",
                    thumbnail_url=f"https://img.youtube.com/vi/{v_id}/hqdefault.jpg",
                )
            )
            if len(videos) >= max_results:
                break
        return videos

    @classmethod
    def resolve_followup(
        cls,
        text: str,
        previous_videos: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Resolves follow-up commands such as 'play the second one' against previous search results."""
        if not previous_videos:
            return None
        clean = text.strip().lower()

        # Check for ordinal matches: first, second, 3rd, #2, etc.
        target_idx = None
        ord_match = FOLLOWUP_ORDINAL_RE.search(clean)
        if ord_match:
            word = ord_match.group(1) or ord_match.group(2) or ord_match.group(3)
            if word and word in ORDINAL_MAP:
                target_idx = ORDINAL_MAP[word]
            elif word == "last":
                target_idx = len(previous_videos) - 1

        if target_idx is not None and 0 <= target_idx < len(previous_videos):
            return {
                "action": "play",
                "index": target_idx + 1,
                "video": previous_videos[target_idx],
            }

        # Fuzzy title match with distinctive word overlap (excluding stopwords)
        stopwords = {"song", "songs", "video", "videos", "track", "tracks", "music", "audio", "play", "watch", "official", "lyrics", "the", "one", "this"}
        clean_words = set(re.findall(r"\w+", clean)) - stopwords
        best_match = None
        max_overlap = 0

        for idx, v in enumerate(previous_videos):
            title = str(v.get("title", "")).lower()
            title_words = set(re.findall(r"\w+", title)) - stopwords
            overlap = len(clean_words & title_words)
            if overlap > max_overlap:
                max_overlap = overlap
                best_match = {
                    "action": "play",
                    "index": idx + 1,
                    "video": v,
                }

        if best_match and max_overlap > 0:
            return best_match

        return None

    @staticmethod
    def _unescape_html(text: str) -> str:
        """Unescapes HTML entities in video titles."""
        import html
        return html.unescape(text)


youtube_service = YouTubeService()
