"""Lightweight retrieval router (sections 1, 12, 33, 34).

Decides *which resource types* a query needs — web, news, images, videos,
docs, academic, products, maps — plus freshness scope and complexity.
Rule/pattern based: no LLM call for routing (fast, ~microseconds).

Enforces zero unnecessary searches for stable conceptual knowledge, creative writing,
math, code algorithms, and personal chit-chat.
"""

import re
from datetime import date
from typing import Optional

# ── Explicit Web Search Triggers ──
_EXPLICIT_SEARCH = re.compile(
    r"^(/search|/web|/news)\b|"
    r"\b(search\s+(?:the\s+)?web|search\s+online|browse\s+(?:the\s+)?web|"
    r"google\s+(?:this|for)|look\s+(?:it\s+)?up\s+online|"
    r"find\s+(?:information|sources|articles|news|web\s+results)\s+(?:about|on|for)|"
    r"check\s+online|research\s+online)\b",
    re.I,
)

# Direct URL in query
_URL_PATTERN = re.compile(r"https?://[^\s<>\"']+|www\.[^\s<>\"']+", re.I)

# ── Negative Bypasses: No Web Search Needed ──
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

_CODE_ALGORITHM = re.compile(
    r"\b(write\s+(?:a\s+)?(?:python|javascript|typescript|c\+\+|java|rust|go)?\s*"
    r"(?:function|script|code|method)\s+to\s+(?:reverse|traverse|sort|find\s+max\s+in)\s+(?:a\s+|an\s+)?"
    r"(?:string|array|list|linked\s+list|binary\s+tree))\b",
    re.I,
)

# ── Resource type signals ──
_NEWS = re.compile(
    r"\b(news|headlines?|breaking|latest (?:updates?|developments?)|what happened (?:today|this week|yesterday)|"
    r"current events|top stories|today's (?:news|headlines)|daily brief|breaking news)\b",
    re.I,
)

_CURRENT = re.compile(
    r"\b(today|tomorrow|yesterday|tonight|now|right now|current|currently|latest|recent|recently|updated|"
    r"breaking|this (?:week|month|year)|price|prices|quote|quotes|stock|stocks|"
    r"market|crypto|bitcoin|btc|eth|weather|forecast|temperature|"
    r"who (?:is|are|was|were|won|became|become|took over|replaced)\b|"
    r"\bwho (?:won|is leading|is ahead)\b|current (?:status|availability|version|price)|"
    r"release date|released? date|roadmap|changelog|patch notes)\b",
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
    r"shop|shopping|product|products|cost of|how much (?:does|is)|affordable|specs of|specifications of)\b",
    re.I,
)

_MAPS = re.compile(
    r"\b(near me|location|directions|map|maps|open (?:now|today|late)|closest|nearby|"
    r"address of|find (?:a|an|the)?\s*(\w+ ){0,3}(store|shop|restaurant|hospital|bank|school)\b)\b",
    re.I,
)

_MUSIC = re.compile(
    r"\b(song|lyrics|track|album|artist|playlist|listen to|play (?:song|track|music|the )|"
    r"spotify|youtube music|mp3|record label|band|concert|tour dates)\b",
    re.I,
)

_REGION = re.compile(
    r"\b(in|at|near|around|from)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b|"
    r"\b(city|state|country|region|province|district)\b",
    re.I,
)

# Emerging entities / models / hardware / frameworks (post-cutoff or rapidly changing)
_EMERGING_ENTITIES = re.compile(
    r"\b(deepseek(?:-[a-z0-9\.]+)?|claude\s*3\.[57]|gpt-?4\.[5o]|llama\s*3\.[123]|"
    r"gemini\s*2(?:\.[0-9])?|rtx\s*50\d0|m[45]\s*(?:pro|max)?|next\.?js\s*15|"
    r"react\s*19|tailwind\s*(?:v?4|css\s*4)|vue\s*3\.[45]|angular\s*1[89])\b",
    re.I,
)

_FAST_DOMAINS = re.compile(
    r"\b(who\s+won|score\s+of|match\s+result|election\s+results?|medal\s+tally|standings|"
    r"world\s+cup|olympics|super\s+bowl|stock\s+price|market\s+cap|cryptocurrency)\b",
    re.I,
)

_SEARCH_VERBS = re.compile(
    r"^(search (?:the )?web (?:for )?|find (?:information|sources)? (?:about|on|for)|"
    r"look (?:it )?up|research\b|compare\b|give me (?:sources|documentation|links)|"
    r"what (?:do|does|are|is) .*(?:latest|current|today|202\d))",
    re.I,
)

_COMPLEX_SEARCH = re.compile(
    r"\b(compare|contrast|difference between|pros and cons|analysis|analyze|evaluate|"
    r"research|investigate|deep dive|comprehensive)\b",
    re.I,
)

_YEAR = re.compile(r"\b(19|20)\d{2}\b")
_VERSION = re.compile(r"\bv?\d+(\.\d+)+\b", re.I)


def is_non_search_intent(query: str) -> bool:
    """True if the query represents stable knowledge, smalltalk, creative, or math logic."""
    q = query.strip()
    if not q:
        return True
    # If explicitly asking to search, never bypass
    if _EXPLICIT_SEARCH.search(q) or _URL_PATTERN.search(q):
        return False
    # If time-sensitive or emerging tech mentioned, never bypass
    if _CURRENT.search(q) or _EMERGING_ENTITIES.search(q) or _FAST_DOMAINS.search(q):
        return False
    # Check bypass patterns
    if _SMALLTALK.search(q):
        return True
    if _CREATIVE.search(q):
        return True
    if _TRANSFORM.search(q):
        return True
    if _MATH_LOGIC.search(q):
        return True
    if _CODE_ALGORITHM.search(q) and not _DOCS.search(q):
        return True
    return False


def is_current_info(query: str) -> bool:
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
    q = query.strip()
    if not q:
        return {"types": [], "complexity": "none", "current": False, "needs_search": False}

    # First check non-search intents
    if is_non_search_intent(q):
        return {"types": [], "complexity": "simple", "current": False, "needs_search": False}

    # Process prompt sentence-by-sentence to capture multi-part requests
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', q) if s.strip()]
    q_low = q.lower()
    types_set = set()
    current_any = False

    for sent in sentences:
        sent_low = sent.lower()
        if is_current_info(sent_low):
            current_any = True
        if is_news_query(sent_low):
            types_set.add("news")
        if _IMAGE.search(sent_low):
            types_set.add("images")
        if _VIDEO.search(sent_low):
            types_set.add("videos")
        if _DOCS.search(sent_low):
            types_set.add("docs")
        if _ACADEMIC.search(sent_low):
            types_set.add("academic")
        if _PRODUCT.search(sent_low):
            types_set.add("products")
        if _MAPS.search(sent_low):
            types_set.add("maps")
        if _MUSIC.search(sent_low):
            types_set.add("music")
        if _REGION.search(sent_low) and not _MAPS.search(sent_low):
            types_set.add("region")

    current = current_any or is_current_info(q_low)
    types = list(types_set)

    # In ALWAYS-CURRENT DATA MODE: every query that passed is_non_search_intent needs web search
    needs_search = True
    if "web" not in types:
        types.append("web")

    if _COMPLEX_SEARCH.search(q) or len(re.findall(r"\b\w+\b", q)) >= 10:
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
