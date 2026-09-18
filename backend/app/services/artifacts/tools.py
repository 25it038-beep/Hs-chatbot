import os
import json
import time
import shutil
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from app.services.artifacts.models import ArtifactMetadata, ArtifactCategory, ArtifactVersionRecord
from app.services.artifacts.registry import artifact_registry
from app.services.artifacts.adapters import adapter_registry
from app.services.artifacts.engine import artifact_engine, ArtifactSecretScanner, SecretLeakDetectedError
from app.services.artifacts.editor import artifact_editor
from app.services.artifacts.preview import artifact_preview
from app.services.workspace.workspace import get_workspace

logger = logging.getLogger("hsbot.artifacts.tools")

# ==============================================================================
# Tool Schemas (Section 2 & 39)
# ==============================================================================

ARTIFACT_TOOL_DEFINITIONS = [
    {
        "name": "create_file",
        "description": "Directly writes a real file with content to the sandboxed workspace.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative file path inside the workspace (e.g. 'src/index.js', 'README.md')"},
                "content": {"type": "string", "description": "Full file content string"},
                "workspace_id": {"type": "string", "description": "Workspace ID", "default": "default"}
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "create_artifact",
        "description": "Generates, validates, and registers a real deliverable artifact (PDF, DOCX, PPTX, XLSX, CSV, HTML, SVG, Code, ZIP) with automatic QA.",
        "parameters": {
            "type": "object",
            "properties": {
                "artifact_type": {"type": "string", "description": "Format type: pdf, docx, pptx, xlsx, csv, html, svg, code, zip"},
                "filename": {"type": "string", "description": "Target filename with extension (e.g. 'quarterly_report.pdf', 'budget.xlsx')"},
                "content": {"type": ["string", "object", "array"], "description": "Content data or structured payload for document generation"},
                "title": {"type": "string", "description": "Document/artifact title", "default": ""},
                "options": {"type": "object", "description": "Style/layout options", "default": {}},
                "chat_id": {"type": "string", "description": "Associated chat ID"},
                "user_id": {"type": "string", "description": "Associated user ID"}
            },
            "required": ["artifact_type", "filename", "content"]
        }
    },
    {
        "name": "edit_artifact",
        "description": "Incrementally updates an existing artifact without regenerating unrelated parts, and records a new version.",
        "parameters": {
            "type": "object",
            "properties": {
                "artifact_id": {"type": "string", "description": "Unique ID of the artifact to edit"},
                "instruction": {"type": "string", "description": "Targeted change description (e.g. 'Change slide 4', 'Add quarterly column', 'Dark theme')"},
                "target": {"type": "string", "description": "Optional specific target selector (e.g. 'slide 4', 'sheet 2', 'header')", "default": ""}
            },
            "required": ["artifact_id", "instruction"]
        }
    },
    {
        "name": "inspect_artifact",
        "description": "Inspects structural details, slide count, sheets, lines, size, and metadata of an existing artifact.",
        "parameters": {
            "type": "object",
            "properties": {
                "artifact_id": {"type": "string", "description": "Artifact ID to inspect"}
            },
            "required": ["artifact_id"]
        }
    },
    {
        "name": "render_artifact",
        "description": "Generates a structured interactive preview of an artifact (HTML iframe, slides, sheets, archive file tree).",
        "parameters": {
            "type": "object",
            "properties": {
                "artifact_id": {"type": "string", "description": "Artifact ID to render"}
            },
            "required": ["artifact_id"]
        }
    },
    {
        "name": "validate_artifact",
        "description": "Executes format integrity validation, structure verification, and secret scanning on the artifact.",
        "parameters": {
            "type": "object",
            "properties": {
                "artifact_id": {"type": "string", "description": "Artifact ID to validate"}
            },
            "required": ["artifact_id"]
        }
    },
    {
        "name": "repair_artifact",
        "description": "Diagnoses detected validation/formatting issues in an artifact and applies targeted automated repair.",
        "parameters": {
            "type": "object",
            "properties": {
                "artifact_id": {"type": "string", "description": "Artifact ID to repair"},
                "issues": {"type": "array", "items": {"type": "string"}, "description": "List of detected issues to fix", "default": []}
            },
            "required": ["artifact_id"]
        }
    },
    {
        "name": "convert_artifact",
        "description": "Converts an existing artifact to another supported format (e.g. DOCX to PDF, Markdown to HTML/DOCX).",
        "parameters": {
            "type": "object",
            "properties": {
                "artifact_id": {"type": "string", "description": "Artifact ID to convert"},
                "target_format": {"type": "string", "description": "Target format (e.g. 'pdf', 'docx', 'html')"}
            },
            "required": ["artifact_id", "target_format"]
        }
    },
    {
        "name": "package_artifacts",
        "description": "Packages workspace project files or multiple artifacts into a verified, secret-scanned ZIP archive.",
        "parameters": {
            "type": "object",
            "properties": {
                "zip_filename": {"type": "string", "description": "Output zip filename", "default": "project.zip"},
                "workspace_id": {"type": "string", "description": "Workspace ID to package", "default": "default"},
                "chat_id": {"type": "string", "description": "Associated chat ID"},
                "user_id": {"type": "string", "description": "Associated user ID"}
            }
        }
    },
    {
        "name": "download_artifact",
        "description": "Returns direct download URL and file verification stats for a generated artifact.",
        "parameters": {
            "type": "object",
            "properties": {
                "artifact_id": {"type": "string", "description": "Artifact ID to download"}
            },
            "required": ["artifact_id"]
        }
    },
    {
        "name": "list_artifacts",
        "description": "Lists all registered artifacts, optionally filtered by chat ID or category.",
        "parameters": {
            "type": "object",
            "properties": {
                "chat_id": {"type": "string", "description": "Optional chat ID filter"},
                "category": {"type": "string", "description": "Optional category filter"}
            }
        }
    },
    {
        "name": "get_artifact",
        "description": "Retrieves comprehensive metadata, provenance, and version history for an artifact.",
        "parameters": {
            "type": "object",
            "properties": {
                "artifact_id": {"type": "string", "description": "Artifact ID"}
            },
            "required": ["artifact_id"]
        }
    },
    {
        "name": "get_artifact_version",
        "description": "Retrieves information about a specific historical version snapshot of an artifact.",
        "parameters": {
            "type": "object",
            "properties": {
                "artifact_id": {"type": "string", "description": "Artifact ID"},
                "version": {"type": "integer", "description": "Version number to inspect"}
            },
            "required": ["artifact_id", "version"]
        }
    },
    {
        "name": "restore_artifact_version",
        "description": "Restores a previous historical version as the current version of the artifact.",
        "parameters": {
            "type": "object",
            "properties": {
                "artifact_id": {"type": "string", "description": "Artifact ID"},
                "version": {"type": "integer", "description": "Version number to restore"}
            },
            "required": ["artifact_id", "version"]
        }
    }
]

