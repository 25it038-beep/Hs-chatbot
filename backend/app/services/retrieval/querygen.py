"""Adaptive query generation and multi-angle planning (sections 3, 5, 7, 19).

Transforms raw user prompts into focused, multi-angle search queries.
Resolves conversational pronouns (anaphora) from recent chat history.
Produces targeted angles: primary intent, official sources, freshness, and technical specs.
"""

import re
from datetime import date
from typing import Optional

_YEAR = re.compile(r"\b(19|20)\d{2}\b")

# Trailing intent clauses like "...and show pictures", "...plus videos"
_TRAIL = re.compile(
    r"(?i)\s+(?:and|also|plus|then)\s+(?:show|display|include|add|get|find)\s+"
    r"(?:me\s+)?(?:some\s+|relevant\s+|related\s+)?(?:images?|pictures?|photos?|pics?|videos?)\s*[.?!]*$"
)

# Conversational filler and polite phrasing
_CONVERSATIONAL_PREFIXES = re.compile(
    r"(?i)^\s*(?:please\s+|pls\s+)?(?:(?:can you|could you|would you|can u)\s+)?"
    r"(?:(?:please\s+)?(?:tell me|give me|find|search for|look up|show me|check|research|explain|describe)\s+)?"
    r"(?:(?:about|information on|details (?:about|on)|sources for)\s+)?"
    r"(?:(?:what|whats|what'?s|who|whom|which|where|when|how)\s+(?:is|are|was|were|do|does|did|can|will)\s+)?"
    r"(?:(?:the|a|an)\s+)*"
)

# Pronoun indicators for conversational follow-ups
_ANAPHORA_PATTERNS = re.compile(
    r"\b(it|its|they|them|their|this|that|these|those|he|him|his|she|her)\b|"
    r"^(how much (?:does it|is it)|when was (?:it|that)|who made (?:it|that)|"
    r"is it (?:good|worth|available)|where to buy)\b",
    re.I,
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


def clean_query(query: str) -> str:
    """Strip conversational filler, trailing request tags, and punctuation."""
    q = _TRAIL.sub("", query.strip())
    q = _CONVERSATIONAL_PREFIXES.sub("", q)
    q = _ARTICLE.sub("", q)
    q = re.sub(r"[\s]+", " ", q).strip(" .:;!?\"'“”")
    return q or query.strip()


def _extract_recent_entity(chat_history: list[dict]) -> Optional[str]:
    """Extract the primary subject/entity from recent turns."""
    if not chat_history:
        return None
    # Look at the most recent 3 messages in reverse
    for msg in reversed(chat_history[-3:]):
        content = msg.get("content") or ""
        if not content or len(content) > 500:
            continue
        cleaned = clean_query(content)
        tokens = cleaned.split()
        if 1 <= len(tokens) <= 6:
            return cleaned
        # Try matching capitalized entity names (e.g. "Apple Vision Pro", "RTX 5090")
        entities = re.findall(r"\b[A-Z][a-zA-Z0-9\-_]+(?:\s+[A-Z0-9][a-zA-Z0-9\-_]+)*\b", content)
        if entities:
            # Return the longest entity
            best = max(entities, key=len)
            if len(best) > 3:
                return best
    return None


def resolve_context_query(query: str, chat_history: Optional[list[dict]] = None) -> str:
    """Resolve anaphoric references using recent conversation history."""
    q = query.strip()
    if not chat_history:
        return q

    # Check if query contains anaphoric pronouns or is a short fragment (< 5 words)
    words = q.split()
    if _ANAPHORA_PATTERNS.search(q) or len(words) <= 4:
        entity = _extract_recent_entity(chat_history)
        if entity:
            # If query is very short, combine entity with query
            if len(words) <= 4 and entity.lower() not in q.lower():
                return f"{entity} {clean_query(q)}"
            # Replace pronoun with entity
            resolved = re.sub(r"\b(it|this|that|these|those)\b", entity, q, flags=re.I)
            if resolved != q:
                return resolved
    return q


def _video_subject(query: str) -> str:
    base = _TRAIL.sub("", query.strip())
    base = _VIDEO_PREFIX.sub("", base)
    base = _QUESTION_PREFIX.sub("", base)
    base = _ARTICLE.sub("", base)
    base = re.sub(r"[\s]+", " ", base).strip(" .:;!?")
    return base


def generate_video_queries(query: str) -> list[str]:
    """Video-optimized queries (section 26): bare subject + tutorial variant."""
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


def generate_queries(
    query: str,
    complexity: str = "simple",
    types: Optional[list[str]] = None,
    chat_history: Optional[list[dict]] = None,
) -> list[str]:
    """Generate focused, multi-angle search queries.

    Simple -> 1 focused query.
    Medium -> 2 diverse queries.
    Complex -> 3-4 targeted queries from diverse angles.
    """
    types = types or []
    # 1. Resolve conversational pronouns if history is present
    resolved = resolve_context_query(query, chat_history)

    # 2. Clean base query
    base = clean_query(resolved)
    if not base:
        base = query.strip()

    if complexity == "simple" and not ("news" in types or "docs" in types or "products" in types):
        return [base]

    current_year = str(date.today().year)
    year_match = _YEAR.search(base)
    year = year_match.group(0) if year_match else current_year

    queries: list[str] = [base]

    # Angle 2: Official / Authoritative documentation angle
    if "docs" in types or re.search(r"\b(api|sdk|library|framework|install|setup|guide|config|syntax)\b", base, re.I):
        queries.append(f"{base} official documentation")
    elif "products" in types or re.search(r"\b(rtx|gpu|cpu|phone|laptop|price|specs)\b", base, re.I):
        # Angle 2: Technical specifications / pricing angle
        queries.append(f"{base} specifications review")
        if "price" not in base.lower():
            queries.append(f"{base} price {year}")
    elif "news" in types or "web" in types:
        # Angle 2: Fresh updates angle
        if year not in base:
            queries.append(f"{base} latest updates {year}")
        else:
            queries.append(f"{base} latest developments")

    # Angle 3: Comparison / Research angle for complex queries
    if complexity == "complex":
        if re.search(r"\b(vs|versus|difference|compare)\b", base, re.I):
            queries.append(f"{base} comparison benchmark")
        elif "research" not in base.lower():
            queries.append(f"{base} overview analysis")

    # Deduplicate while preserving order
    seen: set[str] = set()
    result: list[str] = []
    for q in queries:
        norm = re.sub(r"\s+", " ", q).strip().lower()
        if norm and norm not in seen:
            seen.add(norm)
            result.append(q)

    # Cap to max 4 queries to maintain provider efficiency
    return result[:4]
