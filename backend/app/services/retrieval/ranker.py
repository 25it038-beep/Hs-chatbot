"""Result ranking + deduplication + diversity capping (sections 4, 13, 18).

Collect candidates -> normalize URLs -> dedupe (URL + title similarity) ->
score (domain authority, freshness, keyword overlap, intent match, spam penalties) ->
select top N with domain diversity capping (max 2 per domain).
"""

import difflib
import re
import time
from datetime import date
from urllib.parse import urlparse

from .providers import SearchResult

_AUTHORITY_TIERS = {
    3: [
        "gov", "edu", "ac.", "mil", "int", "wikipedia.org", "arxiv.org", "pubmed", "who.int",
        "un.org", "europa.eu", "oecd.org", "nasa.gov", "irs.gov", "nih.gov", "cdc.gov", "fda.gov",
        "w3.org", "ietf.org", "rfc-editor.org", "ieee.org", "iso.org", "nature.com", "science.org",
    ],
    2: [
        "official", "developers.", "docs.", "developer.", "api.", "microsoft.com", "apple.com",
        "google.com", "openai.com", "anthropic.com", "nvidia.com", "amd.com", "intel.com",
        "github.com", "gitlab.com", "stackoverflow.com", "mdn.", "python.org", "nodejs.org",
        "react.dev", "vuejs.org", "angular.dev", "rust-lang.org", "golang.org", "aws.amazon.com",
        "cloud.google.com", "pypi.org", "npmjs.com", "huggingface.co",
    ],
    1: [
        "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk", "nytimes.com", "wsj.com", "ft.com",
        "theguardian.com", "bloomberg.com", "economist.com", "forbes.com", "aljazeera.com",
        "wired.com", "techcrunch.com", "theverge.com", "arstechnica.com", "anandtech.com",
        "tomshardware.com", "gsmarena.com", "bleepingcomputer.com",
    ],
}

_SPAM_HINTS = [
    "spam", "scam", "casino", "crypto-", "buyfollowers", "free-", "promo", "click-here",
    "porn", "adult", "coupon", "cracked", "warez", "torrent", "best-deals-now",
]
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
        host = (urlparse(url).hostname or "").lower()
        if host.startswith("www."):
            host = host[4:]
        return host
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
        if dom in seen_domains and _title_similarity(seen_domains[dom], r.title) > 0.88:
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
            if 0 <= days < 30:
                return 0.6 - (days / 60)
            elif 30 <= days < 180:
                return 0.3 - (days / 600)
        except (ValueError, TypeError):
            pass
    if _YEAR_IN_URL.search(r.url):
        return 0.35 if current else 0.1
    return 0.0


def score_results(
    results: list[SearchResult], query: str, current: bool, complexity: str
) -> list[SearchResult]:
    query_tokens = [t for t in re.split(r"\W+", query.lower()) if len(t) > 2]
    domain = _domain(query)
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
        s += authority * 0.45

        if domain and domain in host:
            s += 1.2  # explicit site match

        if r.kind == "news" and current:
            s += 0.5
        if r.kind == "docs":
            s += 0.3

        # Provider relevance score bonus (e.g. Tavily score)
        tavily_score = float(r.extra.get("tavily_score", 0.0))
        if tavily_score:
            s += min(tavily_score, 1.0) * 0.4

        # Spam / low-quality penalties
        if any(h in url_l for h in _SPAM_HINTS):
            s -= 2.5

        # Freshness (sections 12, 18)
        s += _freshness_bonus(r, current)

        # Truncated or junk title penalty
        if len(title_l) < 12:
            s -= 0.3

        r.score = round(s, 3)
        scored.append(r)

    scored.sort(key=lambda r: r.score, reverse=True)
    return scored


def select_top(results: list[SearchResult], n: int, max_per_domain: int = 2) -> list[SearchResult]:
    """Select top N results with domain diversity capping (section 18).

    Ensures no single domain monopolizes results, maintaining diverse perspectives.
    """
    domain_counts: dict[str, int] = {}
    selected: list[SearchResult] = []
    overflow: list[SearchResult] = []

    for r in results:
        dom = _domain(r.url or r.image_url)
        count = domain_counts.get(dom, 0)
        if count < max_per_domain:
            domain_counts[dom] = count + 1
            selected.append(r)
            if len(selected) >= n:
                return selected
        else:
            overflow.append(r)

    # Backfill if domain capping left room below n
    for r in overflow:
        if len(selected) >= n:
            break
        selected.append(r)

    return selected
