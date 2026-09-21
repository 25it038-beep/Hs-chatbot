"""Query planning, decomposition, multi-angle generation, and gap-filling (sections 8, 9, 10, 26)."""

import re
from datetime import date
from typing import Any, Dict, List, Optional

from app.web.models import ResearchPlan, ResearchSubtask, SearchMode

_CONVERSATIONAL_PREFIXES = re.compile(
    r"(?i)^\s*(?:please\s+|pls\s+)?(?:(?:can you|could you|would you|can u)\s+)?"
    r"(?:(?:please\s+)?(?:tell me|give me|find|search for|look up|show me|check|research|explain|describe)\s+)?"
    r"(?:(?:about|information on|details (?:about|on)|sources for)\s+)?"
    r"(?:(?:what|whats|what'?s|who|whom|which|where|when|how)\s+(?:is|are|was|were|do|does|did|can|will)\s+)?"
    r"(?:(?:the|a|an)\s+)*"
)

_PRONOUNS = re.compile(r"\b(it|its|they|them|their|this|that|these|those)\b", re.I)


def clean_subject(query: str) -> str:
    """Extract clean subject core from query."""
    q = _CONVERSATIONAL_PREFIXES.sub("", query.strip())
    q = re.sub(r"[.?!]+$", "", q).strip()
    return q or query.strip()


def resolve_anaphora(query: str, chat_history: Optional[List[Dict[str, str]]] = None) -> str:
    """Resolve conversational pronouns using recent chat history."""
    if not chat_history:
        return query

    words = query.strip().split()
    if _PRONOUNS.search(query) or len(words) <= 4:
        for msg in reversed(chat_history[-3:]):
            content = msg.get("content", "")
            if not content or len(content) > 400:
                continue
            cleaned = clean_subject(content)
            if 1 <= len(cleaned.split()) <= 6:
                if len(words) <= 4 and cleaned.lower() not in query.lower():
                    return f"{cleaned} {query.strip()}"
                return re.sub(r"\b(it|this|that|these|those)\b", cleaned, query, flags=re.I)
    return query


class QueryPlanner:
    def __init__(self):
        self._current_year = str(date.today().year)

    def plan_queries(
        self,
        query: str,
        mode: SearchMode,
        constraints: Optional[Dict[str, Any]] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> List[str]:
        """Generate optimized multi-angle search queries based on mode and constraints."""
        resolved = resolve_anaphora(query, chat_history)
        base = clean_subject(resolved)
        constraints = constraints or {}
        year = constraints.get("year") or self._current_year
        region = constraints.get("region")

        if mode == SearchMode.FAST:
            # Fast mode: primary query + optional recency tag
            queries = [base]
            if "latest" in query.lower() or "current" in query.lower() or "today" in query.lower():
                if year not in base:
                    queries.append(f"{base} {year}")
            return queries[:2]

        queries: List[str] = [base]

        # Angle 1: Official / Primary Documentation
        # Angle 1: Official / Primary Documentation / Specs
        tech_tokens = ["nvidia", "amd", "intel", "apple", "google", "meta", "blackwell", "rtx", "model", "library", "framework", "api", "software", "docs", "spec", "gpu", "cpu"]
        if any(w in base.lower() for w in tech_tokens):
            queries.append(f"{base} official documentation")
            queries.append(f"{base} specifications official")
        elif constraints.get("category") in ["laptop", "phone", "gpu", "cpu", "robot"]:
            queries.append(f"{base} manufacturer specifications")
        else:
            queries.append(f"{base} official")

        # Angle 2: Recency / Announcements
        if year not in base:
            queries.append(f"{base} latest updates {year}")
        else:
            queries.append(f"{base} release announcement")

        # Angle 3: Regional / Pricing / Criteria specific
        if constraints.get("budget"):
            budget_str = constraints["budget"]
            queries.append(f"{base} price {budget_str} {region or ''}".strip())
        elif region:
            queries.append(f"{base} price availability {region}")

        # Angle 4: Benchmarks / Comparative reviews
        if constraints.get("criteria"):
            crit_str = " ".join(constraints["criteria"][:2])
            queries.append(f"{base} review {crit_str} comparison")
        elif "vs" in base.lower() or "compare" in base.lower():
            queries.append(f"{base} comparison benchmark")
        else:
            queries.append(f"{base} overview analysis")

        # Deduplicate while preserving order
        seen = set()
        unique = []
        for q in queries:
            norm = re.sub(r"\s+", " ", q.strip().lower())
            if norm and norm not in seen:
                seen.add(norm)
                unique.append(q.strip())

        max_q = 6 if mode == SearchMode.PRO else 8
        return unique[:max_q]

    def create_research_plan(
        self,
        query: str,
        constraints: Optional[Dict[str, Any]] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> ResearchPlan:
        """Create a multi-subtask structured research plan for Deep Research."""
        resolved = resolve_anaphora(query, chat_history)
        base = clean_subject(resolved)
        constraints = constraints or {}
        year = constraints.get("year") or self._current_year

        objectives = [
            f"Analyze current state and recent announcements ({year})",
            "Identify major players, architectures, and technical approaches",
            "Evaluate capabilities, specifications, performance, and costs",
            "Investigate current limitations, challenges, and open problems",
        ]

        subtasks = [
            ResearchSubtask(
                subtask_id="subtask-1",
                question=f"What is the current state and latest developments of {base} in {year}?",
                search_queries=[f"{base} current state overview {year}", f"{base} latest developments {year}"],
            ),
            ResearchSubtask(
                subtask_id="subtask-2",
                question=f"Who are the major companies/approaches and what are their technical specifications in {base}?",
                search_queries=[f"{base} major companies hardware technologies", f"{base} specifications comparison"],
            ),
            ResearchSubtask(
                subtask_id="subtask-3",
                question=f"What are the economics, pricing, commercial availability, and costs associated with {base}?",
                search_queries=[f"{base} pricing cost commercialization", f"{base} market availability {year}"],
            ),
            ResearchSubtask(
                subtask_id="subtask-4",
                question=f"What are the primary technical bottlenecks, safety considerations, and limitations of {base}?",
                search_queries=[f"{base} technical challenges limitations", f"{base} bottlenecks future outlook"],
            ),
        ]

        return ResearchPlan(
            topic=base,
            objectives=objectives,
            subtasks=subtasks,
            total_sources_consulted=0,
            gaps_identified=[],
        )

    def plan_gap_queries(self, missing_subtask: ResearchSubtask, topic: str) -> List[str]:
        """Generate targeted recovery queries when a specific subtask has insufficient evidence."""
        year = self._current_year
        q = missing_subtask.question
        return [
            f"{topic} {clean_subject(q)} official {year}",
            f"{topic} {clean_subject(q)} detailed analysis",
        ]
