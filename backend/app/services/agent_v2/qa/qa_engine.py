import re
import logging
from typing import Dict, List, Optional, Any, Tuple
from app.services.agent.qa_engine import (
    VisualQAInspector,
    UserFlowVerifier,
    VisualQAReport,
    UserFlowVerificationReport
)

logger = logging.getLogger("hsbot.agent_v2.qa")

class NoveltyTestEngine:
    """
    Novelty Test (§47): Evaluates whether the generated product authentically matches
    the user's idea rather than blindly reusing a generic admin dashboard layout.
    """

    @classmethod
    def evaluate_novelty(
        cls,
        domain: str,
        files: Dict[str, str],
        user_request: str
    ) -> Tuple[bool, str]:
        html = files.get("index.html", "")
        script = files.get("script.js", "")
        combined = (html + " " + script).lower()

        # If it's a game, it MUST contain canvas / arena / game loop elements, NOT a table with "Users"
        if "game" in domain or "football" in user_request.lower():
            if "<canvas" not in html and "requestanimationframe" not in script:
                return False, "Failed Novelty Test: Game product lacks canvas/game loop and appears to be a generic UI."
            if "total users" in combined and "total revenue" in combined:
                return False, "Failed Novelty Test: Inappropriate SaaS dashboard metrics found in a game."

        # If it's healthcare, it must contain triage/vitals/admissions
        if "healthcare" in domain or "hospital" in user_request.lower():
            if not any(w in combined for w in ["triage", "patient", "vitals", "bed"]):
                return False, "Failed Novelty Test: Healthcare product lacks clinical triage and patient entities."

        return True, "Passed Novelty Test: Application structure authentically designed for product domain."


class AgentCritic:
    """
    Evaluates product completeness before final verification (§44).
    Asks: Does this represent the user's idea? Are any features fake?
    """

    @classmethod
    def critique(
        cls,
        user_request: str,
        files: Dict[str, str],
        domain: str
    ) -> Dict[str, Any]:
        html = files.get("index.html", "")
        script = files.get("script.js", "")

        has_interactive_handlers = "addeventlistener" in script.lower() or "onclick" in html.lower()
        has_buttons = "<button" in html.lower()
        has_responsive_meta = "viewport" in html.lower()

        is_complete = has_interactive_handlers and has_buttons and has_responsive_meta
        issues = []
        if not has_interactive_handlers:
            issues.append("Missing interactive JavaScript state event listeners.")
        if not has_buttons:
            issues.append("Missing interactive button triggers.")
        if not has_responsive_meta:
            issues.append("Missing responsive viewport meta tag.")

        return {
            "critique_passed": is_complete,
            "issues": issues,
            "recommendation": "Ready for independent verification" if is_complete else "Apply repair tasks"
        }
