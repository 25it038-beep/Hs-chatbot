from pathlib import Path
from typing import Dict, Any, Optional

from app.services.artifacts.models import ArtifactMetadata
from app.services.artifacts.registry import artifact_registry
from app.services.artifacts.adapters import adapter_registry

class ArtifactPreviewService:
    def get_preview(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        art = artifact_registry.get(artifact_id)
        if not art:
            return None

        file_path = Path(art.storage_path)
        if not file_path.exists():
            return {
                "artifact_id": art.artifact_id,
                "filename": art.filename,
                "error": "Artifact storage file missing on disk"
            }

        adapter = adapter_registry.get(art.extension)
        preview_data = {}
        if adapter:
            try:
                preview_data = adapter.render_preview(file_path)
            except Exception as e:
                preview_data = {"error": f"Preview rendering failed: {e}"}

        return {
            "artifact_id": art.artifact_id,
            "filename": art.filename,
            "extension": art.extension,
            "mime_type": art.mime_type,
            "size": art.size,
            "version": art.version,
            "total_versions": len(art.versions),
            "preview": preview_data,
            "download_url": f"/api/agent/artifacts/{art.artifact_id}/download"
        }

    def get_content(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        art = artifact_registry.get(artifact_id)
        if not art:
            return None

        file_path = Path(art.storage_path)
        if not file_path.exists():
            return None

        # If textual format
        if art.extension in ["txt", "md", "csv", "json", "py", "ts", "tsx", "js", "html", "svg", "sql"]:
            try:
                text = file_path.read_text(encoding="utf-8", errors="ignore")
                return {
                    "artifact_id": art.artifact_id,
                    "filename": art.filename,
                    "type": "text",
                    "content": text
                }
            except Exception as e:
                return {"error": str(e)}

        return {
            "artifact_id": art.artifact_id,
            "filename": art.filename,
            "type": "binary",
            "message": "Binary artifact cannot be displayed as raw text. Use preview or download."
        }

artifact_preview = ArtifactPreviewService()