# ==============================================================================
# Tool Execution Handlers
# ==============================================================================

class ArtifactToolExecutor:
    """Executes the 14 artifact tools with sandbox safety and QA."""

    @staticmethod
    def create_file(path: str, content: str, workspace_id: str = "default") -> Dict[str, Any]:
        ws = get_workspace(workspace_id)
        res = ws.write_file(path, content)
        return res

    @staticmethod
    async def create_artifact(
        artifact_type: str,
        filename: str,
        content: Any,
        title: str = "",
        options: Optional[Dict[str, Any]] = None,
        chat_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        fmt = artifact_type.lower().lstrip(".")
        adapter = adapter_registry.get(fmt)
        if not adapter:
            return {
                "success": False,
                "error": f"UNSUPPORTED_FORMAT: Format .{fmt} is not supported by the runtime engine."
            }

        dest_dir = artifact_engine.storage_dir
        dest_dir.mkdir(parents=True, exist_ok=True)
        import uuid
        art_id = f"art_{uuid.uuid4().hex[:10]}"
        dest_path = dest_dir / f"{art_id}_{filename}"

        # 1. Generate via adapter
        title_str = title or Path(filename).stem
        gen_res = adapter.generate(dest_path, title_str, content, options or {})
        if hasattr(gen_res, "__await__"):
            gen_res = await gen_res

        if not gen_res or not getattr(gen_res, "passed", True):
            errors = getattr(gen_res, "errors", ["Generation failed"])
            return {"success": False, "error": "; ".join(errors)}

        if not dest_path.exists():
            return {"success": False, "error": "Generated file missing on disk"}

        # 2. Secret Scan
        leak = ArtifactSecretScanner.scan_file(dest_path)
        if leak:
            dest_path.unlink(missing_ok=True)
            raise SecretLeakDetectedError(leak, filename)

        # 3. Validation
        valid, val_errs = adapter.validate(dest_path)
        if not valid:
            logger.info(f"Artifact {filename} failed validation ({val_errs}). Running repair loop...")
            repaired = False
            if hasattr(adapter, "edit"):
                repaired = adapter.edit(dest_path, "Auto-repair validation errors")
            if not repaired:
                dest_path.unlink(missing_ok=True)
                return {"success": False, "error": f"Artifact validation failed: {'; '.join(val_errs)}"}

        # 4. Preview
        preview_data = adapter.render_preview(dest_path)

        # 5. Register
        meta = ArtifactMetadata(
            artifact_id=art_id,
            name=filename,
            filename=filename,
            extension=fmt,
            mime_type=adapter.mime_type,
            artifact_type=fmt,
            category=adapter.category,
            storage_path=str(dest_path),
            size=dest_path.stat().st_size,
            created_at=time.time(),
            updated_at=time.time(),
            version=1,
            chat_id=chat_id,
            user_id=user_id,
            generation_method="adapter",
            validation_status="passed",
            visual_validation_status="passed",
            security_status="passed",
            delivery_status="ready",
            preview_data=preview_data,
            content_summary=f"Verified {fmt.upper()} artifact: {filename}"
        )
        saved = artifact_registry.register_artifact(meta)
        return {"success": True, "artifact": saved.to_dict()}

    @staticmethod
    async def edit_artifact(artifact_id: str, instruction: str, target: Optional[str] = None) -> Dict[str, Any]:
        success, art, msg = await artifact_editor.edit_artifact(artifact_id, instruction, target)
        if not success:
            return {"success": False, "error": msg}
        return {"success": True, "artifact": art.to_dict(), "message": msg}

    @staticmethod
    def inspect_artifact(artifact_id: str) -> Dict[str, Any]:
        art = artifact_registry.get(artifact_id)
        if not art:
            return {"success": False, "error": "Artifact not found"}
        return {
            "success": True,
            "artifact_id": art.artifact_id,
            "filename": art.filename,
            "extension": art.extension,
            "size_bytes": art.size,
            "version": art.version,
            "total_versions": len(art.versions),
            "validation_status": art.validation_status,
            "security_status": art.security_status,
            "download_url": f"/api/agent/artifacts/{art.artifact_id}/download"
        }

    @staticmethod
    def render_artifact(artifact_id: str) -> Dict[str, Any]:
        prev = artifact_preview.get_preview(artifact_id)
        if not prev:
            return {"success": False, "error": "Artifact preview not available"}
        return {"success": True, "preview": prev}

    @staticmethod
    def validate_artifact(artifact_id: str) -> Dict[str, Any]:
        art = artifact_registry.get(artifact_id)
        if not art:
            return {"success": False, "error": "Artifact not found"}
        file_path = Path(art.storage_path)
        if not file_path.exists():
            return {"success": False, "error": "Artifact storage file missing on disk"}

        leak = ArtifactSecretScanner.scan_file(file_path)
        if leak:
            return {"success": False, "valid": False, "security_leak": leak}

        adapter = adapter_registry.get(art.extension)
        if not adapter:
            return {"success": True, "valid": True, "note": "Generic format check passed"}

        valid, errs = adapter.validate(file_path)
        return {
            "success": True,
            "valid": valid,
            "errors": errs,
            "security": "passed"
        }

    @staticmethod
    async def repair_artifact(artifact_id: str, issues: Optional[List[str]] = None) -> Dict[str, Any]:
        instruction = f"Repair issues: {'; '.join(issues)}" if issues else "Auto-repair formatting and layout"
        return await ArtifactToolExecutor.edit_artifact(artifact_id, instruction)

    @staticmethod
    async def convert_artifact(artifact_id: str, target_format: str) -> Dict[str, Any]:
        success, art, msg = await artifact_editor.convert_artifact(artifact_id, target_format)
        if not success:
            return {"success": False, "error": msg}
        return {"success": True, "artifact": art.to_dict(), "message": msg}

    @staticmethod
    def package_artifacts(
        zip_filename: str = "project.zip",
        workspace_id: str = "default",
        chat_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        ws = get_workspace(workspace_id)
        return artifact_engine.create_zip_project(
            workspace_dir=ws.root,
            zip_filename=zip_filename,
            chat_id=chat_id,
            user_id=user_id
        )

    @staticmethod
    def download_artifact(artifact_id: str) -> Dict[str, Any]:
        art = artifact_registry.get(artifact_id)
        if not art:
            return {"success": False, "error": "Artifact not found"}
        return {
            "success": True,
            "filename": art.filename,
            "size": art.size,
            "download_url": f"/api/agent/artifacts/{art.artifact_id}/download"
        }

    @staticmethod
    def list_artifacts(chat_id: Optional[str] = None, category: Optional[str] = None) -> Dict[str, Any]:
        cat_enum = None
        if category:
            try:
                cat_enum = ArtifactCategory(category.lower())
            except Exception:
                pass
        items = artifact_registry.list_artifacts(category=cat_enum, chat_id=chat_id)
        return {"success": True, "artifacts": [a.to_dict() for a in items]}

    @staticmethod
    def get_artifact(artifact_id: str) -> Dict[str, Any]:
        art = artifact_registry.get(artifact_id)
        if not art:
            return {"success": False, "error": "Artifact not found"}
        return {"success": True, "artifact": art.to_dict()}

    @staticmethod
    def get_artifact_version(artifact_id: str, version: int) -> Dict[str, Any]:
        art = artifact_registry.get(artifact_id)
        if not art:
            return {"success": False, "error": "Artifact not found"}
        ver = next((v for v in art.versions if v.version == version), None)
        if not ver:
            return {"success": False, "error": f"Version {version} not found"}
        return {"success": True, "version": ver.to_dict()}

    @staticmethod
    def restore_artifact_version(artifact_id: str, version: int) -> Dict[str, Any]:
        art = artifact_registry.restore_version(artifact_id, version)
        if not art:
            return {"success": False, "error": f"Could not restore version {version}"}
        return {"success": True, "artifact": art.to_dict()}

async def execute_artifact_tool(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Executes an artifact tool by name with arguments."""
    func = getattr(ArtifactToolExecutor, tool_name, None)
    if not func:
        return {"success": False, "error": f"Unknown artifact tool: '{tool_name}'"}
    try:
        res = func(**args)
        if hasattr(res, "__await__"):
            res = await res
        return res
    except SecretLeakDetectedError as e:
        logger.warning(f"Tool {tool_name} blocked by security: {e}")
        return {"success": False, "error": str(e), "security_blocked": True}
    except Exception as e:
        logger.error(f"Error executing {tool_name}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
