"""Webpage content extraction (sections 9, 10).

Removes scripts/styles/navigation/ads/cookie banners and extracts the
meaningful text, then splits into overlapping passages. Stdlib only.
"""

import re
from html.parser import HTMLParser

from .config import retrieval_config as cfg

_SKIP_TAGS = {"script", "style", "noscript", "svg", "iframe", "canvas", "template", "video", "audio", "picture", "form", "button", "nav", "footer", "aside"}
_BOILERPLATE_CLASS = re.compile(
    r"(nav|navbar|menu|footer|header|sidebar|cookie|advert|ads|popup|modal|"
    r"share|social|comment|related|recommended|breadcrumb|pagination|"
    r"newsletter|subscribe|consent|widget|banner)",
    re.I,
)
_HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "blockquote", "td", "caption", "dt", "dd", "pre", "br", "hr"}
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
_META_RE = re.compile(r'<meta[^>]+(?:name|property)=["\'](?:description|og:description)["\'][^>]*content=["\']([^"\']*)', re.I)
_OG_TITLE_RE = re.compile(r'<meta[^>]+property=["\']og:title["\'][^>]*content=["\']([^"\']*)', re.I)
_NOISE_LINES = re.compile(
    r"^(skip to (content|navigation)|cookie|accept( cookies| all)?|manage (preferences|consent)|"
    r"privacy policy|terms of service|about us|contact us|sign in|log in|sign up|subscribe|"
    r"advertisement|sponsored|related articles?|you might also like|share this|"
    r"©|copyright|all rights reserved|back to top|menu)$",
    re.I,
)


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._skip_until = None
        self._blocks: list[str] = []
        self._cur: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        attrs_map = {k.lower(): (v or "").lower() for k, v in attrs}
        if self._skip_depth:
            self._skip_depth += 1
            return
        if tag in _SKIP_TAGS:
            self._skip_depth = 1
            return
        classname = attrs_map.get("class", "")
        if _BOILERPLATE_CLASS.search(classname):
            self._skip_depth = 1
            return
        if tag in _HEADING_TAGS:
            self._flush()
            self._blocks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if self._skip_depth:
            if tag in _SKIP_TAGS:
                self._skip_depth = 0
            else:
                self._skip_depth -= 1
            return
        if tag in _HEADING_TAGS:
            self._flush()
            self._blocks.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self._cur.append(data)

    def _flush(self) -> None:
        text = "".join(self._cur)
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            self._blocks.append(text)
        self._cur = []

    def text(self) -> str:
        self._flush()
        return "\n".join(self._blocks)


def extract_text(html: str) -> str:
    """HTML -> cleaned main text (no JS/CSS/nav/ads)."""
    if not html:
        return ""
    parser = _TextExtractor()
    try:
        parser.feed(html)
    except Exception:
        pass
    text = parser.text()
    lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if len(line) < 90 and _NOISE_LINES.match(line):
            continue
        lines.append(line)
    return "\n".join(lines)


def extract_meta(html: str, fallback_title: str = "") -> dict:
    title = ""
    m = _TITLE_RE.search(html[:20_000])
    if m:
        title = re.sub(r"\s+", " ", m.group(1)).strip()[:200]
    if not title:
        m = _OG_TITLE_RE.search(html[:20_000])
        if m:
            title = m.group(1).strip()[:200]
    desc = ""
    m = _META_RE.search(html[:20_000])
    if m:
        desc = re.sub(r"\s+", " ", m.group(1)).strip()[:300]
    return {"title": title or fallback_title, "description": desc}


def chunk_passages(text: str, max_chars: Optional[int] = None) -> list[str]:
    """Split clean text into overlapping passages (~1200 chars)."""
    max_chars = max_chars or cfg.PASSAGE_CHARS
    overlap = cfg.PASSAGE_OVERLAP
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]
    passages = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            # cut at sentence boundary if possible
            cut = text.rfind(". ", start + max_chars // 2, end)
            if cut > start + max_chars // 2:
                end = cut + 1
        passage = text[start:end].strip()
        if passage:
            passages.append(passage)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
        if len(passages) > 200:
            break
    return passages


def html_to_passages(html: str) -> tuple[list[str], dict]:
    text = extract_text(html)
    meta = extract_meta(html)
    return chunk_passages(text), meta
