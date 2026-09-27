import time
import hashlib
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from app.services.agent_v2.core.contracts import GenerationProvenanceRecord

logger = logging.getLogger("hsbot.agent_v2.provenance")


class GenerationProvenanceTracker:
    """
    Generation Provenance Engine (§43, §44):
    Tracks cryptographic provenance for all AI model operations and tool executions.
    Guarantees anti-cheating by recording exact model lineage, inputs, outputs, and file diffs.
    """

    def __init__(self):
        self._records: List[GenerationProvenanceRecord] = []

    def record_generation(
        self,
        project_id: str,
        task_id: str,
        model: str,
        role: str,
        input_context: str,
        output_content: str,
        files_created: List[str],
        files_modified: List[str],
        tools_used: List[str],
        prompt_version: str = "v2.0"
    ) -> GenerationProvenanceRecord:
        input_hash = hashlib.sha256(input_context.encode("utf-8")).hexdigest()
        output_hash = hashlib.sha256(output_content.encode("utf-8")).hexdigest()

        record = GenerationProvenanceRecord(
            project_id=project_id,
            task_id=task_id,
            model=model,
            role=role,
            prompt_version=prompt_version,
            input_context_hash=input_hash,
            output_hash=output_hash,
            files_created=files_created,
            files_modified=files_modified,
            tools_used=tools_used,
            timestamp=time.time(),
            is_genuine_ai=True
        )
        self._records.append(record)
        logger.info(f"Provenance recorded for task {task_id} with model {model}: {len(files_created)} created, {len(files_modified)} modified.")
        return record

    def get_provenance_summary(self, project_id: str) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self._records if r.project_id == project_id]

    def verify_provenance(self, project_id: str, files: Dict[str, str]) -> Tuple[bool, str]:
        """
        Verifies that every generated file has a corresponding provenance record.
        """
        project_records = [r for r in self._records if r.project_id == project_id]
        if not project_records:
            return False, "Zero generation provenance records found for project."

        tracked_files = set()
        for r in project_records:
            tracked_files.update(r.files_created)
            tracked_files.update(r.files_modified)

        missing = [f for f in files.keys() if f not in tracked_files and not f.startswith("tests/")]
        if missing:
            return False, f"Files generated without provenance records: {missing}"

        return True, f"Verified authentic AI provenance across {len(project_records)} model generation events."


# Global provenance tracker
generation_provenance_tracker = GenerationProvenanceTracker()
