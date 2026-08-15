"""Natural-language intent detection for browser actions (sections 1-3, 22).

Deterministic, fast, and safe: normal chat must NEVER be hijacked by a
false-positive browser trigger. Every intent requires strong evidence
(verb + service/URL/media-noun + optional query). Returns None → normal chat.

BROWSER_ACTION subcategories:
OPEN_WEBSITE SEARCH_WEB SEARCH_SITE PLAY_MEDIA PAUSE_MEDIA RESUME_MEDIA
SKIP_MEDIA NAVIGATE CLICK TYPE SCROLL EXTRACT DOWNLOAD SCREENSHOT
OTHER_BROWSER_ACTION  (+ internal CONFIRM_ACTION for pending approvals)

Detection priority (compound commands win):
confirm → media controls → SEARCH_SITE → SEARCH_WEB → PLAY_MEDIA → OPEN →
screenshot/scroll/extract/click/type/download → other-browser
("Open Spotify and play Believer" is PLAY_MEDIA, not OPEN_WEBSITE.)
"""

import re
from dataclasses import dataclass, field
from typing import Optional

from .config import browser_config

# ---------------------------------------------------------------------------
# Intents
# ---------------------------------------------------------------------------

OPEN_WEBSITE = "OPEN_WEBSITE"
SEARCH_WEB = "SEARCH_WEB"
SEARCH_SITE = "SEARCH_SITE"
PLAY_MEDIA = "PLAY_MEDIA"
PAUSE_MEDIA = "PAUSE_MEDIA"
RESUME_MEDIA = "RESUME_MEDIA"
SKIP_MEDIA = "SKIP_MEDIA"
NAVIGATE = "NAVIGATE"
CLICK = "CLICK"
TYPE = "TYPE"
SCROLL = "SCROLL"
EXTRACT = "EXTRACT"
DOWNLOAD = "DOWNLOAD"
SCREENSHOT = "SCREENSHOT"
OTHER_BROWSER_ACTION = "OTHER_BROWSER_ACTION"
CONFIRM_ACTION = "CONFIRM_ACTION"

BROWSER_INTENTS = {
    OPEN_WEBSITE, SEARCH_WEB, SEARCH_SITE, PLAY_MEDIA, PAUSE_MEDIA, RESUME_MEDIA,
    SKIP_MEDIA, NAVIGATE, CLICK, TYPE, SCROLL, EXTRACT, DOWNLOAD, SCREENSHOT,
    OTHER_BROWSER_ACTION, CONFIRM_ACTION,
}

MEDIA_SERVICES = {"spotify", "youtube", "netflix", "soundcloud", "pandora", "music"}

# "search this website for X" → operate on the current page
CURRENT_PAGE = "current"


@dataclass
class BrowserIntent:
    intent: str
    service: Optional[str] = None        # spotify / youtube / github ... or CURRENT_PAGE
    query: Optional[str] = None
    url: Optional[str] = None
    target: Optional[str] = None         # element description (CLICK/TYPE)
    text: Optional[str] = None           # text to type (TYPE)
    direction: Optional[str] = None      # down/up/top/bottom (SCROLL)
    requires_confirmation: bool = False
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "intent": self.intent,
            "service": self.service,
            "query": self.query,
            "url": self.url,
            "target": self.target,
            "text": self.text,
            "direction": self.direction,
            "requires_confirmation": self.requires_confirmation,
        }


# ---------------------------------------------------------------------------
# Regex tables
# ---------------------------------------------------------------------------

_URL_RE = re.compile(r"https?://[^\s\"'<>]+")
_BARE_DOMAIN_RE = re.compile(
    r"\b(?:www\.)?([a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:com|org|net|io|dev|ai|co|me|app|xyz|info|edu|gov))\b",
    re.I,
)

_VERB_OPEN = re.compile(r"\b(?:open|go to|navigate to|launch|take me to|visit|load)\b", re.I)
_VERB_OPEN_WEBSITE = re.compile(r"\bopen\s+(?:(?:the|this)\s+)?(?:website|web page|page|site|url)\b", re.I)
_VERB_SEARCH = re.compile(r"\b(?:search|look up|find|look for)\b", re.I)
_VERB_PLAY = re.compile(r"\b(?:play|put on|start)\b", re.I)
_VERB_PAUSE = re.compile(r"\b(?:pause|stop)\b", re.I)
_VERB_RESUME = re.compile(r"\b(?:resume|unpause|continue)\b", re.I)
_VERB_SKIP = re.compile(r"\b(?:skip|next)\b", re.I)

