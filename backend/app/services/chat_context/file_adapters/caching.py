import hashlib
import os
import json
import logging
from typing import Optional, Dict, Any
from app.services.chat_context.contracts import FileAnalysisResult, DocumentChunk, FileCapability, FileProcessingState

logger = logging.getLogger("hsbot.chat_context.cache")

PARSER_VERSION = "2.1.0"


class FileProcessingCache:
    """
    In-memory and file-hash backed cache for processed files.
    Avoids re-parsing identical documents or spreadsheets across conversation turns.
    """

    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}

    def _compute_hash(self, file_path: str) -> str:
        if not os.path.exists(file_path):
            return ""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    def get(self, file_path: str, filename: str) -> Optional[FileAnalysisResult]:
        file_hash = self._compute_hash(file_path)
        if not file_hash:
            return None
        cache_key = f"{file_hash}:{PARSER_VERSION}"
        cached_data = self._cache.get(cache_key)
        if not cached_data:
            return None

        try:
            chunks = [
                DocumentChunk(**c) for c in cached_data["chunks"]
            ]
            return FileAnalysisResult(
                file_id=cached_data["file_id"],
                filename=filename,
                capability=FileCapability(cached_data["capability"]),
                state=FileProcessingState(cached_data["state"]),
                summary=cached_data["summary"],
                chunks=chunks,
                total_tokens=cached_data["total_tokens"],
                total_pages=cached_data.get("total_pages"),
                metadata=cached_data.get("metadata", {}),
                citations=cached_data.get("citations", []),
                error=cached_data.get("error"),
                is_partially_supported=cached_data.get("is_partially_supported", False),
            )
        except Exception as e:
            logger.warning(f"Error restoring cached file analysis: {e}")
            return None

    def put(self, file_path: str, result: FileAnalysisResult):
        file_hash = self._compute_hash(file_path)
        if not file_hash:
            return
        cache_key = f"{file_hash}:{PARSER_VERSION}"
        self._cache[cache_key] = result.to_dict()

    def clear(self):
        self._cache.clear()


file_processing_cache = FileProcessingCache()
