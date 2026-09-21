"""Deep source reading and contextual evidence extraction (sections 12, 13)."""

import asyncio
import re
from typing import Dict, List, Optional

from app.services.retrieval.extractor import extract_meta, extract_text, chunk_passages
from app.services.retrieval.fetcher import PageFetcher
from app.services.retrieval.security import sanitize_webpage_text
from app.web.models import EvidenceItem, SourceMetadata


class SourceReader:
    def __init__(self):
        self._fetcher = PageFetcher()

    async def read_sources(
        self,
        sources: List[SourceMetadata],
        query: str,
        budget_s: float = 8.0,
    ) -> Dict[int, List[str]]:
        """Fetch and extract high-signal passages for each source."""
        urls = [s.url for s in sources]
        if not urls:
            return {}

        fetched = await self._fetcher.fetch_many(urls, budget_s=budget_s, scope="web")
        results: Dict[int, List[str]] = {}

        # Map URL to fetched content
        content_by_url = {item["url"]: item for item in fetched}

        query_tokens = [t for t in re.split(r"\W+", query.lower()) if len(t) > 2]

        for source in sources:
            item = content_by_url.get(source.url)
            if not item or not item.get("content"):
                # Fallback to snippet if fetch failed
                if source.snippet:
                    results[source.source_id] = [source.snippet]
                continue

            raw_html = item.get("content", "")
            meta = extract_meta(raw_html, fallback_title=source.title)
            if meta.get("published") and not source.published_date:
                source.published_date = meta["published"]

            text = extract_text(raw_html)
            passages = chunk_passages(text, max_chars=1400)

            # Score passages based on query overlap and statistics/tables presence
            scored_passages = []
            for p in passages:
                p_clean = sanitize_webpage_text(p)
                if len(p_clean) < 80:
                    continue
                pl = p_clean.lower()
                hits = sum(1 for t in query_tokens if t in pl)
                stat_bonus = 0.3 if re.search(r"(\d+%|\$\d+|₹\d+|\b\d+\s*(?:gb|tb|mhz|ghz|core|billion|million)\b)", pl) else 0.0
                table_bonus = 0.4 if ("|" in p_clean or "\t" in p_clean) else 0.0
                score = hits + stat_bonus + table_bonus
                scored_passages.append((p_clean, score))

            scored_passages.sort(key=lambda x: x[1], reverse=True)
            # Take top 3 most relevant passages per source
            top_passages = [p for p, _ in scored_passages[:3]]
            if top_passages:
                results[source.source_id] = top_passages
            elif source.snippet:
                results[source.source_id] = [source.snippet]

        return results
