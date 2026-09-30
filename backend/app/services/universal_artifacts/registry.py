from typing import Dict, List, Optional, Any
from app.services.universal_artifacts.contracts import ArtifactCategory

MIME_REGISTRY: Dict[str, str] = {
    # Documents
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "doc": "application/msword",
    "md": "text/markdown",
    "markdown": "text/markdown",
    "txt": "text/plain",
    "rtf": "application/rtf",
    "odt": "application/vnd.oasis.opendocument.text",
    
    # Spreadsheets
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "xls": "application/vnd.ms-excel",
    "csv": "text/csv",
    "tsv": "text/tab-separated-values",
    "ods": "application/vnd.oasis.opendocument.spreadsheet",

    # Presentations
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "ppt": "application/vnd.ms-powerpoint",
    "odp": "application/vnd.oasis.opendocument.presentation",

    # Structured Data
    "json": "application/json",
    "jsonl": "application/x-ndjson",
    "yaml": "application/x-yaml",
    "yml": "application/x-yaml",
    "xml": "application/xml",
    "sql": "application/sql",

    # Code Files
    "py": "text/x-python",
    "js": "application/javascript",
    "ts": "application/typescript",
    "tsx": "text/typescript-jsx",
    "jsx": "text/jsx",
    "html": "text/html",
    "css": "text/css",
    "java": "text/x-java-source",
    "c": "text/x-c",
    "cpp": "text/x-c++src",
    "cs": "text/x-csharp",
    "go": "text/x-go",
    "rs": "text/rust",
    "php": "application/x-httpd-php",
    "rb": "application/x-ruby",
    "kt": "text/x-kotlin",
    "swift": "text/x-swift",
    "sh": "application/x-sh",
    "ps1": "text/plain",

    # Web & Media
    "svg": "image/svg+xml",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",

    # Archives
    "zip": "application/zip",
}

CATEGORY_MAP: Dict[str, ArtifactCategory] = {
    "pdf": ArtifactCategory.DOCUMENT,
    "docx": ArtifactCategory.DOCUMENT,
    "doc": ArtifactCategory.DOCUMENT,
    "md": ArtifactCategory.DOCUMENT,
    "markdown": ArtifactCategory.DOCUMENT,
    "txt": ArtifactCategory.DOCUMENT,
    "rtf": ArtifactCategory.DOCUMENT,
    "odt": ArtifactCategory.DOCUMENT,

    "xlsx": ArtifactCategory.SPREADSHEET,
    "xls": ArtifactCategory.SPREADSHEET,
    "csv": ArtifactCategory.SPREADSHEET,
    "tsv": ArtifactCategory.SPREADSHEET,
    "ods": ArtifactCategory.SPREADSHEET,

    "pptx": ArtifactCategory.PRESENTATION,
    "ppt": ArtifactCategory.PRESENTATION,
    "odp": ArtifactCategory.PRESENTATION,

    "json": ArtifactCategory.DATA,
    "jsonl": ArtifactCategory.DATA,
    "yaml": ArtifactCategory.DATA,
    "yml": ArtifactCategory.DATA,
    "xml": ArtifactCategory.DATA,
    "sql": ArtifactCategory.DATA,

    "py": ArtifactCategory.CODE,
    "js": ArtifactCategory.CODE,
    "ts": ArtifactCategory.CODE,
    "tsx": ArtifactCategory.CODE,
    "jsx": ArtifactCategory.CODE,
    "java": ArtifactCategory.CODE,
    "c": ArtifactCategory.CODE,
    "cpp": ArtifactCategory.CODE,
    "cs": ArtifactCategory.CODE,
    "go": ArtifactCategory.CODE,
    "rs": ArtifactCategory.CODE,
    "php": ArtifactCategory.CODE,
    "rb": ArtifactCategory.CODE,
    "kt": ArtifactCategory.CODE,
    "swift": ArtifactCategory.CODE,
    "sh": ArtifactCategory.CODE,
    "ps1": ArtifactCategory.CODE,

    "html": ArtifactCategory.WEB,
    "css": ArtifactCategory.WEB,
    "svg": ArtifactCategory.WEB,

    "png": ArtifactCategory.MEDIA,
    "jpg": ArtifactCategory.MEDIA,
    "jpeg": ArtifactCategory.MEDIA,
    "webp": ArtifactCategory.MEDIA,

    "zip": ArtifactCategory.ARCHIVE,
}

PREVIEW_TYPE_MAP: Dict[str, str] = {
    "pdf": "pages",
    "docx": "document",
    "doc": "document",
    "pptx": "slides",
    "ppt": "slides",
    "xlsx": "table",
    "xls": "table",
    "csv": "table",
    "tsv": "table",
    "json": "json_tree",
    "jsonl": "json_tree",
    "yaml": "code",
    "yml": "code",
    "xml": "code",
    "sql": "code",
    "py": "code",
    "js": "code",
    "ts": "code",
    "tsx": "code",
    "jsx": "code",
    "html": "code",
    "css": "code",
    "md": "document",
    "txt": "text",
    "svg": "image",
    "png": "image",
    "jpg": "image",
    "jpeg": "image",
    "webp": "image",
    "zip": "archive",
}


class ArtifactFormatRegistryV2:
    """Central registry declaring MIME types, categories, and capabilities for all supported artifacts (§14)."""

    @classmethod
    def get_mime_type(cls, ext: str) -> str:
        clean = ext.lower().lstrip(".")
        return MIME_REGISTRY.get(clean, "application/octet-stream")

    @classmethod
    def get_category(cls, ext: str) -> ArtifactCategory:
        clean = ext.lower().lstrip(".")
        return CATEGORY_MAP.get(clean, ArtifactCategory.DOCUMENT)

    @classmethod
    def get_preview_type(cls, ext: str) -> str:
        clean = ext.lower().lstrip(".")
        return PREVIEW_TYPE_MAP.get(clean, "text")

    @classmethod
    def is_supported(cls, ext: str) -> bool:
        clean = ext.lower().lstrip(".")
        return clean in MIME_REGISTRY

    @classmethod
    def list_supported_formats(cls) -> List[str]:
        return sorted(list(MIME_REGISTRY.keys()))
