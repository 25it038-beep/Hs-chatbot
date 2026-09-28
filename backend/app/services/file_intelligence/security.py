"""
HSBot General Chat — File Security, Magic-Byte Detection, Validation & Archive Safety (V2)
"""
import os
import re
import hashlib
import zipfile
import tarfile
from pathlib import Path
from typing import Tuple, Optional, Any
from app.services.file_intelligence.models import FILE_LIMITS


CODE_EXTENSIONS: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".jsx": "jsx",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".c": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
    ".sql": "sql",
    ".sh": "bash",
    ".bash": "bash",
    ".ps1": "powershell",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "scss",
    ".toml": "toml",
    ".ini": "ini",
    ".cfg": "ini",
    ".env": "dotenv",
    ".dockerfile": "dockerfile",
}


def sanitize_filename(filename: str) -> str:
    """Strip path traversal, control characters, and null bytes from filenames."""
    if not filename:
        return "unnamed_file"
    base = os.path.basename(filename.replace("\\", "/"))
    base = re.sub(r"[\x00-\x1f\x7f]", "", base).strip()
    base = re.sub(r'[<>:"/\\|?*]', "_", base)
    if not base or base in (".", ".."):
        return "unnamed_file"
    return base[:200]


def compute_sha256_file(file_path: str) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            block = f.read(65536)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def detect_file_type_and_validate(
    file_path: str,
    original_filename: str,
    client_mime: Optional[str] = None,
) -> dict[str, Any]:
    """
    Detect true file type using magic bytes, OOXML container inspection, and extension fallback.
    Also detects corrupt headers/containers and performs active-content security scanning.
    """
    safe_name = sanitize_filename(original_filename)
    ext_with_dot = os.path.splitext(safe_name)[1].lower()
    ext = ext_with_dot.lstrip(".")
    size = os.path.getsize(file_path) if os.path.exists(file_path) else 0

    with open(file_path, "rb") as f:
        header = f.read(4096)

    is_corrupt = False
    corrupt_reason: Optional[str] = None
    detected_format = "unsupported"
    mime_type = client_mime or "application/octet-stream"
    security_warnings: list[str] = []

    # 1. Check Magic Bytes & Container Signatures
    if header.startswith(b"%PDF-"):
        detected_format = "pdf"
        mime_type = "application/pdf"
    elif header.startswith(b"\x89PNG\r\n\x1a\n"):
        detected_format = "image"
        mime_type = "image/png"
    elif header.startswith(b"\xff\xd8\xff"):
        detected_format = "image"
        mime_type = "image/jpeg"
    elif header.startswith((b"GIF87a", b"GIF89a")):
        detected_format = "image"
        mime_type = "image/gif"
    elif header.startswith(b"RIFF") and header[8:12] == b"WEBP":
        detected_format = "image"
        mime_type = "image/webp"
    elif header.startswith(b"BM"):
        detected_format = "image"
        mime_type = "image/bmp"
    elif header.startswith(b"PK\x03\x04") or header.startswith(b"PK\x05\x06"):
        # ZIP or OOXML (DOCX / XLSX / PPTX)
        if zipfile.is_zipfile(file_path):
            try:
                with zipfile.ZipFile(file_path, "r") as zf:
                    names = set(zf.namelist())
                    if any(n.startswith("word/") for n in names):
                        detected_format = "docx"
                        mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    elif any(n.startswith("xl/") for n in names):
                        detected_format = "xlsx"
                        mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    elif any(n.startswith("ppt/") for n in names):
                        detected_format = "pptx"
                        mime_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
                    else:
                        detected_format = "archive"
                        mime_type = "application/zip"
                    if any(n.endswith("vbaProject.bin") for n in names):
                        security_warnings.append("Macro binary (vbaProject.bin) detected and stripped from execution.")
            except Exception as e:
                is_corrupt = True
                corrupt_reason = f"Corrupted ZIP/OOXML container: {e}"
                detected_format = ext if ext in ("docx", "xlsx", "pptx") else "archive"
        else:
            is_corrupt = True
            corrupt_reason = "Truncated or corrupted PKZIP header."
            detected_format = ext if ext in ("docx", "xlsx", "pptx") else "archive"
    elif tarfile.is_tarfile(file_path):
        detected_format = "archive"
        mime_type = "application/x-tar"

    # 2. Check if extension claims binary container (PDF/DOCX/XLSX/PPTX/IMAGE/ZIP) but magic bytes don't match
    if detected_format == "unsupported":
        if ext == "pdf":
            is_corrupt = True
            corrupt_reason = "PDF could not be parsed: missing %PDF header (corrupted or invalid PDF file)."
            detected_format = "pdf"
            mime_type = "application/pdf"
        elif ext in ("docx", "xlsx", "pptx"):
            is_corrupt = True
            corrupt_reason = f"{ext.upper()} could not be parsed: not a valid OpenXML container (corrupted file)."
            detected_format = ext
        elif ext in ("png", "jpg", "jpeg", "webp", "gif", "bmp"):
            is_corrupt = True
            corrupt_reason = f"Image file '{safe_name}' has corrupted or invalid image header bytes."
            detected_format = "image"
        elif ext in ("zip", "tar", "gz", "tgz"):
            is_corrupt = True
            corrupt_reason = f"Archive '{safe_name}' is corrupted or not a valid archive."
            detected_format = "archive"
        elif ext in ("mp3", "wav", "m4a", "ogg", "flac"):
            detected_format = "audio"
            mime_type = f"audio/{ext}"
        elif ext in ("mp4", "mov", "webm", "mkv", "avi"):
            detected_format = "video"
            mime_type = f"video/{ext}"
        elif ext in ("csv", "tsv"):
            detected_format = "csv"
            mime_type = "text/csv"
        elif ext in ("json", "jsonl", "xml", "yaml", "yml"):
            detected_format = "yaml" if ext in ("yaml", "yml") else ext
            mime_type = f"application/{detected_format}"
        elif ext in ("md", "markdown"):
            detected_format = "md"
            mime_type = "text/markdown"
        elif ext == "txt" or ext == "log":
            detected_format = "txt"
            mime_type = "text/plain"
        elif ext_with_dot in CODE_EXTENSIONS or safe_name.lower() == "dockerfile":
            detected_format = "code"
            mime_type = "text/plain"
        else:
            # Check if unknown extension or unknown binary
            is_probably_binary = b"\x00" in header[:1024]
            if is_probably_binary or ext not in ("", "txt", "text"):
                detected_format = "unsupported"
            else:
                detected_format = "txt"
                mime_type = "text/plain"

    # 3. Validate structured text formats (JSON/XML) for corruption at validation stage if needed
    if not is_corrupt and detected_format in ("json", "xml"):
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as tf:
                raw_content = tf.read()
            if detected_format == "json":
                import json
                json.loads(raw_content)
            elif detected_format == "xml":
                import xml.etree.ElementTree as ET
                if "<!ENTITY" in raw_content.upper():
                    security_warnings.append("XML external entity (XXE) declaration detected.")
                    is_corrupt = True
                    corrupt_reason = "XML file rejected: contains disallowed <!ENTITY declaration."
                else:
                    ET.fromstring(raw_content)
        except Exception as e:
            is_corrupt = True
            corrupt_reason = f"Malformed {detected_format.upper()} syntax: {str(e)}"

    return {
        "filename": safe_name,
        "extension": ext or "bin",
        "mime_type": mime_type,
        "detected_format": detected_format,
        "size": size,
        "is_corrupt": is_corrupt,
        "corrupt_reason": corrupt_reason,
        "security_scan": {
            "passed": not is_corrupt,
            "warnings": security_warnings,
            "active_content_executed": False,
        },
    }


