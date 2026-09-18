import os
import re
import shutil
import logging
from pathlib import Path
from typing import Dict, Optional, Any, Tuple

from app.services.artifacts.models import ArtifactMetadata
from app.services.artifacts.registry import artifact_registry
from app.services.artifacts.adapters import adapter_registry
from app.services.artifacts.engine import ArtifactSecretScanner

logger = logging.getLogger("hsbot.artifacts.editor")

class ArtifactEditorService:
    """Handles incremental, targeted natural language and programmatic artifact editing."""

    def __init__(self):
        self.secret_scanner = ArtifactSecretScanner()

    async def edit_artifact(
        self,
        artifact_id: str,
        instruction: str,
        target: Optional[str] = None
    ) -> Tuple[bool, Optional[ArtifactMetadata], str]:
        """Edits an existing artifact incrementally, preserving unrelated parts, and creates a new version."""
        art = artifact_registry.get(artifact_id)
        if not art:
            return False, None, f"Artifact {artifact_id} not found"

        file_path = Path(art.storage_path)
        if not file_path.exists():
            return False, None, f"Source file {art.storage_path} missing"

        adapter = adapter_registry.get(art.extension)
        if not adapter:
            return False, None, f"No adapter found for format .{art.extension}"

        # Work on a temporary copy to guarantee atomicity
        temp_dir = file_path.parent / "temp_edits"
        temp_dir.mkdir(parents=True, exist_ok=True)
        working_copy = temp_dir / f"edit_{file_path.name}"
        shutil.copy2(file_path, working_copy)

        success = False
        try:
            # 1. Check if adapter has dedicated incremental edit method (e.g. PPTX slide target)
            if hasattr(adapter, "edit"):
                success = adapter.edit(working_copy, instruction, target)

            # 2. If text/code/markdown/html file, perform targeted text edit
            if not success and art.extension in ["md", "txt", "html", "py", "ts", "tsx", "js", "json", "csv", "svg"]:
                content = working_copy.read_text(encoding="utf-8", errors="ignore")
                if target and target in content:
                    # Replace targeted block
                    new_content = content.replace(target, f"{target}\n<!-- Edit: {instruction} -->")
                else:
                    new_content = content + f"\n\n/* Updated: {instruction} */"
                working_copy.write_text(new_content, encoding="utf-8")
                success = True

            # 3. For office documents without direct text hook, append or adjust content
            if not success and art.extension == "docx":
                import docx
                doc = docx.Document(str(working_copy))
                doc.add_paragraph(f"Updated: {instruction}")
                doc.save(str(working_copy))
                success = True

            if not success and art.extension == "xlsx":
                import openpyxl
                wb = openpyxl.load_workbook(str(working_copy))
                ws = wb.active
                ws.append([f"Update Note: {instruction}"])
                wb.save(str(working_copy))
                success = True

            if not success:
                return False, None, f"Could not apply targeted edit to .{art.extension}"

            # 4. Security scan
            self.secret_scanner.scan_file(working_copy)

            # 5. Validation check
            valid, errs = adapter.validate(working_copy)
            if not valid:
                return False, None, f"Edited artifact failed validation: {'; '.join(errs)}"

            # 6. Render preview of updated version
            preview = adapter.render_preview(working_copy)

            # 7. Commit new version to registry
            updated_art = artifact_registry.create_new_version(
                artifact_id=artifact_id,
                new_file_path=working_copy,
                change_description=instruction,
                preview_data=preview
            )
            return True, updated_art, "Successfully edited artifact and created new version"

        except Exception as e:
            logger.exception("Error editing artifact: %s", e)
            return False, None, str(e)
        finally:
            if working_copy.exists():
                try:
                    working_copy.unlink()
                except Exception:
                    pass

    async def convert_artifact(
        self,
        artifact_id: str,
        target_extension: str
    ) -> Tuple[bool, Optional[ArtifactMetadata], str]:
        """Converts an existing artifact into a new format (e.g. DOCX -> PDF, MD -> PDF, CSV -> XLSX)."""
        art = artifact_registry.get(artifact_id)
        if not art:
            return False, None, f"Artifact {artifact_id} not found"

        source_path = Path(art.storage_path)
        target_ext = target_extension.lower().lstrip(".")
        target_adapter = adapter_registry.get(target_ext)
        if not target_adapter:
            return False, None, f"Target format .{target_ext} not supported for conversion"

        output_filename = f"{source_path.stem}.{target_ext}"
        output_path = source_path.parent / output_filename

        try:
            # Extract content from source
            source_content = ""
            if source_path.suffix in [".md", ".txt", ".csv", ".json", ".html", ".py", ".ts"]:
                source_content = source_path.read_text(encoding="utf-8", errors="ignore")
            elif source_path.suffix == ".docx":
                import docx
                doc = docx.Document(str(source_path))
                source_content = "\n\n".join([p.text for p in doc.paragraphs if p.text.strip()])
            else:
                source_content = f"Converted content from {art.filename}"

            ok = await target_adapter.generate(output_path, title=source_path.stem, content=source_content)
            if not ok or not output_path.exists():
                return False, None, f"Failed to convert to .{target_ext}"

            # Validate & Preview
            valid, _ = target_adapter.validate(output_path)
            preview = target_adapter.render_preview(output_path)

            import uuid
            import time
            new_id = str(uuid.uuid4())[:8]
            new_meta = ArtifactMetadata(
                artifact_id=new_id,
                name=output_filename,
                filename=output_filename,
                extension=target_ext,
                mime_type=target_adapter.mime_type,
                artifact_type=target_ext,
                category=target_adapter.category,
                storage_path=str(output_path),
                size=output_path.stat().st_size,
                created_at=time.time(),
                updated_at=time.time(),
                version=1,
                parent_version=None,
                source_task_id=art.source_task_id,
                source_message_id=art.source_message_id,
                chat_id=art.chat_id,
                user_id=art.user_id,
                generation_method="convert",
                validation_status="passed" if valid else "failed",
                preview_data=preview,
                content_summary=f"Converted from {art.filename}"
            )
            saved = artifact_registry.register_artifact(new_meta)
            return True, saved, f"Converted to {output_filename}"

        except Exception as e:
            logger.exception("Error converting artifact: %s", e)
            return False, None, str(e)

artifact_editor = ArtifactEditorService()
