"""Video retrieval (section 26).

Retrieves real, verified video links only — never fabricated. Videos run in
parallel with text/images when the query needs them (VIDEO_REQUIRED /
VIDEO_RECOMMENDED) and asynchronously after the answer for VIDEO_OPTIONAL.

Pipeline: ddgs.videos (primary) -> host/URL validation -> keyword relevance
-> dedupe -> rank (youtube bias, recency, duration) -> cap -> markdown.

Fallback: if ddgs video search returns nothing, a plain web search filtered
to known video hosts (youtube/vimeo/dailymotion/...) supplies real links.
"""

import re
from dataclasses import dataclass, field
from typing import Optional

from loguru import logger

from .config import retrieval_config as cfg
from .providers import VIDEO_SEARCH_DOMAINS, SearchResult, provider_pool

# Hosts whose URLs are reliably a video page (used by the fallback path).
# Shared with providers.TavilyVideoProvider (include_domains).
_VIDEO_HOSTS = VIDEO_SEARCH_DOMAINS

_HOST_HINT = re.compile(r"^(?:https?://)?(?:www\.)?([^/:]+)")
_TITLE_CLEAN = re.compile(r"[\u00a0\u200b]+")
_PLACEHOLDER_TITLE = re.compile(
    r"(?i)(video unavailable|page not found|404|forbidden|removed by|private video)"
)


@dataclass
class VideoResult:
    title: str = ""
    url: str = ""
    host: str = ""
    duration: str = ""
    published: str = ""
    source: str = "ddgs"
    score: float = 0.0
    extra: dict = field(default_factory=dict)


def to_video_result(r: SearchResult) -> VideoResult:
    """Adapt a pipeline SearchResult (kind='videos') to a VideoResult."""
    return VideoResult(
        title=r.title,
        url=r.url,
        duration=str(r.extra.get("duration") or ""),
        published=r.published,
        source=r.source,
        extra=r.extra,
    )


def _host(url: str) -> str:
    m = _HOST_HINT.match(url)
    return m.group(1).lower() if m else ""


def _is_video_host(url: str) -> bool:
    h = _host(url)
    return any(h == v or h.endswith("." + v) for v in _VIDEO_HOSTS)


def _clean_title(title: str) -> str:
    # DDGS often glues multiple results into one title
    # ("How to Make Pancakes - video DailymotionGood Old-Fashioned..."). Cut at
    # the first glue token and cap the length.
    t = _TITLE_CLEAN.sub(" ", title)
    t = re.split(r"(?i)\s*(?:- video\b|, video\b|\(with video\)|video:)", t, maxsplit=1)[0]
    t = t.strip(" -:,;")
    return t[:110] or ""


def _query_keywords(query: str) -> set[str]:
    return {k for k in re.split(r"[\s,]+", query.lower()) if len(k) > 3 and not k.startswith(("http", "www"))}


def _video_key(url: str) -> str:
    """Stable identity key per video — never the bare watch path.

    Stripping the query string collapses every YouTube watch URL onto
    'youtube.com/watch'; keep the platform's video ID instead.
    """
    host = _host(url)
    if "youtube.com" in host or host == "youtu.be":
        m = re.search(r"[?&](?:v|embed)=([\w-]{6,})", url) or re.search(r"youtu\.be/([\w-]{6,})", url)
        if m:
            return f"yt:{m.group(1)}"
        m = re.search(r"/shorts/([\w-]{6,})", url)
        if m:
            return f"yt-shorts:{m.group(1)}"
    if "vimeo.com" in host:
        m = re.search(r"vimeo\.com/(?:video/)?(\d+)", url)
        if m:
            return f"vim:{m.group(1)}"
    if "dailymotion.com" in host:
        m = re.search(r"dailymotion\.com/video/([a-z0-9]+)", url)
        if m:
            return f"dm:{m.group(1)}"
    if "tiktok.com" in host:
        m = re.search(r"tiktok\.com/@[^/]+/video/(\d+)", url)
        if m:
            return f"tt:{m.group(1)}"
    if "bilibili.com" in host:
        m = re.search(r"(?:/video/|/BV)([A-Za-z0-9]+)", url)
        if m:
            return f"bili:{m.group(1)}"
    return re.sub(r"^(https?://www\.|https?://)", "", re.split(r"[?#]", url)[0].rstrip("/"))


