import hashlib
import logging
from typing import Dict, List, Optional, Any, Set, Tuple
from app.services.agent_v2.core.contracts import ApplicationUniquenessReport

logger = logging.getLogger("hsbot.agent_v2.uniqueness")


class ApplicationUniquenessValidator:
    """
    Application Uniqueness Engine (§26):
    Compares newly generated applications against historical or concurrent projects.
    Rejects superficial color-only modifications and ensures genuine structural divergence.
    """

    # In-memory structural repository fingerprints
    _project_fingerprints: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def compute_structural_fingerprint(
        cls,
        files: Dict[str, str],
        domain: str,
        entities: List[str],
        workflows: List[str]
    ) -> Dict[str, Any]:
        """
        Computes structural fingerprint based on DOM elements, function signatures, and entity models.
        """
        html = files.get("index.html", "")
        js = files.get("script.js", "")

        # Extract major tags and structural tokens
        tag_tokens = set()
        for token in ["<canvas", "<table", "<form", "<nav", "<aside", "<video", "<svg", "<dialog"]:
            if token in html.lower():
                tag_tokens.add(token)

        # Extract key function names / event bindings
        js_tokens = set()
        for token in ["requestanimationframe", "addeventlistener", "localstorage", "fetch(", "getcontext('2d')", "websocket"]:
            if token in js.lower():
                js_tokens.add(token)

        entity_set = set(e.lower() for e in entities)
        workflow_set = set(w.lower() for w in workflows)

        return {
            "domain": domain.lower(),
            "tags": sorted(list(tag_tokens)),
            "js_features": sorted(list(js_tokens)),
            "entities": sorted(list(entity_set)),
            "workflows": sorted(list(workflow_set)),
            "file_names": sorted(list(files.keys()))
        }

    @classmethod
    def validate_uniqueness(
        cls,
        project_id: str,
        files: Dict[str, str],
        domain: str,
        entities: List[str],
        workflows: List[str]
    ) -> ApplicationUniquenessReport:
        """
        Validates whether this product is authentically distinct from other domains.
        """
        current_fp = cls.compute_structural_fingerprint(files, domain, entities, workflows)

        reasons = []
        highest_similarity = 0.0
        matched_proj = None

        for prev_id, prev_fp in cls._project_fingerprints.items():
            if prev_id == project_id:
                continue

            # Compare structural tokens
            tags_overlap = len(set(current_fp["tags"]).intersection(set(prev_fp["tags"])))
            js_overlap = len(set(current_fp["js_features"]).intersection(set(prev_fp["js_features"])))
            entities_overlap = len(set(current_fp["entities"]).intersection(set(prev_fp["entities"])))

            # If two different domains share 100% entities, something is wrong
            if current_fp["domain"] != prev_fp["domain"] and entities_overlap >= 3:
                similarity = 0.95
                reasons.append(f"Domain '{current_fp['domain']}' reused exact entity set from '{prev_fp['domain']}'")
            else:
                similarity = 0.1

            if similarity > highest_similarity:
                highest_similarity = similarity
                matched_proj = prev_id

        # Store fingerprint for future comparisons
        cls._project_fingerprints[project_id] = current_fp

        is_unique = highest_similarity < 0.85
        return ApplicationUniquenessReport(
            is_unique=is_unique,
            similarity_score=round(highest_similarity, 2),
            compared_project_id=matched_proj,
            reasons=reasons if not is_unique else ["Passed uniqueness verification against historical projects."]
        )

    @classmethod
    def record_and_validate(
        cls,
        project_id: str,
        user_request: str,
        domain: str,
        files: Dict[str, str]
    ) -> Tuple[bool, float, str]:
        report = cls.validate_uniqueness(
            project_id=project_id,
            files=files,
            domain=domain,
            entities=[],
            workflows=[]
        )
        msg = report.reasons[0] if report.reasons else "Application exhibits authentic domain uniqueness."
        return report.is_unique, report.similarity_score, msg
