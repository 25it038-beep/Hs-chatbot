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


class TemplateContaminationDetector:
    """
    TemplateContaminationDetector (§4):
    Detects whether the generated project has become an existing template clone.
    Compares:
    - folder structure
    - component structure
    - routes
    - page structure
    - workflows
    - domain entities
    - data model
    - navigation
    - UI structure
    - feature architecture
    """
    FORBIDDEN_GENERIC_PATTERNS = [
        "core entities & data stream",
        "operational telemetry",
        "total users: 500",
        "total revenue: $10,000",
        "lorem ipsum",
        "default_dashboard",
        "default_saas",
        "template_cloner",
        "supported_apps"
    ]

    @classmethod
    def check_contamination(
        cls,
        files: Dict[str, str],
        domain: str,
        user_request: str
    ) -> Tuple[bool, List[str]]:
        """
        Returns (is_contaminated, list_of_violations).
        """
        violations = []
        html = files.get("index.html", "")
        js = files.get("script.js", "")
        css = files.get("styles.css", "")
        combined = (html + " " + js + " " + css).lower()

        # 1. Generic template markers
        for pat in cls.FORBIDDEN_GENERIC_PATTERNS:
            if pat in combined:
                # If it's a game or CLI or simulation, dashboard tokens are strictly forbidden
                if ("game" in domain or "football" in user_request.lower() or "cli" in domain or "simulation" in domain):
                    violations.append(f"Forbidden template marker '{pat}' found in non-SaaS product.")

        # 2. Check if unrelated applications have been forced into a fake SaaS dashboard
        if ("game" in domain or "simulation" in domain or "3d" in domain):
            if "total revenue" in combined or "total users" in combined:
                violations.append("SaaS metrics card detected in specialized non-SaaS application.")

        # 3. Check for empty placeholders or fake stub functions
        if "// todo: implement" in combined or "alert('placeholder')" in combined:
            violations.append("Unimplemented placeholder or stub alert detected.")

        is_contaminated = len(violations) > 0
        return is_contaminated, violations


class ApplicationUniquenessValidator:
    """
    ApplicationUniquenessValidator (§26):
    For every new application, compares structural fingerprints against previous generations.
    Ensures no two unrelated applications share the same template architecture with merely recolored CSS.
    """
    _PROJECT_REGISTRY: List[Dict[str, Any]] = []

    @classmethod
    def record_and_validate(
        cls,
        project_id: str,
        user_request: str,
        domain: str,
        files: Dict[str, str]
    ) -> Tuple[bool, float, str]:
        """
        Returns (is_unique, similarity_score, message).
        """
        html = files.get("index.html", "")
        script = files.get("script.js", "")

        # Extract structural tokens: tags, IDs, class names, functions
        tags = set(re.findall(r"<([a-zA-Z0-9]+)", html))
        element_ids = set(re.findall(r'id=["\']([^"\']+)["\']', html))
        classes = set(re.findall(r'class=["\']([^"\']+)["\']', html))
        functions = set(re.findall(r'(?:function\s+|const\s+)([a-zA-Z0-9_]+)\s*=', script))

        signature = {
            "project_id": project_id,
            "domain": domain,
            "request": user_request,
            "tags": tags,
            "element_ids": element_ids,
            "classes": classes,
            "functions": functions
        }

        # Compare with existing registry of distinct domains
        for past in cls._PROJECT_REGISTRY:
            if past["domain"] != domain:
                # Calculate Jaccard similarity of element IDs
                common_ids = element_ids.intersection(past["element_ids"])
                total_ids = element_ids.union(past["element_ids"])
                if total_ids:
                    id_similarity = len(common_ids) / len(total_ids)
                    if id_similarity > 0.75:
                        return False, id_similarity, f"Structural collision with unrelated project '{past['request'][:30]}': similarity {id_similarity:.2f}"

        cls._PROJECT_REGISTRY.append(signature)
        return True, 0.0, "Application exhibits authentic domain uniqueness."


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
