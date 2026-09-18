import time
import uuid
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict

class ArtifactCategory(str, Enum):
    DOCUMENT = "document"
    SPREADSHEET = "spreadsheet"
    PRESENTATION = "presentation"
    CODE = "code"
    WEB = "web"
    IMAGE = "image"
    DATA = "data"
    CONFIGURATION = "configuration"
    ARCHIVE = "archive"
    DIAGRAM = "diagram"
    REPORT = "report"
    PROJECT = "project"
    OTHER = "other"

@dataclass
class ArtifactVersionRecord:
    version: int
    created_at: float
    storage_path: str
    file_size: int
    change_description: str = "Initial generation"
    checksum: Optional[str] = None
    verification_status: str = "verified"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class ArtifactMetadata:
    artifact_id: str
    name: str
    filename: str
    extension: str
    mime_type: str
    artifact_type: str # pdf, docx, pptx, xlsx, zip, code, html, svg, etc.
    category: ArtifactCategory
    storage_path: str
    size: int
    created_at: float
    updated_at: float
    version: int = 1
    parent_version: Optional[int] = None
    source_task_id: Optional[str] = None
    source_message_id: Optional[str] = None
    chat_id: Optional[str] = None
    user_id: Optional[str] = None
    generation_method: str = "adapter"
    validation_status: str = "passed" # passed, failed, pending
    visual_validation_status: str = "passed"
    security_status: str = "passed" # passed, blocked
    delivery_status: str = "ready" # ready, repairing, failed
    preview_data: Optional[Dict[str, Any]] = None
    content_summary: Optional[str] = None
    versions: List[ArtifactVersionRecord] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["category"] = self.category.value if isinstance(self.category, ArtifactCategory) else str(self.category)
        d["versions"] = [v.to_dict() for v in self.versions]
        d["download_url"] = f"/api/agent/artifacts/{self.artifact_id}/download"
        return d
