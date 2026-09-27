import re
import logging
from typing import Dict, List, Optional, Any, Set, Tuple
from app.services.agent_v2.core.contracts import (
    TemplateContaminationReport,
    ProductSpecification,
    ModelHandoffContract
)

logger = logging.getLogger("hsbot.agent_v2.anti_template")


class TemplateContaminationDetector:
    """
    Anti-Template Detection Engine (§4):
    Before and after generation, detects whether the project has become an existing template clone.
    Fails generation if unrelated applications produce essentially identical architecture/workflows.
    """

    # Forbidden canned boilerplate patterns
    FORBIDDEN_COUNTER_PATTERNS = [
        r"count\s*\+\+",
        r"decBtn",
        r"incBtn",
        r"counterDisplay",
        r"decrementBtn",
        r"incrementBtn",
        r"click to (?:increment|decrement)",
        r"Simple Counter Demo"
    ]

    FORBIDDEN_GENERIC_DASHBOARD_PATTERNS = [
        r"Total Users\s*[\$0-9,]+",
        r"Monthly Recurring Revenue",
        r"Churn Rate",
        r"Active Subscriptions\s*[\$0-9,]+"
    ]

    @classmethod
    def detect_pre_generation(cls, contract: ModelHandoffContract) -> TemplateContaminationReport:
        """
        Inspects the architecture and requirements before code generation to verify
        the system is not defaulting to a canned archetype.
        """
        spec = contract.product_specification or {}
        p_name = spec.get("product_name", "").lower()
        domain = spec.get("domain", "").lower()
        entities = spec.get("entities", [])
        workflows = spec.get("core_workflow", [])

        matched = []
        # If user asks for game, check that entities/workflows aren't generic SaaS
        if "game" in domain or "football" in p_name:
            for wf in workflows:
                if any(kw in wf.lower() for kw in ["mrr", "subscription", "checkout cart", "invoice"]):
                    matched.append(f"Inappropriate SaaS workflow in game: {wf}")

        is_contaminated = len(matched) > 0
        return TemplateContaminationReport(
            is_contaminated=is_contaminated,
            confidence_score=0.95 if is_contaminated else 0.05,
            matched_patterns=matched,
            details="Pre-generation clean" if not is_contaminated else f"Contamination detected in plan: {matched}"
        )

    @classmethod
    def detect_post_generation(
        cls,
        files: Dict[str, str],
        spec_dict: Dict[str, Any]
    ) -> TemplateContaminationReport:
        """
        Inspects generated source files (HTML, CSS, JS) to ensure zero template contamination.
        """
        p_name = spec_dict.get("product_name", "").lower()
        domain = str(spec_dict.get("domain", "web_app")).lower()
        entities = [str(e).lower() for e in spec_dict.get("entities", [])]
        features = [str(f).lower() for f in spec_dict.get("features", [])]

        matched_patterns = []
        combined_text = "\n".join(files.values())

        # 1. Check for forbidden counter button patterns
        # Only allowed if the user explicitly asked for a counter app
        if "counter" not in p_name and "counter" not in domain:
            for pat in cls.FORBIDDEN_COUNTER_PATTERNS:
                if re.search(pat, combined_text, re.IGNORECASE):
                    matched_patterns.append(f"Forbidden counter pattern: {pat}")

        # 2. Check for canned SaaS metric mockups in non-SaaS products (games, tools, simulators)
        is_game_or_tool = any(k in domain or k in p_name for k in ["game", "football", "simulator", "tool", "cli", "player"])
        if is_game_or_tool:
            for pat in cls.FORBIDDEN_GENERIC_DASHBOARD_PATTERNS:
                if re.search(pat, combined_text, re.IGNORECASE):
                    matched_patterns.append(f"Forbidden canned dashboard pattern in {domain}: {pat}")

        # 3. Check domain authenticity: Game must have canvas/arena, not generic table
        if "game" in domain or "football" in p_name:
            has_canvas = "<canvas" in combined_text.lower()
            has_gameloop = "requestanimationframe" in combined_text.lower() or "gameloop" in combined_text.lower()
            if not has_canvas and not has_gameloop:
                matched_patterns.append("Game product lacks canvas arena or interactive game loop.")

        # 4. Check entity representation: At least one domain entity must be actively referenced in code
        if entities and len(entities) > 0:
            found_entities = [e for e in entities if e in combined_text.lower()]
            if not found_entities and len(entities) >= 2:
                matched_patterns.append(f"None of the required entities {entities} appear in the generated code.")

        is_contaminated = len(matched_patterns) > 0
        confidence = min(1.0, 0.4 + (len(matched_patterns) * 0.3)) if is_contaminated else 0.05

        return TemplateContaminationReport(
            is_contaminated=is_contaminated,
            confidence_score=round(confidence, 2),
            matched_patterns=matched_patterns,
            details="Code is authentic to domain specifications" if not is_contaminated else f"Contamination detected: {', '.join(matched_patterns)}"
        )
