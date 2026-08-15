"""Lightweight retrieval router (sections 1, 12).

Decides *which resource types* a query needs — web, news, images, videos,
docs, academic, products, maps — plus freshness scope and complexity.
Rule/pattern based: no LLM call for routing (fast, ~microseconds).
"""

import re
from typing import Optional

# ── Resource type signals ──
_NEWS = re.compile(
    r"\b(news|headlines?|breaking|latest (?:updates?|developments?)|what happened (?:today|this week)|"
    r"current events|top stories|today's (?:news|headlines)|daily brief)\b",
    re.I,
)
_CURRENT = re.compile(
    r"\b(today|tomorrow|yesterday|tonight|now|current|latest|recent|updated|"
    r"breaking|this (?:week|month|year)|price|prices|quote|quotes|stock|stocks|"
    r"market|crypto|bitcoin|eth|weather|forecast|temperature|"
    r"who (?:is|are|was|were|won|became|become|took over|replaced)\b|"
    r"\bwho (?:won|is leading|is ahead)\b|current (?:status|availability|version|price)\b)\b",
    re.I,
)
_IMAGE = re.compile(
    r"(show|display|find|search|get|fetch|give|send|want|need)\b.*\b(images?|pictures?|photos?|pics?|"
    r"diagrams?|screenshots?|graphics?)\b|\b(images?|pictures?|photos?|pics?)\s+(of|for)\b|"
    r"[\w'\-\s]{2,}\s+(images?|pictures?|photos?|pics?)\s*$",
    re.I,
)
_VIDEO = re.compile(
    r"\b(videos?|video of|watch |youtube|clip|clips|footage|documentary|tutorial video|"
    r"show (?:me )?a video|show (?:me )?videos)\b",
    re.I,
)
# Procedural / demonstrative queries strongly benefit from a video (section 26).
_VIDEO_RECOMMENDED = re.compile(
    r"\b(how do i|how do you|how to|how can i|step[- ]by[- ]step|steps?\b.*(?:do|make|build|install|"
    r"fix|setup)|walkthrough|tutorial|demonstrat|show me how|learn (?:to|how)|setup|install|configure|"
    r"repair|troubleshoot|fix\b|build\b|diy\b|recipe|cook\b|bake\b|paint\b|draw\b|play\b.*(?:song|guitar|"
    r"piano)|workout|yoga|exercise|routine|assembly|unboxing|review\b)\b",
    re.I,
)
_DOCS = re.compile(
    r"\b(docs|documentation|manual|manuals|reference|api (?:reference|docs)|developer guide|"
    r"syntax|how (?:do|to) (?:i|we)\b.*\b(install|use|setup|configure|deploy)\b|readme|guide|guides|"
    r"specifications?|changelog|release notes|documentation page)\b",
    re.I,
)
_ACADEMIC = re.compile(
    r"\b(research (?:paper|papers)|papers? (?:on|about|in)|arxiv|academic|scholarly|journal|"
    r"peer[- ]reviewed|studies? (?:on|about|show)|literature review|thesis)\b",
    re.I,
)
_PRODUCT = re.compile(
    r"\b(buy|purchase|price of|prices? for|cheapest|best (?:price|deal|deals?)|amazon|"
    r"shop|shopping|product|products|cost of|how much (?:does|is)|affordable)\b",
    re.I,
)
_MAPS = re.compile(
    r"\b(near me|location|directions|map|maps|open (?:now|today|late)|closest|nearby|"
    r"address of|find (?:a|an|the)?\s*(\w+ ){0,3}(store|shop|restaurant|hospital|bank|school)\b)\b",
    re.I,
)
_SEARCH_VERBS = re.compile(
    r"^(search (?:the )?web (?:for )?|find (?:information|sources)? (?:about|on|for)|"
    r"look (?:it )?up|research\b|compare\b|give me (?:sources|documentation|links)|"
    r"what (?:do|does|are|is) .*(?:latest|current|today|202\d))",
    re.I,
)

_QUESTION = re.compile(
    r"^(what|whats|what'?s|how|why|when|where|which|who|whom|whose|can|could|"
    r"should|would|will|does|do|did|is|are|was|were)\b[^\?]{3,}(\?|\s*$)",
    re.I,
)

_COMPLEX = re.compile(
    r"\b(compare|contrast|difference between|pros and cons|analysis|analyze|evaluate|"
    r"research|investigate|overview of|everything about|deep dive|comprehensive)\b",
    re.I,
)
_YEAR = re.compile(r"\b(19|20)\d{2}\b")
_VERSION = re.compile(r"\bv?\d+(\.\d+)+\b", re.I)


def is_current_info(query: str) -> bool:
    from datetime import date

    q = query.lower().strip()
    if not q:
        return False
    if _CURRENT.search(q):
        return True
    years = _YEAR.findall(q)
    current_year = date.today().year
    return any(int(y) >= current_year - 1 for y in years)


def is_news_query(query: str) -> bool:
    return bool(_NEWS.search(query)) or bool(re.search(r"\blatest\b", query.lower()))


def is_docs_query(query: str) -> bool:
    return bool(_DOCS.search(query))


def classify_video_intent(query: str) -> str:
    """Video intent level (section 26).

    required    -> the user explicitly asked for a video
    recommended -> procedural/demonstrative query where a video clearly helps
    optional    -> general knowledge query that could be enhanced by a video
    not_needed  -> no search needed at all
    """
    q = query.strip().lower()
    if not q:
        return "not_needed"
    if _VIDEO.search(q):
        return "required"
    if _VIDEO_RECOMMENDED.search(q):
        return "recommended"
    return "optional" if classify(q)["needs_search"] else "not_needed"


def classify(query: str) -> dict:
    """Return {'types': [...], 'complexity': ..., 'current': bool, 'needs_search': bool}."""
    q = query.strip().lower()
    types: list[str] = []
    if not q:
        return {"types": [], "complexity": "none", "current": False, "needs_search": False}

    current = is_current_info(q)
    if is_news_query(q):
        types.append("news")
    if _IMAGE.search(q):
        types.append("images")
    if _VIDEO.search(q):
        types.append("videos")
    if _DOCS.search(q):
        types.append("docs")
    if _ACADEMIC.search(q):
        types.append("academic")
    if _PRODUCT.search(q):
        types.append("products")
    if _MAPS.search(q):
        types.append("maps")

    needs_search = bool(
        q.startswith(("/search", "/web", "/news"))
        or _SEARCH_VERBS.search(q)
        or _QUESTION.search(q)
        or current
        or "latest" in q
        or _COMPLEX.search(q)
        or types
    )
    if needs_search:
        types.append("web")

    if _COMPLEX.search(q) or len(re.findall(r"\b\w+\b", q)) >= 8:
        complexity = "complex"
    elif len(re.findall(r"\b\w+\b", q)) >= 5:
        complexity = "medium"
    else:
        complexity = "simple"

    return {
        "types": types,
        "complexity": complexity,
        "current": current,
        "needs_search": needs_search,
    }
