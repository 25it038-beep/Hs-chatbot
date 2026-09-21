"""Evidence collection and structured claim mapping (section 17)."""

import uuid
from typing import Dict, List
from app.web.models import EvidenceItem, SourceMetadata


class EvidenceEngine:
    def assemble_evidence(
        self,
        source_passages: Dict[int, List[str]],
        sources: List[SourceMetadata],
    ) -> List[EvidenceItem]:
        """Convert extracted source passages into structured EvidenceItem objects."""
        items: List[EvidenceItem] = []
        source_map = {s.source_id: s for s in sources}

        for source_id, passages in source_passages.items():
            source = source_map.get(source_id)
            if not source:
                continue

            for idx, p in enumerate(passages):
                item = EvidenceItem(
                    evidence_id=f"evi-{source_id}-{idx+1}",
                    source_id=source_id,
                    text=p.strip(),
                    relevance=source.relevance_score,
                    extracted_at=source.published_date,
                )
                items.append(item)

        return items
