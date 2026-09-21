"""Deep Research Engine: multi-stage planning, iterative gap-filling, and comprehensive report synthesis (sections 5, 26, 27, 28, 29, 63)."""

import asyncio
import time
from typing import Awaitable, Callable, Optional, List, Dict

from app.services.retrieval.providers import provider_pool
from app.web.cache import search_cache
from app.web.citation import build_research_context, format_sources_markdown
from app.web.conflict import ConflictDetector
from app.web.deduplication import deduplicate_sources
from app.web.evidence import EvidenceEngine
from app.web.models import (
    EvidenceItem,
    ResearchPlan,
    ResearchRequest,
    ResearchSubtask,
    SearchMode,
    SearchResultBundle,
    SourceMetadata,
)
from app.web.query_planner import QueryPlanner
from app.web.search_router import extract_constraints
from app.web.source_ranker import SourceRanker
from app.web.source_reader import SourceReader
from app.web.verifier import ClaimVerifier

StatusCallback = Optional[Callable[[str], Awaitable[None]]]


class ResearchService:
    """Perplexity-style Deep Research Engine."""

    def __init__(self):
        self._planner = QueryPlanner()
        self._ranker = SourceRanker()
        self._reader = SourceReader()
        self._evidence_engine = EvidenceEngine()
        self._conflict_detector = ConflictDetector()
        self._verifier = ClaimVerifier()
        self._pool = provider_pool

    async def _notify(self, cb: StatusCallback, msg: str) -> None:
        if cb:
            try:
                await cb(msg)
            except Exception:
                pass

    async def conduct_research(
        self,
        query: str,
        depth: str = "comprehensive",
        max_sources: int = 12,
        status_cb: StatusCallback = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> SearchResultBundle:
        start_t = time.time()
        constraints = extract_constraints(query)

        # 1. Create Deep Research Plan
        await self._notify(status_cb, "Developing deep research plan & subquestions...")
        plan = self._planner.create_research_plan(query, constraints=constraints, chat_history=chat_history)

        # 2. First-pass parallel search across all subtasks
        await self._notify(status_cb, f"Executing investigation across {len(plan.subtasks)} research subtasks...")
        all_queries = []
        for subtask in plan.subtasks:
            all_queries.extend(subtask.search_queries)

        search_jobs = [self._pool.text(q, limit=8, kind="web") for q in all_queries]
        raw_nested = await asyncio.gather(*search_jobs, return_exceptions=True)

        raw_candidates = []
        for res in raw_nested:
            if isinstance(res, list):
                raw_candidates.extend(res)

        # 3. Deduplicate and initial ranking
        deduped = deduplicate_sources(raw_candidates)
        ranked_sources = self._ranker.rank_and_select(
            deduped,
            query=query,
            max_sources=max_sources,
            max_per_domain=2,
        )

        # 4. Deep reading of sources
        await self._notify(status_cb, f"Deep-reading evidence across {len(ranked_sources)} sources...")
        passages_map = await self._reader.read_sources(ranked_sources, query=query, budget_s=10.0)
        evidence = self._evidence_engine.assemble_evidence(passages_map, ranked_sources)

        # 5. Gap Analysis & Iterative Second-Pass Search (sections 27, 28)
        # Check subtask evidence coverage
        evidence_text_combined = " ".join([e.text.lower() for e in evidence])
        gap_queries = []
        for subtask in plan.subtasks:
            # Check if keywords from question appear in evidence
            tokens = [t for t in subtask.question.lower().split() if len(t) > 4]
            hits = sum(1 for t in tokens if t in evidence_text_combined)
            if hits < 2:
                plan.gaps_identified.append(subtask.question)
                gap_queries.extend(self._planner.plan_gap_queries(subtask, plan.topic))

        if gap_queries:
            await self._notify(status_cb, f"Filling identified knowledge gaps with {len(gap_queries)} targeted searches...")
            gap_jobs = [self._pool.text(gq, limit=6, kind="web") for gq in gap_queries[:4]]
            gap_nested = await asyncio.gather(*gap_jobs, return_exceptions=True)
            gap_candidates = []
            for res in gap_nested:
                if isinstance(res, list):
                    gap_candidates.extend(res)
            if gap_candidates:
                new_deduped = deduplicate_sources(ranked_sources + gap_candidates)
                ranked_sources = self._ranker.rank_and_select(
                    new_deduped,
                    query=query,
                    max_sources=max_sources + 4,
                    max_per_domain=2,
                )
                passages_map = await self._reader.read_sources(ranked_sources, query=query, budget_s=8.0)
                evidence = self._evidence_engine.assemble_evidence(passages_map, ranked_sources)

        # 6. Discrepancy & Conflict Detection
        await self._notify(status_cb, "Cross-checking claims & detecting discrepancies...")
        conflicts = self._conflict_detector.detect_conflicts(evidence, ranked_sources)

        # 7. Build Deep Research Context with report generation directives
        plan.total_sources_consulted = len(ranked_sources)
        await self._notify(status_cb, "Synthesizing comprehensive research report...")

        report_directives = (
            "DEEP RESEARCH REPORT STRUCTURE:\n"
            "Produce a thorough, authoritative, well-structured research report formatted in clean Markdown:\n"
            "1. EXECUTIVE SUMMARY: High-level synthesis of key findings and breakthroughs.\n"
            "2. CURRENT LANDSCAPE & DEVELOPMENTS: In-depth analysis of state of the art in {year}.\n"
            "3. ARCHITECTURAL & TECHNICAL SPECIFICATIONS: Detailed comparison of technical approaches.\n"
            "4. STRUCTURED COMPARISON TABLE: A markdown comparison matrix summarizing key players, specs, costs, and availability.\n"
            "5. CHALLENGES, BOTTLENECKS & LIMITATIONS: Honest evaluation of what remains unproven or unresolved.\n"
            "6. INLINE CITATIONS: Every factual assertion must be attributed inline with [1], [2], etc.\n"
        ).format(year=constraints.get("year", "2026"))

        base_context = build_research_context(ranked_sources, evidence, conflicts)
        deep_context = f"{report_directives}\n\n{base_context}"

        bundle = SearchResultBundle(
            mode=SearchMode.DEEP,
            original_query=query,
            resolved_query=plan.topic,
            structured_context=deep_context,
            sources=ranked_sources,
            evidence=evidence,
            conflicts=conflicts,
            duration_ms=(time.time() - start_t) * 1000,
            research_plan=plan,
        )

        return bundle
