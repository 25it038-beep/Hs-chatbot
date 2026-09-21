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

    today_str = "Monday, September 21, 2026 (2026-09-21)"
    directives = (
        f"ALWAYS-CURRENT DATA & PERPLEXITY-STYLE ANSWER REQUIREMENTS (Current Date: {today_str}):\n"
        "1. DIRECT ANSWER FIRST: State the direct, factual answer clearly in the opening 1-2 sentences.\n"
        "2. INLINE CITATIONS: Attribute every fact, person, date, price, or specification inline with bracketed numbers, e.g. [1], [2].\n"
        "3. SOURCES SECTION: At the bottom of your response, include a '### Sources' section listing each source with its link: - [1] [Title](url)\n"
        "4. FACTUAL ENTITIES: Always state the actual official or public figure (e.g. President of India, Chief Minister of Tamil Nadu, CEO, etc.) based on the retrieved evidence. Never deflect to an identity statement.\n"
        "5. OBJECTIVITY & CONFLICTS: Distinguish verified facts from rumors. Acknowledge conflicting claims honestly.\n"
        "6. ZERO FABRICATION: Only cite sources [1] through [{max_src}] that actually appear in the evidence above. Never invent sources or URLs.\n"
    ).format(max_src=len(sources))

    body = f"Current System Date: {today_str}\n\n" + "\n\n---\n\n".join(entries) + f"\n\n{conflict_block}\n\n{directives}"
    return safe_context_wrapper(body)
