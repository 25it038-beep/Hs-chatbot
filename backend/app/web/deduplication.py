"""URL and content deduplication for web research."""

import difflib
import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from typing import Any, List


_TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "ref", "ref_src", "mc_cid", "mc_eid", "igshid", "spm",
}


def canonicalize_url(url: str) -> str:
    """Normalize URL by stripping tracking parameters, anchors, and www."""
    if not url:
        return ""
    try:
        parsed = urlparse(url)
    except Exception:
        return url

    scheme = parsed.scheme.lower() or "https"
    netloc = (parsed.netloc or "").lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]

    # Remove default port
    if ":" in netloc:
        host, port = netloc.split(":", 1)
        if (scheme == "http" and port == "80") or (scheme == "https" and port == "443"):
            netloc = host

    # Normalize path
    path = parsed.path or "/"
    path = re.sub(r"/+", "/", path)
    if path != "/" and path.endswith("/"):
        path = path[:-1]

    # Filter tracking query parameters
    query_params = []
    if parsed.query:
        for k, v in parse_qsl(parsed.query, keep_blank_values=False):
            if k.lower() not in _TRACKING_PARAMS and not k.lower().startswith("utm_"):
                query_params.append((k, v))
    new_query = urlencode(query_params)

    return urlunparse((scheme, netloc, path, "", new_query, ""))


def text_similarity(a: str, b: str) -> float:
    """Fast similarity ratio between two text snippets."""
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a.lower()[:300], b.lower()[:300]).ratio()


def deduplicate_sources(sources: List[Any], sim_threshold: float = 0.85) -> List[Any]:
    """Deduplicate source objects by canonical URL and title/snippet similarity."""
    seen_urls = set()
    unique_sources = []

    for s in sources:
        url = getattr(s, "url", "") if hasattr(s, "url") else (s.get("url") if isinstance(s, dict) else "")
        title = getattr(s, "title", "") if hasattr(s, "title") else (s.get("title") if isinstance(s, dict) else "")

        canon = canonicalize_url(url)
        if canon and canon in seen_urls:
            continue

        # Check content/title similarity against accepted sources
        is_duplicate = False
        for u in unique_sources:
            u_title = getattr(u, "title", "") if hasattr(u, "title") else (u.get("title") if isinstance(u, dict) else "")
            if text_similarity(title, u_title) > sim_threshold:
                is_duplicate = True
                break

        if not is_duplicate:
            if canon:
                seen_urls.add(canon)
            unique_sources.append(s)

    return unique_sources
