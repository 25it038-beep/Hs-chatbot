"""Adaptive query generation (sections 3, 19).

Generates the minimum number of focused sub-queries from a user query.
Simple -> 1 query, medium -> 2, complex -> 3-4. Never excessive.
"""

import re

_YEAR = re.compile(r"\b(19|20)\d{2}\b")
_TRAIL = re.compile(
    r"(?i)\s+(?:and|also|plus|then)\s+(?:show|display|include|add|get|find)\s+"
    r"(?:me\s+)?(?:some\s+|relevant\s+|related\s+)?(?:images?|pictures?|photos?|pics?|videos?)\s*[.?!]*$"
)

_VIDEO_PREFIX = re.compile(
    r"(?i)^\s*(?:please\s+|pls\s+)?(?:(?:can you|could you|would you)\s+)?"
    r"(?:show me|show|find|get|search for|give me|recommend|send me|fetch)?\s*"
    r"(?:a|an|the|some)?\s*(?:video\s+(?:about|of|on)\s+|videos\s+(?:about|of|on)\s+|"
    r"youtube (?:video\s+)?(?:about|of|on)\s+)?"
)
_QUESTION_PREFIX = re.compile(
    r"(?i)^\s*(?:what|whats|what'?s|what are|what is|how|why|when|where|which|who|whose|"
    r"can|could|should|would|will|does|do|did|is|are|was|were)\s+"
    r"(?:(?:do|does|did|is|are|was|were|can|could|should|would|will|to|i|you|we|they|one|it|"
    r"a|an|the)\s+)*"
)
_ARTICLE = re.compile(r"(?i)^\s*(?:an?\s+|the\s+)")


def _video_subject(query: str) -> str:
    base = _TRAIL.sub("", query.strip())
    base = _VIDEO_PREFIX.sub("", base)
    base = _QUESTION_PREFIX.sub("", base)
    base = _ARTICLE.sub("", base)
    base = re.sub(r"[\s]+", " ", base).strip(" .:;!?")
    return base


def generate_video_queries(query: str) -> list[str]:
    """Video-optimized queries (section 26): bare subject + tutorial variant.

    DDGS video search is best with a plain subject ('solar panel installation'),
    so we strip intent/verb scaffolding instead of appending keywords.
    """
    subject = _video_subject(query)
    if not subject:
        return [query.strip()]
    variants = [subject, f"{subject} tutorial"]
    seen: list[str] = []
    for v in variants:
        key = v.lower()
        if key not in seen:
            seen.append(key)
    return seen[:2]


def generate_queries(query: str, complexity: str) -> list[str]:
    base = _TRAIL.sub("", query.strip())
    base = re.sub(r"[\s]+", " ", base).strip(" .:;!?")
    if not base:
        return [query.strip()]

    if complexity == "simple":
        return [base]

    year = ""
    m = _YEAR.search(base)
    if m:
        year = m.group(0)

    queries = [base]
    if year:
        queries.append(re.sub(r"\b(19|20)\d{2}\b", str(int(year) + 1), base))
    else:
        queries.append(f"{base} 2026")

    if complexity == "complex":
        if "research" not in base.lower():
            queries.append(f"{base} research")
        if "latest" not in base.lower() and len(queries) < 4 and not re.search(
            r"\b(vs|versus|difference|comparison|specs|specifications)\b", base, re.I
        ):
            queries.append(f"{base} latest")

    # Deduplicate near-identical variants
    seen: list[str] = []
    for q in queries:
        key = q.lower()
        if key not in seen:
            seen.append(key)
    return seen[:4]
