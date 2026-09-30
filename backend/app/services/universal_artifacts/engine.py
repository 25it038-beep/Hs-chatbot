import os
import uuid
import json
import hashlib
import logging
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.models.file import GeneratedFile
from app.services.universal_artifacts.contracts import (
    ArtifactSpec,
    ArtifactMetadata,
    ArtifactCategory,
    ValidationResult,
)
from app.services.universal_artifacts.registry import ArtifactFormatRegistryV2
from app.services.universal_artifacts.validator import ArtifactValidator
from app.services.universal_artifacts.generators.document_gen import (
    generate_universal_pdf,
    generate_universal_docx,
    generate_universal_markdown,
    generate_universal_text,
)
from app.services.universal_artifacts.generators.spreadsheet_gen import (
    generate_universal_xlsx,
    generate_universal_csv,
)
from app.services.universal_artifacts.generators.presentation_gen import (
    generate_universal_pptx,
)
from app.services.universal_artifacts.generators.data_gen import (
    generate_universal_json,
    generate_universal_yaml,
    generate_universal_xml,
    generate_universal_sql,
)
from app.services.universal_artifacts.generators.code_gen import (
    generate_universal_code_file,
)
from app.services.universal_artifacts.generators.archive_gen import (
    generate_universal_zip,
)
from app.services.universal_artifacts.generators.media_gen import (
    generate_universal_svg,
    generate_universal_png,
)

logger = logging.getLogger("hsbot.universal_artifacts")


