"""Source classification, authority scoring, and domain diversity ranking (sections 11, 14, 15)."""

import re
import time
from urllib.parse import urlparse
from typing import Any, List

from app.web.models import SourceMetadata, SourceType


_GOV_PATTERNS = ["gov", "mil", "int", "who.int", "un.org", "europa.eu", "nasa.gov", "nih.gov", "cdc.gov", "fda.gov", "nist.gov"]
_ACADEMIC_PATTERNS = ["edu", "ac.", "arxiv.org", "pubmed", "biorxiv.org", "nature.com", "science.org", "ieee.org", "springer.com"]
_OFFICIAL_PATTERNS = ["docs.", "developer.", "developers.", "api.", "github.com", "gitlab.com", "rfc-editor.org", "w3.org"]
_COMPANY_PATTERNS = ["nvidia.com", "apple.com", "google.com", "microsoft.com", "openai.com", "anthropic.com", "meta.com", "amazon.com"]
_NEWS_PATTERNS = [
    "reuters.com", "apnews.com", "bloomberg.com", "bbc.com", "nytimes.com", "wsj.com",
    "theguardian.com", "economist.com", "ft.com", "theverge.com", "arstechnica.com",
    "techcrunch.com", "wired.com", "tomshardware.com", "gsmarena.com", "anandtech.com"
]
_FORUM_PATTERNS = ["reddit.com", "quora.com", "stackexchange.com", "stackoverflow.com", "news.ycombinator.com", "discourse"]
_AGGREGATOR_PATTERNS = ["pricenprice", "mysmartprice", "91mobiles", "smartprix", "gadgets360", "pricebaba"]
_SPAM_PATTERNS = ["coupon", "casino", "scam", "promo", "cracked", "warez", "free-download"]


def classify_source_type(url: str) -> SourceType:
    """Classify the organizational category of a web source."""
    if not url:
        return SourceType.WEB
    host = (urlparse(url).hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]

    if any(p in host for p in _GOV_PATTERNS):
        return SourceType.GOVERNMENT
    if any(p in host for p in _ACADEMIC_PATTERNS):
        return SourceType.ACADEMIC
    if any(p in host for p in _OFFICIAL_PATTERNS):
        return SourceType.OFFICIAL
    if any(p in host for p in _COMPANY_PATTERNS):
        return SourceType.COMPANY
    if any(p in host for p in _NEWS_PATTERNS):
        return SourceType.NEWS
    if any(p in host for p in _FORUM_PATTERNS):
        return SourceType.COMMUNITY
    if any(p in host for p in _AGGREGATOR_PATTERNS):
        return SourceType.AGGREGATOR
    if "blog" in host or "medium.com" in host or "substack.com" in host:
        return SourceType.BLOG

    return SourceType.WEB


def score_source_authority(source_type: SourceType, url: str) -> float:
    """Score domain authority between 0.0 and 1.0."""
    host = (urlparse(url).hostname or "").lower()
    if any(s in host for s in _SPAM_PATTERNS):
        return 0.0

    scores = {
        SourceType.GOVERNMENT: 0.95,
        SourceType.ACADEMIC: 0.90,
        SourceType.OFFICIAL: 0.88,
        SourceType.COMPANY: 0.82,
        SourceType.NEWS: 0.78,
        SourceType.TECHNICAL: 0.75,
        SourceType.PRIMARY: 0.85,
        SourceType.COMMUNITY: 0.55,
        SourceType.BLOG: 0.45,
        SourceType.AGGREGATOR: 0.35,
        SourceType.WEB: 0.50,
        SourceType.FORUM: 0.40,
    }
    return scores.get(source_type, 0.50)


class SourceRanker:
    def rank_and_select(
        self,
        raw_results: List[Any],
        query: str,
        max_sources: int = 8,
        max_per_domain: int = 2,
    ) -> List[SourceMetadata]:
        """Classify, score, and select top sources with domain diversity capping."""
        query_tokens = [t for t in re.split(r"\W+", query.lower()) if len(t) > 2]
        scored_sources: List[SourceMetadata] = []

        for idx, item in enumerate(raw_results):
            url = getattr(item, "url", "") or (item.get("url") if isinstance(item, dict) else "")
            title = getattr(item, "title", "") or (item.get("title") if isinstance(item, dict) else "")
            snippet = getattr(item, "body", "") or getattr(item, "snippet", "") or (item.get("body", "") if isinstance(item, dict) else "")
            published = getattr(item, "published", None) or (item.get("published") if isinstance(item, dict) else None)

            if not url or not title:
                continue

            host = (urlparse(url).hostname or "").lower()
            if host.startswith("www."):
                host = host[4:]

            stype = classify_source_type(url)
            auth = score_source_authority(stype, url)

            # Relevance score from query overlap
            text_combo = f"{title} {snippet}".lower()
            hits = sum(1 for t in query_tokens if t in text_combo)
            relevance = hits / max(len(query_tokens), 1)

            # Extra authority bonus for primary / official matches
            if any(t in title.lower() for t in ["official", "documentation", "announcement", "specifications"]):
                auth = min(1.0, auth + 0.1)

            final_score = round(auth * 0.45 + relevance * 0.55, 3)

            meta = SourceMetadata(
                source_id=idx + 1,
                title=title[:200],
                url=url,
                domain=host,
                source_type=stype,
                authority_score=auth,
                published_date=published,
                snippet=snippet[:500],
                relevance_score=final_score,
            )
            scored_sources.append(meta)

        # Sort by final score descending
        scored_sources.sort(key=lambda s: s.relevance_score, reverse=True)

        # Apply domain diversity capping (max_per_domain)
        selected: List[SourceMetadata] = []
        domain_counts: dict = {}
        overflow: List[SourceMetadata] = []

        for s in scored_sources:
            d = s.domain
            count = domain_counts.get(d, 0)
            if count < max_per_domain:
                domain_counts[d] = count + 1
                selected.append(s)
                if len(selected) >= max_sources:
                    break

        # Re-index source IDs consecutively 1..N for clean citation formatting
        for i, s in enumerate(selected):
            s.source_id = i + 1

        return selected