_MEDIA_NOUN = re.compile(
    r"\b(?:song|songs|music|track|tracks|playlist|artist|album|video|videos|radio|podcast)\b", re.I
)
_PAUSE_NOUN = re.compile(r"\b(?:music|song|track|playback|video|it)\b", re.I)
_RESUME_NOUN = re.compile(r"\b(?:music|song|track|playback|video|it|playing)\b", re.I)
_SKIP_NOUN = re.compile(r"\b(?:song|track|one|music|video|this)\b", re.I)

_WEB_SEARCH = re.compile(
    r"\b(?:search|look up|find)\s+(?:the\s+)?(?:web|internet|online|google)\b"
    r"|\bsearch\s+(?:for|about)\b[^,.]{2,80}|\blook\s+it\s+up\b|\bgoogle\s+it\b|\bweb\s+search\b",
    re.I,
)
_SITE_SEARCH = re.compile(r"\bsearch\s+(?:on\s+)?([a-z0-9 .-]+?)\s+for\s+(.+)$", re.I)
_SITE_SEARCH2 = re.compile(r"\b(?:look up|find|search for)\s+(.+?)\s+on\s+([a-z0-9 .-]+?)\s*$", re.I)
_SITE_SEARCH_CURRENT = re.compile(
    r"\bsearch\s+(?:on\s+)?this\s+(?:website|site|web page|page)\s+for\s+(.+)$", re.I
)

_CONFIRM = re.compile(
    r"^\s*(?:yes|yeah|yep|y|sure|ok|okay|go ahead|do it|confirm|proceed|continue|approved|yes please|that'?s right)"
    r"(?:[.!]|,\s*sure|\s+(?:and\s+)?(?:do\s+it|go\s+ahead|please|proceed|continue|sure))*\s*$",
    re.I,
)
_CONSEQUENTIAL = re.compile(
    r"\b(?:buy|purchase|order|checkout|add to cart|pay|payment|transfer|withdraw|"
    r"send\s+(?:an?\s+|this\s+|the\s+|my\s+)?(?:message|email|text)|post|tweet|submit\s+(?:form|this)|"
    r"delete|remove|clear|unsubscribe|cancel\s+(?:my\s+)?(?:subscription|account)|sign\s+out|log\s+out)\b",
    re.I,
)

_SCREENSHOT = re.compile(r"\b(?:take\s+a\s+)?(?:screenshot|screen\s+shot|capture\s+(?:the\s+)?(?:screen|page))\b", re.I)
_SCROLL = re.compile(r"\bscroll\s+(down|up|to\s+(?:bottom|top))\b", re.I)
_EXTRACT = re.compile(r"\b(?:extract|grab|copy)\s+(?:the\s+)?(?:page\s+|site\s+)?(?:text|content|data)\b", re.I)
_CLICK = re.compile(r"\bclick\s+(?:on\s+|the\s+|the\s+)?(.+?)\s*$", re.I)
_TYPE = re.compile(r"\b(?:type|enter|put)\s+(.+?)\s+(?:in|into)\s+(?:the\s+)?(.+?)\s*$", re.I)
_DOWNLOAD = re.compile(r"\bdownload\b", re.I)

# query tail cleanup: "search X for Python and play it" → "Python"
_QUERY_TAIL = re.compile(r"\s+(?:and|then)\s+(?:play|search|open|show|watch).*$", re.I)

_SERVICE_RE = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in sorted(browser_config.WEBSITES, key=len, reverse=True)) + r")\b", re.I
)


