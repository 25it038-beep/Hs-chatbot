import os
import time
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple


class OutputIntent(str, Enum):
    CHAT = "CHAT"
    FILE = "FILE"
    CHAT_AND_FILE = "CHAT_AND_FILE"
    MULTIPLE_FILES = "MULTIPLE_FILES"
    PROJECT = "PROJECT"
    ARCHIVE = "ARCHIVE"


class ArtifactCategory(str, Enum):
    DOCUMENT = "DOCUMENT"
    SPREADSHEET = "SPREADSHEET"
    PRESENTATION = "PRESENTATION"
    DATA = "DATA"
    CODE = "CODE"
    WEB = "WEB"
    ARCHIVE = "ARCHIVE"
    MEDIA = "MEDIA"


@dataclass
class ArtifactSpec:
    format: str                           # pdf, docx, xlsx, pptx, csv, json, yaml, py, html, zip, etc.
    output_intent: OutputIntent           # CHAT, FILE, CHAT_AND_FILE, etc.
    title: str                            # e.g. "Database Normalization Guide"
    filename: str                         # e.g. "normalization_guide.pdf"
    category: ArtifactCategory            # DOCUMENT, SPREADSHEET, etc.
    topic: str = ""                       # core topic
    user_prompt: str = ""                 # raw prompt
    count: Optional[int] = None           # e.g. 5 slides, 3 pages
    count_unit: Optional[str] = None      # "page", "slide", "sheet"
    is_conversational_edit: bool = False  # True if editing existing artifact
    is_format_conversion: bool = False   # True if converting an existing artifact to new format
    parent_artifact_id: Optional[str] = None # ID of previous artifact if versioning
    edit_instruction: Optional[str] = None # specific modification directive
    source_files: List[str] = field(default_factory=list) # uploaded files to incorporate
    requires_chat_response: bool = False  # True if user also requested explanation/answer in chat
    is_ambiguous: bool = False            # True if user asked for a file but format is completely unspecified
    suggested_formats: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "format": self.format,
            "output_intent": self.output_intent.value,
            "title": self.title,
            "filename": self.filename,
            "category": self.category.value,
            "topic": self.topic,
            "count": self.count,
            "count_unit": self.count_unit,
            "is_conversational_edit": self.is_conversational_edit,
            "is_format_conversion": self.is_format_conversion,
            "parent_artifact_id": self.parent_artifact_id,
            "edit_instruction": self.edit_instruction,
            "source_files": self.source_files,
            "requires_chat_response": self.requires_chat_response,
            "is_ambiguous": self.is_ambiguous,
            "suggested_formats": self.suggested_formats,
        }


@dataclass
class ValidationResult:
    is_valid: bool
    format: str
    error: Optional[str] = None
    checks_passed: int = 0
    total_checks: int = 0
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ArtifactMetadata:
    id: str
    filename: str
    mime_type: str
    file_size: int
    storage_path: str
    download_url: str
    sha256_hash: str
    format: str
    category: str
    title: str
    version: int = 1
    parent_id: Optional[str] = None
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    preview_data: Optional[Dict[str, Any]] = None
    verification: Optional[Dict[str, Any]] = None
    source_files_used: List[str] = field(default_factory=list)

    def to_attachment_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.filename,
            "type": self.mime_type,
            "size": self.file_size,
            "download_url": self.download_url,
            "format": self.format,
            "category": self.category,
            "version": self.version,
            "parent_id": self.parent_id,
            "sha256": self.sha256_hash,
            "verification": self.verification,
            "preview_data": self.preview_data,
        }
