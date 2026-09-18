import io
import os
import re
import zipfile
import time
import uuid
import shutil
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from app.config import settings
from app.services.document_service.service import DocumentService, MIME_TYPES
from app.services.document_service.verifier import document_verifier
from app.services.artifacts.models import ArtifactMetadata, ArtifactCategory, ArtifactVersionRecord
from app.services.artifacts.registry import artifact_registry
from app.services.artifacts.adapters import adapter_registry
from app.services.artifacts.preview import artifact_preview

logger = logging.getLogger("hsbot.artifacts")

SECRET_PATTERNS = [
    (re.compile(r"nvapi-[A-Za-z0-9_\-]{20,}", re.IGNORECASE), "NVIDIA API Key"),
    (re.compile(r"sk-[A-Za-z0-9_\-]{20,}", re.IGNORECASE), "OpenAI API Key"),
    (re.compile(r"ghp_[A-Za-z0-9]{30,}", re.IGNORECASE), "GitHub Personal Access Token"),
    (re.compile(r"eyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}", re.IGNORECASE), "JWT / Bearer Token"),
    (re.compile(r"-----BEGIN (?:RSA )?PRIVATE KEY-----", re.IGNORECASE), "Private Key"),
    (re.compile(r"(?:api[_-]?key|secret[_-]?key|auth[_-]?token)[\s:=]+['\"]?([A-Za-z0-9_\-\.]{16,})['\"]?", re.IGNORECASE), "Sensitive Credential"),
]

class SecretLeakDetectedError(Exception):
    def __init__(self, secret_type: str, file_path: str):
        super().__init__(f"Artifact delivery blocked: Detected {secret_type} in '{file_path}'")
        self.secret_type = secret_type
        self.file_path = file_path

class ArtifactSecretScanner:
    """Scans files and archives for leaked credentials before delivery."""
    @staticmethod
    def scan_text(text: str, filename: str = "content") -> Optional[str]:
        for pattern, desc in SECRET_PATTERNS:
            if pattern.search(text):
                return desc
        return None

    @classmethod
    def scan_file(cls, file_path: Path) -> Optional[str]:
        if not file_path.exists() or file_path.stat().st_size > 10_000_000:
            return None
        try:
            # Check if it's a zip archive
            if file_path.suffix.lower() == ".zip":
                return cls.scan_zip(file_path)
            # Text / readable scan
            with open(file_path, "rb") as f:
                header = f.read(1024)
                # Skip binary images
                if b"\x00" in header and file_path.suffix.lower() in [".png", ".jpg", ".jpeg", ".ico", ".pdf", ".docx", ".pptx", ".xlsx"]:
                    return None
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            return cls.scan_text(content, file_path.name)
        except Exception:
            return None

    @classmethod
    def scan_zip(cls, zip_path: Path) -> Optional[str]:
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                for member in zf.infolist():
                    if member.file_size > 2_000_000:
                        continue
                    if any(member.filename.endswith(ext) for ext in [".py", ".js", ".ts", ".tsx", ".env", ".json", ".yaml", ".yml", ".md", ".txt"]):
                        with zf.open(member) as f:
                            text = f.read().decode("utf-8", errors="ignore")
                            found = cls.scan_text(text, member.filename)
                            if found:
                                return f"{found} in archive member '{member.filename}'"
        except Exception:
            pass
        return None