def _clean(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    s = re.sub(r"\s+", " ", s).strip(" \t\n\"'.,;!?")
    s = _QUERY_TAIL.sub("", s)
    s = re.sub(r"\s+on\s*$", "", s)          # "believer on" → "believer"
    s = re.sub(r"^(?:some|a|an|any|the)\s+", "", s)  # "some A.R. Rahman" → "A.R. Rahman"
    return s or None


def known_service(name: str) -> Optional[str]:
    key = _clean(name)
    if not key:
        return None
    return browser_config.WEBSITES.get(key.lower())


def lookup_site(service: str) -> Optional[str]:
    return browser_config.WEBSITES.get(service.lower())


def _extract_url(text: str) -> Optional[str]:
    m = _URL_RE.search(text)
    return m.group(0) if m else None


def _extract_bare_domain(text: str) -> Optional[str]:
    m = _BARE_DOMAIN_RE.search(text)
    if not m:
        return None
    return f"https://{m.group(0).lower()}"


def _extract_service(text: str) -> Optional[str]:
    matches = _SERVICE_RE.findall(text)
    if not matches:
        return None
    return sorted(matches, key=len, reverse=True)[0].lower()


def _strip_service(text: str, service: Optional[str]) -> str:
    if not service:
        return text
    return re.sub(rf"\b{re.escape(service)}\b", " ", text, flags=re.I)


def _query_after(text: str, verb: str) -> Optional[str]:
    """Text after 'for'/'about' following a verb; else after the verb itself."""
    m = re.search(rf"{verb}\b[^.!?]*?\b(?:for|about)\s+(.+)$", text, re.I)
    if m:
        return _clean(m.group(1))
    m = re.search(rf"{verb}\b[^.!?]*?\s+(.+)$", text, re.I)
    if m:
        return _clean(m.group(1))
    return None


def classify_browser_intent(message: str, current_service: Optional[str] = None) -> Optional[BrowserIntent]:
    """Returns a BrowserIntent or None (normal chat). Never raises."""
    if not message or not message.strip():
        return None
    text = " ".join(message.split())

    service = _extract_service(text)
    url = _extract_url(text)

    # ── Confirm an already-queued consequential action ──
    if _CONFIRM.match(text) and len(text) <= 60:
        return BrowserIntent(intent=CONFIRM_ACTION, evidence=["confirm"])

    # ── Short media controls (need media context to avoid false positives) ──
    if _VERB_PAUSE.search(text) and (_PAUSE_NOUN.search(text) or service in MEDIA_SERVICES):
        return BrowserIntent(intent=PAUSE_MEDIA, service=current_service, evidence=["pause"])
    if _VERB_RESUME.search(text) and (_RESUME_NOUN.search(text) or service in MEDIA_SERVICES):
        return BrowserIntent(intent=RESUME_MEDIA, service=current_service, evidence=["resume"])
    if _VERB_SKIP.search(text) and (_SKIP_NOUN.search(text) or service in MEDIA_SERVICES):
        return BrowserIntent(intent=SKIP_MEDIA, service=current_service, evidence=["skip"])
    if text.lower() in {"pause", "resume", "skip", "next"} and current_service in ("spotify", "youtube"):
        return BrowserIntent(
            intent={"pause": PAUSE_MEDIA, "resume": RESUME_MEDIA, "skip": SKIP_MEDIA, "next": SKIP_MEDIA}[text.lower()],
            service=current_service,
            evidence=[text],
        )

    # ── Consequential actions (section 16): never execute without an explicit
    # user confirmation; queue via OPEN_WEBSITE/OTHER and let the service gate.
    if _CONSEQUENTIAL.search(text) and not _VERB_SEARCH.search(text) and not _VERB_PLAY.search(text):
        if service:
            return BrowserIntent(
                intent=OPEN_WEBSITE, service=service, url=lookup_site(service),
                requires_confirmation=True, evidence=["consequential-open"],
            )
        if _VERB_OPEN.search(text) or url:
            return BrowserIntent(
                intent=OPEN_WEBSITE, url=url, requires_confirmation=True, evidence=["consequential-open"],
            )

    # ── SEARCH_SITE (highest priority among open-style: "open X and search ...") ──
    m = _SITE_SEARCH_CURRENT.search(text)
    if m:
        return BrowserIntent(intent=SEARCH_SITE, service=CURRENT_PAGE, query=_clean(m.group(1)), evidence=["search-current"])
    m = _SITE_SEARCH.search(text)
    if m:
        site = m.group(1).strip().lower()
        if site in browser_config.WEBSITES:
            return BrowserIntent(intent=SEARCH_SITE, service=site, query=_clean(m.group(2)), evidence=["search-site"])
    m = _SITE_SEARCH2.search(text)
    if m:
        query, site = _clean(m.group(1)), m.group(2).strip().lower()
        if site in browser_config.WEBSITES:
            return BrowserIntent(intent=SEARCH_SITE, service=site, query=query, evidence=["search-site"])
    if service and _VERB_SEARCH.search(text) and ("for" in text or "about" in text):
        q = _query_after(_strip_service(text, service), "search") or _query_after(_strip_service(text, service), "look up")
        return BrowserIntent(intent=SEARCH_SITE, service=service, query=q, evidence=["search-service"])

    # ── SEARCH_WEB (fast retrieval, not Selenium — section 5/17) ──
    if _WEB_SEARCH.search(text) and not service:
        q = _query_after(text, "search") or _query_after(text, "look up")
        return BrowserIntent(intent=SEARCH_WEB, query=q, evidence=["web-search"])
    if _VERB_SEARCH.search(text) and ("for" in text or "about" in text) and not service:
        q = _query_after(text, "search")
        if q:
            return BrowserIntent(intent=SEARCH_WEB, query=q, evidence=["search-web-query"])

    # ── PLAY_MEDIA ──
    if _VERB_PLAY.search(text) and (service in MEDIA_SERVICES or _MEDIA_NOUN.search(text)):
        query = None
        stripped = _strip_service(text, service)
        if service:
            query = _query_after(stripped, "play")
        else:
            query = _query_after(text, "play")
        # "play some music" / "put on a song" → no query, just play
        if query and re.fullmatch(r"(?:some\s+|a\s+|an\s+)?(?:music|songs|song|playlist|track)\s*", query, re.I):
            query = None
        return BrowserIntent(
            intent=PLAY_MEDIA,
            service=service or (current_service if current_service in MEDIA_SERVICES else "spotify"),
            query=query,
            requires_confirmation=bool(_CONSEQUENTIAL.search(text)),
            evidence=["play"],
        )

    # ── OPEN_WEBSITE / NAVIGATE ──
    if _VERB_OPEN_WEBSITE.search(text) or (
        _VERB_OPEN.search(text) and (service or url or _extract_bare_domain(text))
    ):
        bare_domain = _extract_bare_domain(text)
        target_url = url or bare_domain or (lookup_site(service) if service else None)
        pure_open_website = bool(_VERB_OPEN_WEBSITE.search(text)) and not service
        intent = BrowserIntent(
            intent=NAVIGATE if (url or bare_domain or pure_open_website) else OPEN_WEBSITE,
            service=service,
            url=target_url,
            evidence=["open"],
        )
        intent.requires_confirmation = bool(_CONSEQUENTIAL.search(text))
        return intent

    # ── SCREENSHOT / SCROLL / EXTRACT / CLICK / TYPE / DOWNLOAD ──
    if _SCREENSHOT.search(text):
        return BrowserIntent(intent=SCREENSHOT, evidence=["screenshot"])
    m = _SCROLL.search(text)
    if m:
        return BrowserIntent(intent=SCROLL, direction=m.group(1).replace("to ", ""), evidence=["scroll"])
    if _EXTRACT.search(text):
        return BrowserIntent(intent=EXTRACT, evidence=["extract"])
    m = _CLICK.search(text)
    if m and len(m.group(1)) > 1:
        target = _clean(m.group(1).removesuffix("button"))
        if target:
            return BrowserIntent(
                intent=CLICK, target=target, requires_confirmation=bool(_CONSEQUENTIAL.search(text)), evidence=["click"]
            )
    m = _TYPE.search(text)
    if m:
        target = _clean(m.group(2)) if m.group(2) else None
        return BrowserIntent(
            intent=TYPE, target=target or ("search box" if "search" in text.lower() else None),
            text=_clean(m.group(1)), evidence=["type"],
        )
    if _DOWNLOAD.search(text):
        return BrowserIntent(intent=DOWNLOAD, requires_confirmation=True, evidence=["download"])

    # ── OTHER_BROWSER_ACTION ──
    if re.search(r"\b(?:browser|chrome)\b", text, re.I) and _VERB_OPEN.search(text):
        return BrowserIntent(intent=OTHER_BROWSER_ACTION, evidence=["other-browser"])

    return None
