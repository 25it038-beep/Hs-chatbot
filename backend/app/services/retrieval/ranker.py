"""Result ranking + deduplication (sections 4, 13, 18).

Collect candidates -> normalize URLs -> dedupe (URL + title similarity) ->
score (domain authority, freshness, keyword overlap, intent match) ->
select top N. Fetching happens only for the selected subset.
"""

import difflib
import re
import time
from datetime import date
from urllib.parse import urlparse

from .providers import SearchResult

_AUTHORITY_TIERS = {
    3: ["gov", "edu", "ac.", "mil", "int", "wikipedia.org", "arxiv.org", "pubmed", "who.int",
        "un.org", "europa.eu", "oecd.org", "nasa.gov", "irs.gov", "nih.gov", "cdc.gov", "fda.gov"],
    2: ["official", "developers.", "docs.", "developer.", "api.", "microsoft.com", "apple.com",
        "google.com", "openai.com", "anthropic.com", "nvidia.com", "amd.com", "intel.com",
        "github.com", "stackoverflow.com", "mdn.", "python.org", "nodejs.org", "react.dev"],
    1: ["reuters.com", "apnews.com", "bbc.com", "bbc.co.uk", "nytimes.com", "wsj.com", "ft.com",
        "theguardian.com", "bloomberg.com", "nature.com", "science.org", "ieee.org", "forbes.com",
        "cnn.com", "aljazeera.com", "economist.com", "wired.com", "techcrunch.com", "verge.com"],
}
_SPAM_HINTS = ["spam", "scam", "casino", "crypto-", "buyfollowers", "free-", "promo", "click-here", "porn", "adult"]
_UTM = re.compile(r"[?&](utm_|fbclid|gclid|ref|ref_src|mc_|igshid|spm)", re.I)
_YEAR_IN_URL = re.compile(r"/(?:20\d{2})/")


def normalize_url(url: str) -> str:
    try:
        parsed = urlparse(url)
    except ValueError:
        return url
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = re.sub(r"/+$", "", parsed.path or "")
    path = re.sub(r"(?:/index\.(?:html?|php|aspx?))$", "", path)
    return f"{host}{path.lower()}"


def _domain(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except ValueError:
        return ""


def _title_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()


def dedupe_results(results: list[SearchResult]) -> list[SearchResult]:
    seen_urls: set[str] = set()
    seen_domains: dict[str, str] = {}
    out: list[SearchResult] = []
    for r in results:
        nurl = normalize_url(r.url or r.image_url)
        if not nurl:
            continue
        if nurl in seen_urls:
            continue
        dom = _domain(r.url or r.image_url)
        if dom in seen_domains and _title_similarity(seen_domains[dom], r.title) > 0.9:
            continue
        seen_urls.add(nurl)
        seen_domains[dom] = r.title
        out.append(r)
    return out


def _freshness_bonus(r: SearchResult, current: bool) -> float:
    if r.published:
        try:
            ts = time.mktime(time.strptime(r.published[:10], "%Y-%m-%d"))
            days = (time.time() - ts) / 86400
            if 0 <= days < 90:
                return 0.5 - days / 180
        except (ValueError, TypeError):
            pass
    if _YEAR_IN_URL.search(r.url):
        return 0.3 if current else 0.1
    return 0.0


def score_results(
    results: list[SearchResult], query: str, current: bool, complexity: str
) -> list[SearchResult]:
    query_tokens = [t for t in re.split(r"\W+", query.lower()) if len(t) > 2]
    domain = _domain(query)  # e.g. query targets a specific site
    scored = []
    for r in results:
        s = 0.0
        title_l = r.title.lower()
        body_l = r.body.lower()
        url_l = (r.url or r.image_url or "").lower()
        host = _domain(r.url or r.image_url)

        # Keyword overlap
        hits = sum(1 for t in query_tokens if t in title_l)
        hits += 0.5 * sum(1 for t in query_tokens if t in body_l)
        s += hits * 0.6

        # Domain authority (section 13)
        authority = 0
        for tier, pats in _AUTHORITY_TIERS.items():
            if any(p in host for p in pats):
                authority = tier
                break
        s += authority * 0.35

        if domain and domain in host:
            s += 1.0  # explicit site match

        if r.kind == "news" and current:
            s += 0.4
        if r.kind == "docs":
            s += 0.2

        # Provider quality signal: Tavily results carry a relevance score
        # from the provider itself (0..1) — small bonus, never dominant.
        tavily_score = float(r.extra.get("tavily_score", 0.0))
        if tavily_score:
            s += min(tavily_score, 1.0) * 0.4

        # Spam / low-quality penalties
        if any(h in url_l for h in _SPAM_HINTS):
            s -= 2.0

        # Freshness (section 12)
        s += _freshness_bonus(r, current)

        # Long-tail junk penalty
        if len(title_l) < 12:
            s -= 0.3

        r.score = round(s, 3)
        scored.append(r)

    scored.sort(key=lambda r: r.score, reverse=True)
    return scored


def select_top(results: list[SearchResult], n: int) -> list[SearchResult]:
    return results[:n]