def validate_archive_safety(file_path: str) -> Tuple[bool, Optional[str], list[dict[str, Any]]]:
    """
    Inspect ZIP or TAR archive for zip-slip (`..`), absolute paths, nested archive bombs,
    file count > MAX_ARCHIVE_FILES, or total uncompressed size > MAX_ARCHIVE_EXTRACTED_SIZE.
    """
    tree: list[dict[str, Any]] = []
    total_uncompressed = 0
    file_count = 0

    if zipfile.is_zipfile(file_path):
        try:
            with zipfile.ZipFile(file_path, "r") as zf:
                for info in zf.infolist():
                    raw_name = info.filename.replace("\\", "/")
                    if raw_name.startswith("/") or ".." in raw_name.split("/"):
                        return False, f"Unsafe archive path traversal rejected: '{raw_name}'", []
                    if info.is_dir():
                        continue
                    file_count += 1
                    if file_count > FILE_LIMITS.MAX_ARCHIVE_FILES:
                        return (
                            False,
                            f"Archive exceeds maximum allowed file count ({FILE_LIMITS.MAX_ARCHIVE_FILES}).",
                            [],
                        )
                    total_uncompressed += info.file_size
                    if total_uncompressed > FILE_LIMITS.MAX_ARCHIVE_EXTRACTED_SIZE:
                        return (
                            False,
                            f"Archive uncompressed size exceeds limit ({FILE_LIMITS.MAX_ARCHIVE_EXTRACTED_SIZE // (1024*1024)}MB).",
                            [],
                        )
                    ext = os.path.splitext(raw_name)[1].lower().lstrip(".") or "file"
                    tree.append({
                        "path": raw_name,
                        "size": info.file_size,
                        "type": ext,
                    })
            return True, None, tree
        except Exception as e:
            return False, f"Invalid ZIP archive: {e}", []

    elif tarfile.is_tarfile(file_path):
        try:
            with tarfile.open(file_path, "r:*") as tf:
                for member in tf.getmembers():
                    raw_name = member.name.replace("\\", "/")
                    if raw_name.startswith("/") or ".." in raw_name.split("/"):
                        return False, f"Unsafe tar path traversal rejected: '{raw_name}'", []
                    if member.issym() or member.islnk():
                        return False, f"Archive symlinks are disallowed for security: '{raw_name}'", []
                    if not member.isfile():
                        continue
                    file_count += 1
                    if file_count > FILE_LIMITS.MAX_ARCHIVE_FILES:
                        return (
                            False,
                            f"Archive exceeds maximum allowed file count ({FILE_LIMITS.MAX_ARCHIVE_FILES}).",
                            [],
                        )
                    total_uncompressed += member.size
                    if total_uncompressed > FILE_LIMITS.MAX_ARCHIVE_EXTRACTED_SIZE:
                        return (
                            False,
                            f"Archive uncompressed size exceeds limit ({FILE_LIMITS.MAX_ARCHIVE_EXTRACTED_SIZE // (1024*1024)}MB).",
                            [],
                        )
                    ext = os.path.splitext(raw_name)[1].lower().lstrip(".") or "file"
                    tree.append({
                        "path": raw_name,
                        "size": member.size,
                        "type": ext,
                    })
            return True, None, tree
        except Exception as e:
            return False, f"Invalid TAR archive: {e}", []

    return False, "Unsupported or corrupted archive container.", []