def dedupe_videos(results: list[VideoResult]) -> list[VideoResult]:
    seen: set[str] = set()
    out: list[VideoResult] = []
    for r in results:
        key = _video_key(r.url)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def filter_videos(results: list[VideoResult], query: str, *, allow_non_video_hosts: bool = True) -> list[VideoResult]:
    """Drop invalid/placeholder results. Real URLs only — nothing is fabricated."""
    out: list[VideoResult] = []
    for r in results:
        if not r.url or not re.match(r"^https?://", r.url):
            continue
        if not allow_non_video_hosts and not _is_video_host(r.url):
            continue
        title = _clean_title(r.title)
        if not title or _PLACEHOLDER_TITLE.search(title):
            continue
        r.title = title
        r.host = _host(r.url)
        out.append(r)
    return out


def rank_videos(results: list[VideoResult], query: str) -> list[VideoResult]:
    keywords = _query_keywords(query)
    for r in results:
        score = 0.0
        host = r.host
        if host.endswith("youtube.com") or host == "youtu.be":
            score += 2.0
        elif host in ("vimeo.com", "dailymotion.com", "tiktok.com", "twitch.tv", "bilibili.com"):
            score += 1.0
        title_l = r.title.lower()
        if keywords:
            hits = sum(1 for k in keywords if k in title_l)
            score += min(hits, 3) * 0.5
        if r.duration:
            score += 0.25
        if r.published:
            score += 0.25
        r.score = round(score, 2)
    return sorted(results, key=lambda r: r.score, reverse=True)


def format_videos_md(results: list[VideoResult], limit: Optional[int] = None) -> str:
    """Structured markdown list. Empty string when there are no real videos."""
    cap = limit or cfg.MAX_VIDEOS
    if not results:
        return ""
    parts = ["\n\n### Videos"]
    for r in results[:cap]:
        meta = []
        if r.host:
            meta.append(r.host)
        if r.duration:
            meta.append(r.duration)
        label = r.title
        if meta:
            label = f"{r.title} — {', '.join(meta)}"
        parts.append(f"- [{label}]({r.url})")
    return "\n".join(parts)


class VideoRetriever:
    """Searches, validates, ranks and formats real videos (section 26)."""

    def __init__(self, pool=None) -> None:
        self._pool = pool if pool is not None else provider_pool

    async def search(self, query: str, limit: int = 20) -> list[VideoResult]:
        """Primary path: ddgs video search. Fallback: web search gated to video hosts."""
        results: list[VideoResult] = []
        try:
            rows = await self._pool.videos(query, limit)
        except Exception as e:
            logger.warning("video search failed for {!r}: {}", query, e)
            rows = []
        if rows:
            results = [
                VideoResult(
                    title=r.title,
                    url=r.url,
                    duration=r.extra.get("duration", ""),
                    published=r.published,
                    source=r.source,
                    extra=r.extra,
                )
                for r in rows
            ]
        if not results:
            logger.info("video search empty for {!r}, trying host-gated web fallback", query)
            try:
                web_rows = await self._pool.text(f"{query} video", 15, "web")
            except Exception as e:
                logger.warning("video fallback search failed for {!r}: {}", query, e)
                web_rows = []
            fallback = [
                VideoResult(title=r.title, url=r.url, source=r.source) for r in web_rows or []
            ]
            # Prefer strict video-platform hosts (youtube/vimeo/...); only when
            # those are too thin, keep other real video pages (recipe sites etc).
            strict = filter_videos(fallback, query, allow_non_video_hosts=False)
            results = strict if len(strict) >= 2 else filter_videos(fallback, query)
        filtered = filter_videos(results, query, allow_non_video_hosts=not bool(rows))
        return rank_videos(dedupe_videos(filtered), query)

    async def retrieve_markdown(self, query: str, status_cb=None) -> str:
        """(query, optional status callback) -> videos markdown or ''."""
        if status_cb is not None:
            try:
                await status_cb("Finding relevant videos...")
            except Exception:
                pass
        results = await self.search(query, cfg.VIDEO_CANDIDATES)
        return format_videos_md(results, cfg.MAX_VIDEOS)


video_retriever = VideoRetriever()
