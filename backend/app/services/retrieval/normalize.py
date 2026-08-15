"""Query normalization for cache keys (section 8).

Equivalent queries collapse to the same key while meaningful differences
(dates, years, versions, locations) are preserved.
"""

import re

_STOP_PREFIXES = [
    r"^please\s+", r"^pls\s+", r"^(can|could)\s+you\s+", r"^i want to\s+",
    r"^(what|how|when|where|why|who|which|does|do|is|are|was|were|did)\s+",
    r"^(tell me about|explain|research|learn about|find|search|look up|show me|give me|get)\s+",
    r"^(an?\s+|the\s+)",
]
_NOISE_TOKENS = {
    "please", "pls", "the", "an", "a", "about", "of", "for", "with", "and", "or",
    "on", "in", "at", "to", "me", "my", "your", "you", "can", "could", "want",
    "need", "show", "find", "search", "what", "how", "when", "where", "why",
    "who", "which", "does", "do", "is", "are", "was", "were", "did", "some",
    "any", "info", "information", "please", "tell", "give", "get", "related",
}


def normalize_query(query: str) -> str:
    q = query.strip().lower()
    q = re.sub(r"[^\w\s\d.\-]", " ", q)
    for p in _STOP_PREFIXES:
        q = re.sub(p, "", q, count=1)
    tokens = [t for t in re.split(r"\s+", q) if t and t not in _NOISE_TOKENS]
    q = " ".join(tokens)
    q = re.sub(r"\s+", " ", q).strip()
    return q or query.strip().lower()


def cache_scope(query: str) -> str:
    """Classify freshness scope so TTL tiers can be chosen."""
    return "docs" if _docs_query(query) else "current" if _current_query(query) else "general"


def _current_query(query: str) -> bool:
    from .router import is_current_info
    return is_current_info(query)


def _docs_query(query: str) -> bool:
    from .router import is_docs_query
    return is_docs_query(query)