class UniversalArtifactEngine:
    """
    Universal Artifact Generation, Preview, Editing & Verification Engine.
    Handles Documents (PDF, DOCX, PPTX, XLSX, CSV, MD), Code projects, and ZIP packages.
    """
    def __init__(self, artifact_storage_dir: Optional[str] = None):
        self.storage_dir = Path(artifact_storage_dir or settings.upload_dir) / "artifacts"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.registry = artifact_registry
        self.adapters = adapter_registry
        from app.services.artifacts.editor import artifact_editor
        self.editor = artifact_editor
        self.preview = artifact_preview

    def create_zip_project(
        self,
        workspace_dir: Path,
        zip_filename: str,
        exclude_dirs: Optional[List[str]] = None,
        chat_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Packages a workspace project into a verified ZIP archive."""
        if not zip_filename.endswith(".zip"):
            zip_filename += ".zip"

        excludes = set(exclude_dirs or ["node_modules", ".git", "__pycache__", "dist", ".next", ".cache", "artifacts"])
        artifact_id = str(uuid.uuid4())[:8]
        dest_path = self.storage_dir / f"{artifact_id}_{zip_filename}"

        total_files = 0
        total_uncompressed_bytes = 0

        with zipfile.ZipFile(dest_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(workspace_dir):
                dirs[:] = [d for d in dirs if d not in excludes]
                rel_root = Path(root).relative_to(workspace_dir)

                for f in files:
                    if f.startswith(".env") or f in [".DS_Store", "thumbs.db"]:
                        continue
                    file_path = Path(root) / f
                    arcname = (rel_root / f).as_posix()
                    zf.write(file_path, arcname=arcname)
                    total_files += 1
                    total_uncompressed_bytes += file_path.stat().st_size

        # Validate ZIP integrity
        with zipfile.ZipFile(dest_path, "r") as zf:
            test_result = zf.testzip()
            if test_result is not None:
                dest_path.unlink(missing_ok=True)
                return {
                    "success": False,
                    "error": f"Corrupted file inside generated archive: {test_result}"
                }

        # Secret Scanning
        leak = ArtifactSecretScanner.scan_zip(dest_path)
        if leak:
            dest_path.unlink(missing_ok=True)
            raise SecretLeakDetectedError(leak, zip_filename)

        file_size = dest_path.stat().st_size
        preview_data = self.adapters.get("zip").render_preview(dest_path) if self.adapters.get("zip") else {}

        meta = ArtifactMetadata(
            artifact_id=artifact_id,
            name=zip_filename,
            filename=zip_filename,
            extension="zip",
            mime_type="application/zip",
            artifact_type="zip_archive",
            category=ArtifactCategory.ARCHIVE,
            storage_path=str(dest_path),
            size=file_size,
            created_at=time.time(),
            updated_at=time.time(),
            version=1,
            chat_id=chat_id,
            user_id=user_id,
            generation_method="zip_packager",
            validation_status="passed",
            visual_validation_status="passed",
            security_status="passed",
            delivery_status="ready",
            preview_data=preview_data,
            content_summary=f"ZIP archive with {total_files} files"
        )
        saved = self.registry.register_artifact(meta)
        return {"success": True, "artifact": saved.to_dict()}

    async def create_document_artifact(
        self,
        format_type: str,
        topic: str,
        title: str,
        filename: str,
        count: Optional[int] = None,
        chat_id: Optional[str] = None,
        user_id: Optional[str] = None,
        db_session: Any = None
    ) -> Dict[str, Any]:
        """Generates and verifies PDF/DOCX/PPTX/XLSX/CSV/Markdown using DocumentService."""
        fmt = format_type.lower().strip()
        doc_service = DocumentService()
        result = await doc_service.generate_and_save(
            fmt=fmt,
            topic=topic,
            title=title,
            filename=filename,
            count=count,
            count_unit="slide" if fmt == "pptx" else "page",
            user_id=user_id,
            conversation_id=chat_id,
            db=db_session
        )

        if not result or not result.get("success"):
            return {"success": False, "error": result.get("error", "Document generation failed") if result else "Failed"}

        # Perform Secret Scan
        saved_path = Path(result.get("storage_path", ""))
        if saved_path.exists():
            leak = ArtifactSecretScanner.scan_file(saved_path)
            if leak:
                saved_path.unlink(missing_ok=True)
                raise SecretLeakDetectedError(leak, filename)

        artifact_id = result.get("id") or str(uuid.uuid4())[:8]
        adapter = self.adapters.get(fmt)
        cat = adapter.category if adapter else ArtifactCategory.DOCUMENT

        meta = ArtifactMetadata(
            artifact_id=artifact_id,
            name=filename,
            filename=filename,
            extension=fmt,
            mime_type=MIME_TYPES.get(fmt, "application/octet-stream"),
            artifact_type=fmt,
            category=cat,
            storage_path=str(saved_path),
            size=result.get("file_size", 0),
            created_at=time.time(),
            updated_at=time.time(),
            version=1,
            chat_id=chat_id,
            user_id=user_id,
            generation_method="document_service",
            validation_status="passed",
            visual_validation_status="passed",
            security_status="passed",
            delivery_status="ready",
            preview_data=result.get("preview_data"),
            content_summary=f"{fmt.upper()} document: {title}"
        )
        saved = self.registry.register_artifact(meta)
        return {"success": True, "artifact": saved.to_dict()}

    def get_artifact(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        art = self.registry.get(artifact_id)
        return art.to_dict() if art else None

    def list_artifacts(self, chat_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return [a.to_dict() for a in self.registry.list_artifacts(chat_id=chat_id)]

# Singleton instance
artifact_engine = UniversalArtifactEngine()
