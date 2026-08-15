"""Image relevance validation (section 11).

Only images whose metadata (title, URL, source page) matches the query are
kept. No fabrication, no keyword-only randomness.
"""

import re

from .config import retrieval_config as cfg
from .providers import SearchResult


def _stem(w: str) -> str:
    """Simple plural/verb-form normalization: 'panels' -> 'panel', 'studies' -> 'study'."""
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    if len(w) > 4 and w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


def _keywords(query: str) -> list[str]:
    return [_stem(k) for k in re.split(r"[\s,]+", query.lower()) if len(k) > 2]


def _title_tokens(s: str) -> set[str]:
    return {_stem(t) for t in re.split(r"[\W_]+", (s or "").lower()) if len(t) > 2}


def is_relevant_image(r: SearchResult, query: str) -> bool:
    kws = _keywords(query)
    if not kws:
        return True
    title_tokens = _title_tokens(r.title)
    url_tokens = _title_tokens(r.url)
    image_tokens = _title_tokens(r.image_url)
    hits = 0
    for k in kws:
        if k in title_tokens or k in url_tokens or k in image_tokens:
            hits += 1
    return hits >= min(cfg.IMAGE_MIN_KEYWORD_HITS, len(kws))


def filter_relevant(results: list[SearchResult], query: str) -> list[SearchResult]:
    return [r for r in results if is_relevant_image(r, query)]
