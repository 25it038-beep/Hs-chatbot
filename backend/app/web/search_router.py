"""Advanced prompt understanding, constraint extraction, and search mode routing (sections 4, 6, 7)."""

import re
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from app.web.models import SearchMode


from enum import Enum

from app.web.models import SearchMode


class CurrentnessClassification(str, Enum):
    CURRENT_REQUIRED = "CURRENT_REQUIRED"
    CURRENT_PREFERRED = "CURRENT_PREFERRED"
    CURRENT_NOT_NEEDED = "CURRENT_NOT_NEEDED"


# ── Non-Search Bypasses (Zero unnecessary searches for purely creative, rewrite, or chit-chat) ──
_SMALLTALK = re.compile(
    r"^\s*(hi|hello|hey|greetings|howdy|good\s+(?:morning|afternoon|evening|night)|"
    r"how\s+are\s+you|who\s+are\s+you|what\s+is\s+your\s+name|what('?s|\s+is)\s+up|"
    r"thank\s+you|thanks|bye|goodbye|see\s+you|can\s+you\s+help\s+me|tell\s+me\s+about\s+yourself)\b[^\?]*[\?!.]*$",
    re.I,
)

_CREATIVE = re.compile(
    r"\b(write\s+(?:me\s+)?(?:a\s+|an\s+)?(?:(?:short|long|sci-fi|funny|bedtime|original|quick)\s+)*(?:poem|story|song|lyrics|essay|joke|riddle|limerick|"
    r"script|screenplay|scene|dialogue|haiku|speech)|compose\s+(?:a\s+)?(?:(?:short|long|funny|quick)\s+)*(?:poem|song|haiku|story|speech|melody|essay|tune)|"
    r"roleplay\s+as|pretend\s+(?:you\s+are|to\s+be)|act\s+as\s+a|brainstorm\s+(?:names|ideas)\s+for)\b",
    re.I,
)

_TRANSFORM = re.compile(
    r"\b(translate\b.*?\b(?:to|into)\b|translate\s+(?:this|the|sentence|text)?|"
    r"summarize\s+(?:this|the\s+following|the\s+text\s+below)?|"
    r"rewrite\s+(?:this|the\s+following|the\s+sentence|the\s+text|the\s+email|the\s+paragraph)?|"
    r"make\s+this\s+(?:email|paragraph|text|sentence|message|draft|post)?\s*(?:more\s+)?(?:professional|polite|concise|formal|better|friendly|clear)|"
    r"paraphrase\s+(?:this|the\s+following)?|proofread\s+(?:this|the\s+following)?|"
    r"fix\s+(?:the\s+)?grammar\s+in|convert\s+to\s+(?:bullet\s+points|markdown|json|table))\b",
    re.I,
)

_MATH_LOGIC = re.compile(
    r"^(calculate|compute|solve|evaluate)\s+[\d\sx\+\-\*\/\^\(\)\=\.\%]+$|"
    r"^\s*[\d\s\.\,\+\-\*\/\^\(\)\=\%]{3,}\s*$|"
    r"\b(what\s+is\s+\d+\s*[\+\-\*\/x]\s*\d+|square\s+root\s+of\s+\d+|derivative\s+of\s+[a-z0-9]|integral\s+of\s+[a-z0-9])\b",
    re.I,
)

_PURE_ALGORITHM = re.compile(
    r"\b(write\s+(?:a\s+)?(?:python|javascript|typescript|c\+\+|java|rust|go)?\s*"
    r"(?:function|script|code|method)\s+to\s+(?:reverse|traverse|sort|find\s+max\s+in)\s+(?:a\s+|an\s+)?"
    r"(?:string|array|list|linked\s+list|binary\s+tree))\b",
    re.I,
)

# ── Positive Cues ──
_EXPLICIT_DEEP = re.compile(
    r"\b(deep\s+research|comprehensive\s+(?:report|analysis|study|investigation)|"
    r"in[- ]depth\s+research|detailed\s+report|research\s+in\s+detail|market\s+landscape|"
    r"research\s+the\s+current\s+state\s+of|produce\s+a\s+research\s+paper)\b",
    re.I,
)

_EXPLICIT_SEARCH = re.compile(
    r"^(/search|/web|/news)\b|"
    r"\b(search\s+(?:the\s+)?web|search\s+online|browse\s+(?:the\s+)?web|"
    r"google\s+(?:this|for)|look\s+(?:it\s+)?up\s+online|"
    r"find\s+(?:information|sources|articles|news|web\s+results)\s+(?:about|on|for)|"
    r"check\s+online|research\s+online)\b",
    re.I,
)

_COMPARISON_PRO = re.compile(
    r"\b(compare|versus|vs\.?|difference\s+between|which\s+is\s+better|pros\s+and\s+cons|"
    r"best\s+(?:laptops?|phones?|gpus?|tools?|options?|frameworks?|models?)|"
    r"under\s+(?:₹|\$|€|rs\.?)\s*\d+)\b",
    re.I,
)

_CURRENT_SIGNALS = re.compile(
    r"\b(today|tomorrow|yesterday|tonight|now|right now|current|currently|latest|recent|recently|updated|"
    r"breaking|this (?:week|month|year)|price|prices|quote|stocks|market|crypto|bitcoin|btc|eth|"
    r"who (?:is|are|won|is leading|was|became|took over|replaced)|"
    r"current (?:cm|chief minister|president|prime minister|pm|governor|leader|ceo)|"
    r"release date|roadmap|changelog|patch notes)\b",
    re.I,
)

