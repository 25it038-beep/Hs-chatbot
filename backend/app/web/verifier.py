"""Cross-source verification and claim consensus (section 16)."""

import re
from typing import Dict, List
from app.web.models import ClaimVerification, EvidenceItem, SourceMetadata


class ClaimVerifier:
    def verify_claims(
        self,
        key_claims: List[str],
        evidence: List[EvidenceItem],
        sources: List[SourceMetadata],
    ) -> List[ClaimVerification]:
        """Cross-check identified claims against extracted evidence items."""
        source_map = {s.source_id: s for s in sources}
        results: List[ClaimVerification] = []

        for idx, claim in enumerate(key_claims):
            tokens = [t for t in re.split(r"\W+", claim.lower()) if len(t) > 3]
            supporting_sources = set()

            for ev in evidence:
                text_low = ev.text.lower()
                hits = sum(1 for t in tokens if t in text_low)
                if hits >= max(2, len(tokens) // 2):
                    supporting_sources.add(ev.source_id)

            supporting_list = list(supporting_sources)
            # Count independent domains
            domains = {source_map[sid].domain for sid in supporting_list if sid in source_map}

            if len(domains) >= 2:
                status = "VERIFIED"
            elif len(domains) == 1:
                status = "PARTIAL"
            else:
                status = "UNVERIFIED"

            results.append(
                ClaimVerification(
                    claim_id=f"claim-{idx+1}",
                    claim_text=claim,
                    source_ids=supporting_list,
                    status=status,
                )
            )

        return results
