"""Passage reranking (section 10).

After extraction, score passages against the query (keyword coverage,
position bonus, length penalty) and select the best evidence, bounded by a
total context budget so we never flood the model.
"""

import re
from typing import Optional

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
    tokens = _query_tokens(query)
    entries: list[str] = []
    sources: list[dict] = []
    used = 0

    for item in fetched:
        content = item.get("content") or ""
        if not content:
            continue
        passages, meta = html_to_passages(content)
        if not passages:
            continue
        scored = score_passages(passages, query)

        # take top passages until this page's share or budget runs out
        page_used = 0
        per_page_cap = min(2_400, budget // 3)
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

        title = meta.get("title") or item.get("url", "")
        page_sources = []
        for passage in page_entries:
            cleaned = sanitize_webpage_text(passage)
            if not cleaned:
                continue
            page_sources.append(
                {"title": title[:180], "url": item.get("final_url") or item.get("url"), "text": cleaned[:1_600]}
            )
        if page_sources:
            sources.extend(page_sources)
            entries.append(f"### {title[:150]}\nSource: {(item.get('final_url') or item.get('url'))[:300]}")
            for s in page_sources:
                entries.append(s["text"])

    if not entries:
        return "", []

    context = safe_context_wrapper("\n\n".join(entries))
    return context[: budget * 2 + 4_000], sources