_REGIONS = [
    ("india", "IN"), ("chennai", "IN"), ("bangalore", "IN"), ("mumbai", "IN"), ("delhi", "IN"),
    ("tamil nadu", "IN"), ("tamilnadu", "IN"), ("karnataka", "IN"), ("us", "US"), ("usa", "US"),
    ("united states", "US"), ("uk", "UK"), ("united kingdom", "UK"), ("europe", "EU"),
    ("germany", "DE"), ("canada", "CA"),
]


def classify_currentness(query: str) -> CurrentnessClassification:
    """Classify prompt into CURRENT_REQUIRED, CURRENT_PREFERRED, or CURRENT_NOT_NEEDED."""
    q = query.strip()
    if not q:
        return CurrentnessClassification.CURRENT_NOT_NEEDED

    explicit = bool(_EXPLICIT_SEARCH.search(q))
    if explicit:
        return CurrentnessClassification.CURRENT_REQUIRED

    # Check non-search bypasses (creative, transform, pure math, smalltalk)
    if _SMALLTALK.search(q):
        return CurrentnessClassification.CURRENT_NOT_NEEDED
    if _CREATIVE.search(q):
        return CurrentnessClassification.CURRENT_NOT_NEEDED
    if _TRANSFORM.search(q):
        return CurrentnessClassification.CURRENT_NOT_NEEDED
    if _MATH_LOGIC.search(q):
        return CurrentnessClassification.CURRENT_NOT_NEEDED
    if _PURE_ALGORITHM.search(q):
        return CurrentnessClassification.CURRENT_NOT_NEEDED

    # Explicit currentness indicators
    if _CURRENT_SIGNALS.search(q) or "202" in q:
        return CurrentnessClassification.CURRENT_REQUIRED

    # Always-Current default: factual, real-world, technical, lookups default to CURRENT_PREFERRED / CURRENT_REQUIRED
    return CurrentnessClassification.CURRENT_PREFERRED


def extract_constraints(query: str) -> Dict[str, Any]:
    """Extract structured constraints: region, budget, criteria, category, freshness."""
    q_low = query.lower()
    constraints: Dict[str, Any] = {
        "region": None,
        "budget": None,
        "criteria": [],
        "category": None,
        "year": None,
        "output_format": "answer",
    }

    # Region
    for term, code in _REGIONS:
        if re.search(rf"\b{term}\b", q_low):
            constraints["region"] = code
            break

    # Budget
    budget_m = re.search(r"(?:under|below|budget\s+of|max)\s*(?:₹|rs\.?|inr|\$|usd|€)?\s*([\d,]+(?:\s*(?:k|lakh|crore))?)", q_low)
    if budget_m:
        constraints["budget"] = budget_m.group(0).strip()

    # Year (grounded with actual current year 2026)
    year_m = re.search(r"\b(202\d)\b", query)
    if year_m:
        constraints["year"] = year_m.group(0)
    else:
        constraints["year"] = str(date.today().year)

    # Categories
    for cat in ["laptop", "phone", "smartphone", "gpu", "cpu", "model", "framework", "software", "robot", "robotics", "car", "ev"]:
        if re.search(rf"\b{cat}s?\b", q_low):
            constraints["category"] = cat
            break

    # Criteria
    for crit in ["battery", "gaming", "camera", "display", "performance", "development", "coding", "design", "weight", "portability"]:
        if re.search(rf"\b{crit}\b", q_low):
            constraints["criteria"].append(crit)

    # Format
    if re.search(r"\b(pdf|docx|pptx|excel|xlsx|slides?|document|report)\b", q_low):
        for fmt in ["pdf", "docx", "pptx", "xlsx", "report"]:
            if fmt in q_low:
                constraints["output_format"] = fmt
                break

    return constraints


def determine_search_mode(query: str, user_override: Optional[str] = None) -> Tuple[SearchMode, Dict[str, Any]]:
    """Automatically decide between FAST, PRO, DEEP, and NONE based on ALWAYS-CURRENT DATA MODE."""
    q = query.strip()
    constraints = extract_constraints(q)

    if user_override:
        ov = user_override.lower()
        if "deep" in ov:
            return SearchMode.DEEP, constraints
        if "pro" in ov:
            return SearchMode.PRO, constraints
        if "fast" in ov or "search" in ov:
            return SearchMode.FAST, constraints
        if "none" in ov or "off" in ov:
            return SearchMode.NONE, constraints

    # 1. Non-search check
    currentness = classify_currentness(q)
    if currentness == CurrentnessClassification.CURRENT_NOT_NEEDED:
        return SearchMode.NONE, constraints

    # 2. Explicit Deep Research markers
    if _EXPLICIT_DEEP.search(q):
        return SearchMode.DEEP, constraints

    # 3. Complex comparative or multi-criteria query -> PRO
    if _COMPARISON_PRO.search(q) or len(constraints["criteria"]) >= 2:
        return SearchMode.PRO, constraints

    # Multi-part complex query check (length >= 14 words with connectors)
    tokens = [t for t in re.split(r"\W+", q) if t]
    if len(tokens) >= 14 and ("and" in q.lower() or "," in q or "compare" in q.lower()):
        return SearchMode.PRO, constraints

    # 4. Standard current, factual, technical, lookup -> FAST by default
    return SearchMode.FAST, constraints