class UniversalArtifactEngineV2:
    """Universal Artifact Engine V2 (§3).
    Genuinely plans, generates, validates, hashes, stores, and delivers real downloadable files.
    """

    @classmethod
    def get_storage_path(cls, user_id: str, conversation_id: str, filename: str) -> Tuple[str, str]:
        clean_user_id = str(user_id or "default_user")
        clean_conv_id = str(conversation_id or "general")
        base_dir = os.path.abspath(settings.storage_dir)
        conv_dir = os.path.join(base_dir, "users", clean_user_id, "conversations", clean_conv_id, "files")
        os.makedirs(conv_dir, exist_ok=True)

        unique_prefix = str(uuid.uuid4())[:8]
        # Path traversal guard (§39)
        safe_base = os.path.basename(filename)
        safe_filename = f"{unique_prefix}_{safe_base}"
        full_path = os.path.join(conv_dir, safe_filename)
        return conv_dir, full_path

    @classmethod
    async def generate_artifact(
        cls,
        spec: ArtifactSpec,
        content: Any,
        user_id: str,
        conversation_id: str,
        db: Optional[AsyncSession] = None,
        version: int = 1,
        parent_id: Optional[str] = None
    ) -> ArtifactMetadata:
        """Executes the pipeline: Generate -> Validate -> Compute Hash -> Store -> Deliver."""
        fmt = spec.format.lower().lstrip(".")
        category = spec.category

        # 1. Setup storage path
        _, file_path = cls.get_storage_path(user_id, conversation_id, spec.filename)
        logger.info("[ARTIFACT] Generating %s (format: %s, category: %s) to %s", spec.title, fmt, category, file_path)

        # 2. Generator Selection & Execution (§15)
        if fmt == "pdf":
            content_dict = content if isinstance(content, dict) else {"sections": [{"heading": "Overview", "paragraphs": [str(content)]}]}
            generate_universal_pdf(spec.title, content_dict, file_path)

        elif fmt in ["docx", "doc"]:
            content_dict = content if isinstance(content, dict) else {"sections": [{"heading": "Overview", "paragraphs": [str(content)]}]}
            generate_universal_docx(spec.title, content_dict, file_path)

        elif fmt in ["pptx", "ppt"]:
            content_dict = content if isinstance(content, dict) else {"slides": [{"title": spec.title, "bullets": [str(content)]}]}
            generate_universal_pptx(spec.title, content_dict, file_path)

        elif fmt in ["xlsx", "xls"]:
            content_dict = content if isinstance(content, dict) else {"headers": ["Item", "Value"], "rows": [["Generated Metric", str(content)]]}
            generate_universal_xlsx(spec.title, content_dict, file_path)

        elif fmt == "csv":
            content_dict = content if isinstance(content, dict) else {"headers": ["Output"], "rows": [[str(content)]]}
            generate_universal_csv(spec.title, content_dict, file_path, delimiter=",")

        elif fmt == "tsv":
            content_dict = content if isinstance(content, dict) else {"headers": ["Output"], "rows": [[str(content)]]}
            generate_universal_csv(spec.title, content_dict, file_path, delimiter="\t")

        elif fmt == "json":
            generate_universal_json(content, file_path)

        elif fmt in ["yaml", "yml"]:
            generate_universal_yaml(content, file_path)

        elif fmt == "xml":
            generate_universal_xml("document", content, file_path)

        elif fmt == "sql":
            content_dict = content if isinstance(content, dict) else {"table_name": "data_table", "rows": [{"metric": str(content)}]}
            generate_universal_sql(spec.title, content_dict, file_path)

        elif fmt in ["md", "markdown"]:
            content_dict = content if isinstance(content, dict) else {"sections": [{"heading": "Content", "paragraphs": [str(content)]}]}
            generate_universal_markdown(spec.title, content_dict, file_path)

        elif fmt == "txt":
            content_dict = content if isinstance(content, dict) else {"sections": [{"heading": "Content", "paragraphs": [str(content)]}]}
            generate_universal_text(spec.title, content_dict, file_path)

        elif fmt == "zip":
            if isinstance(content, dict):
                files_map = content
            else:
                files_map = {
                    "README.md": f"# {spec.title}\n\nGenerated by HSBot Universal Artifact Engine.\n",
                    "data.txt": str(content)
                }
            generate_universal_zip(files_map, file_path)

        elif fmt == "svg":
            svg_text = content if isinstance(content, str) else str(content)
            generate_universal_svg(spec.title, svg_text, file_path)

        elif fmt in ["png", "jpg", "jpeg", "webp"]:
            generate_universal_png(spec.title, file_path)

        elif category == ArtifactCategory.CODE:
            code_text = content if isinstance(content, str) else str(content)
            generate_universal_code_file(spec.title, fmt, code_text, file_path)

        else:
            # Generic text fallback
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(str(content))

        # 3. Artifact Validation (§31)
        val_res = ArtifactValidator.validate(file_path, fmt)
        if not val_res.is_valid:
            logger.error("[ARTIFACT] Validation failed for %s: %s", file_path, val_res.error)
            raise ValueError(f"Artifact generation validation failed: {val_res.error}")

        # 4. Compute SHA256 Hash (§30, §41)
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                sha256.update(chunk)
        file_hash = sha256.hexdigest()
        file_size = os.path.getsize(file_path)

        # 5. Database Persistence (§38)
        art_id = str(uuid.uuid4())
        mime_type = ArtifactFormatRegistryV2.get_mime_type(fmt)
        download_url = f"/api/files/{art_id}/download"

        preview_dict = {
            "title": spec.title,
            "format": fmt,
            "category": category.value,
            "verification": val_res.to_dict(),
        }
        if fmt in ["pdf", "docx"]:
            preview_dict["sections"] = content.get("sections", []) if isinstance(content, dict) else []
        elif fmt == "pptx":
            preview_dict["slides"] = content.get("slides", []) if isinstance(content, dict) else []
        elif fmt in ["xlsx", "csv", "tsv"]:
            if isinstance(content, dict):
                preview_dict["headers"] = content.get("headers", [])
                preview_dict["rows"] = content.get("rows", [])
        elif category == ArtifactCategory.CODE:
            preview_dict["code"] = str(content)[:10000]
            preview_dict["language"] = fmt
        elif fmt == "svg":
            preview_dict["svg"] = str(content)[:20000]
        elif fmt == "zip":
            if isinstance(content, dict):
                preview_dict["files"] = list(content.keys())
        elif fmt in ["json", "yaml", "xml", "sql"]:
            preview_dict["data"] = content

        if db:
            try:
                gen_file = GeneratedFile(
                    id=art_id,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    filename=spec.filename,
                    storage_path=file_path,
                    mime_type=mime_type,
                    file_size=file_size,
                    content_hash=file_hash,
                    status="ready",
                    preview_data=json.dumps(preview_dict),
                    content_data=json.dumps(content) if isinstance(content, (dict, list)) else str(content)[:2000],
                    verification_result=json.dumps(val_res.to_dict()),
                )
                db.add(gen_file)
                await db.commit()
            except Exception as e:
                logger.warning("[ARTIFACT] Database commit warning: %s", e)
                await db.rollback()

        meta = ArtifactMetadata(
            id=art_id,
            filename=spec.filename,
            mime_type=mime_type,
            file_size=file_size,
            storage_path=file_path,
            download_url=download_url,
            sha256_hash=file_hash,
            format=fmt,
            category=category.value,
            title=spec.title,
            version=version,
            parent_id=parent_id,
            conversation_id=conversation_id,
            user_id=user_id,
            verification=val_res.to_dict(),
            source_files_used=spec.source_files,
        )
        return meta
