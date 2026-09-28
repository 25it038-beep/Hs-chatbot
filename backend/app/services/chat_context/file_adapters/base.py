import os
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from app.services.chat_context.contracts import (
    FileCapability,
    FileProcessingState,
    DocumentChunk,
    FileAnalysisResult
)


class BaseFileAdapter(ABC):
    """
    Abstract base adapter for universal file parsing and extraction.
    Adheres strictly to the Any File Type Principle:
    - If supported -> extract and analyze
    - If partially supported -> extract safe text/metadata
    - If unsupported -> identify file type, explain what is not supported, never pretend it was parsed.
    """

    capability: FileCapability = FileCapability.OTHER
    supported_extensions: List[str] = []
    supported_mimes: List[str] = []

    def can_handle(self, filename: str, mime_type: Optional[str] = None) -> bool:
        ext = os.path.splitext(filename)[1].lower()
        if ext in self.supported_extensions:
            return True
        if mime_type and mime_type.lower() in self.supported_mimes:
            return True
        return False

    @abstractmethod
    async def extract(self, file_path: str, filename: str, file_id: str) -> FileAnalysisResult:
        """Parses and extracts structured document chunks and content from the file."""
        pass

    def preview(self, file_path: str, filename: str) -> Dict[str, Any]:
        """Provides preview metadata or snippet for the UI."""
        return {
            "type": self.capability.value,
            "filename": filename,
            "size": os.path.getsize(file_path) if os.path.exists(file_path) else 0
        }

    def metadata(self, file_path: str, filename: str) -> Dict[str, Any]:
        """Returns file system and structure metadata."""
        if not os.path.exists(file_path):
            return {"filename": filename, "exists": False}
        return {
            "filename": filename,
            "size_bytes": os.path.getsize(file_path),
            "capability": self.capability.value,
            "extension": os.path.splitext(filename)[1].lower()
        }
