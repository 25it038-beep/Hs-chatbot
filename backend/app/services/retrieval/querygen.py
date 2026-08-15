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
