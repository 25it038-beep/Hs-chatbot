"""Conflict and discrepancy detection across sources (section 32)."""

import re
from typing import Dict, List
from app.web.models import EvidenceItem, SourceMetadata


class ConflictDetector:
    def detect_conflicts(
        self,
        evidence: List[EvidenceItem],
        sources: List[SourceMetadata],
    ) -> List[str]:
        """Detect conflicting numbers, dates, or specifications across evidence items."""
        conflicts: List[str] = []
        source_map = {s.source_id: s for s in sources}

        # 1. Price pattern discrepancy check
        price_by_source: Dict[int, List[str]] = {}
        price_re = re.compile(r"(?:₹|\$|€|rs\.?|inr|usd)\s*([\d,]+)", re.I)

        for ev in evidence:
            found = price_re.findall(ev.text)
            if found:
                price_by_source.setdefault(ev.source_id, []).extend(found)

        # Compare prices across different domains
        unique_prices = set()
        for sid, p_list in price_by_source.items():
            for p in p_list:
                cleaned_p = p.replace(",", "")
                if len(cleaned_p) >= 3:
                    unique_prices.add((cleaned_p, sid))

        # If we see multiple distinct prices from different sources
        distinct_vals = {p[0] for p in unique_prices}
        if len(distinct_vals) > 1 and len(distinct_vals) <= 4:
            sids = list({p[1] for p in unique_prices})
            if len(sids) >= 2:
                s_names = [source_map[s].domain for s in sids if s in source_map]
                conflicts.append(
                    f"Pricing discrepancies noted across sources ({', '.join(s_names[:3])}): "
                    f"reported figures vary between {', '.join(list(distinct_vals)[:3])}."
                )

        # 2. Date discrepancy check for future releases
        date_re = re.compile(r"\b(early|mid|late|q[1-4]|first half|second half)?\s*(202\d)\b", re.I)
        dates_found = set()
        for ev in evidence:
            for match in date_re.finditer(ev.text):
                dates_found.add(match.group(0).strip())

        if len(dates_found) > 1 and len(dates_found) <= 3:
            conflicts.append(
                f"Timeline variance: sources reference differing release horizons ({', '.join(dates_found)})."
            )

        return conflicts
