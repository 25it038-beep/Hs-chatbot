"""Passage reranking and structured evidence construction (sections 9, 10, 20).

After extraction, score passages against the query (keyword coverage,
position bonus, length penalty) and select the best evidence, bounded by a
total context budget so we never flood the model.
Structures evidence with numbered source markers [Source 1], [Source 2] for precise citation.
"""

import re
from typing import Optional
from urllib.parse import urlparse

from .config import retrieval_config as cfg
from .extractor import html_to_passages
from .security import safe_context_wrapper, sanitize_webpage_text


def _query_tokens(query: str) -> list[str]:
    return [t for t in re.split(r"\W+", query.lower()) if len(t) > 2]


def score_passages(passages: list[str], query: str) -> list[tuple[str, float]]:
    tokens = _query_tokens(query)
    scored = []
    for idx, p in enumerate(passages):
        pl = p.lower()
        hits = sum(1 for t in tokens if t in pl)
        coverage = hits / max(len(tokens), 1)
        position_bonus = 0.15 if idx == 0 else (0.05 if idx < 4 else 0.0)
        length_penalty = 0.1 if len(p) < 200 else 0.0
        score = coverage * 2.0 + position_bonus - length_penalty
        scored.append((p, round(score, 3)))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


def build_evidence(
    fetched: list[dict], query: str, max_chars: Optional[int] = None
) -> tuple[str, list[dict]]:
    """fetched: [{'url', 'final_url', 'content', 'error'}].
    Returns (context_string, source_meta_list)."""
    budget = max_chars or cfg.MAX_CONTEXT_CHARS
    entries: list[str] = []
    sources: list[dict] = []
    used = 0
    source_idx = 1

    for item in fetched:
        content = item.get("content") or ""
        if not content:
            continue
        passages, meta = html_to_passages(content)
        if not passages:
            continue
        scored = score_passages(passages, query)

        # Take top passages until page cap or global budget is met
        page_used = 0
        per_page_cap = min(2_400, budget // 2)
        page_entries: list[str] = []
        for passage, _ in scored:
            take = min(len(passage), 1_600)
            if used + take > budget or page_used + take > per_page_cap:
                break
            page_used += take
            used += take
            page_entries.append(passage)

        if not page_entries:
            continue

        title = (meta.get("title") or item.get("url", "")).strip()
        final_url = item.get("final_url") or item.get("url") or ""
        pub_date = meta.get("published") or ""

        page_sources = []
        for passage in page_entries:
            cleaned = sanitize_webpage_text(passage)
            if not cleaned:
                continue
            page_sources.append(
                {
                    "source_id": source_idx,
                    "title": title[:180],
                    "url": final_url,
                    "published": pub_date,
                    "text": cleaned[:1_600],
                }
            )

        if page_sources:
            sources.extend(page_sources)
            date_info = f" | Published: {pub_date}" if pub_date else ""
            entries.append(f"### [Source {source_idx}] {title[:150]}\nURL: {final_url[:300]}{date_info}")
            for s in page_sources:
                entries.append(s["text"])
            source_idx += 1

    if not entries:
        return "", []

    citation_instructions = (
        "CITATION INSTRUCTIONS:\n"
        "- The external web sources above are numbered [Source 1], [Source 2], etc.\n"
        "- Base your answer directly on these facts. Support key claims with citations like [Source 1] or [Source 2].\n"
        "- If the sources do not provide sufficient information or if they contradict each other, explicitly note the limitation or conflict.\n"
        "- Do NOT invent URLs or fabricate claims not present in the sources.\n"
    )

    combined_text = "\n\n".join(entries) + f"\n\n{citation_instructions}"
    context = safe_context_wrapper(combined_text)
    return context[: budget * 2 + 4_000], sources
