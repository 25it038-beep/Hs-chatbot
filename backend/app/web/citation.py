"""Citation formatting, source card generation, and context building (sections 18, 40, 41)."""

from typing import List
from app.services.retrieval.security import safe_context_wrapper
from app.web.models import EvidenceItem, SourceMetadata, SourceType


def format_source_badge(source_type: SourceType) -> str:
    badges = {
        SourceType.OFFICIAL: "Official",
        SourceType.GOVERNMENT: "Government",
        SourceType.ACADEMIC: "Academic",
        SourceType.PRIMARY: "Primary Source",
        SourceType.NEWS: "News",
        SourceType.TECHNICAL: "Technical",
        SourceType.COMPANY: "Company",
        SourceType.COMMUNITY: "Community",
        SourceType.BLOG: "Blog",
    }
    return badges.get(source_type, "Web")


def format_sources_markdown(sources: List[SourceMetadata]) -> str:
    """Format a clean markdown bibliography of retrieved sources."""
    if not sources:
        return ""
    lines = ["\n### Sources"]
    for s in sources:
        badge = format_source_badge(s.source_type)
        date_str = f" • {s.published_date}" if s.published_date else ""
        lines.append(f"- [{s.source_id}] [{s.title}]({s.url}) — *{s.domain}* `[{badge}]`{date_str}")
    return "\n".join(lines)


def build_research_context(
    sources: List[SourceMetadata],
    evidence: List[EvidenceItem],
    conflicts: List[str],
) -> str:
    """Build structured context with clear source numbers and strict citation directives."""
    source_map = {s.source_id: s for s in sources}
    entries: List[str] = []

    for sid in sorted(source_map.keys()):
        s = source_map[sid]
        badge = format_source_badge(s.source_type)
        date_info = f" | Date: {s.published_date}" if s.published_date else ""
        header = f"### [{sid}] {s.title}\nDomain: {s.domain} | Type: {badge} | URL: {s.url}{date_info}"
        
        # Gather evidence for this source
        passages = [e.text for e in evidence if e.source_id == sid]
        if not passages and s.snippet:
            passages = [s.snippet]

        if passages:
            entries.append(f"{header}\n" + "\n\n".join(passages[:3]))

    conflict_block = ""
    if conflicts:
        conflict_block = (
            "\nDISCREPANCY ALERT:\n"
            + "\n".join(f"- {c}" for c in conflicts)
            + "\nExplicitly disclose these contradictions in your answer.\n"
        )

    directives = (
        "PERPLEXITY-STYLE ANSWER REQUIREMENTS:\n"
        "1. DIRECT ANSWER FIRST: Begin with the immediate, direct answer or executive summary in the opening 1-2 sentences.\n"
        "2. INLINE CITATIONS: Attribute every key fact, statistic, release date, and price inline with brackets e.g. [1], [2].\n"
        "3. STRUCTURED DETAILS: Use clear markdown sections, bullet points, and comparison tables where helpful.\n"
        "4. OBJECTIVITY & CONFLICTS: Distinguish verified facts from rumors/opinions. Acknowledge conflicting claims honestly.\n"
        "5. ZERO FABRICATION: Only cite sources [1] through [{max_src}] that actually appear above. Never invent sources or URLs.\n"
    ).format(max_src=len(sources))

    body = "\n\n---\n\n".join(entries) + f"\n\n{conflict_block}\n\n{directives}"
    return safe_context_wrapper(body)
