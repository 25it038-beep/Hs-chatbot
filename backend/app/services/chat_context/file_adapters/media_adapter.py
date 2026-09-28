import os
import logging
from typing import Dict, List, Optional, Any
from app.services.chat_context.contracts import (
    FileCapability,
    FileProcessingState,
    DocumentChunk,
    FileAnalysisResult
)
from app.services.chat_context.file_adapters.base import BaseFileAdapter

logger = logging.getLogger("hsbot.chat_context.media")


class MediaAdapter(BaseFileAdapter):
    capability = FileCapability.MEDIA if hasattr(FileCapability, "MEDIA") else FileCapability.OTHER
    supported_extensions = [
        ".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac",
        ".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"
    ]
    supported_mimes = [
        "audio/mpeg", "audio/wav", "audio/mp4", "audio/ogg", "audio/flac",
        "video/mp4", "video/quicktime", "video/x-msvideo", "video/webm"
    ]

    AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac"}
    VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}

    def _estimate_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)

    async def extract(self, file_path: str, filename: str, file_id: str) -> FileAnalysisResult:
        if not os.path.exists(file_path):
            return FileAnalysisResult(
                file_id=file_id,
                filename=filename,
                capability=FileCapability.AUDIO if os.path.splitext(filename)[1].lower() in self.AUDIO_EXTENSIONS else FileCapability.VIDEO,
                state=FileProcessingState.FAILED,
                error=f"File not found: {file_path}"
            )

        ext = os.path.splitext(filename)[1].lower()
        is_audio = ext in self.AUDIO_EXTENSIONS
        capability = FileCapability.AUDIO if is_audio else FileCapability.VIDEO
        media_type_label = "Audio" if is_audio else "Video"

        size_bytes = os.path.getsize(file_path)
        size_mb = size_bytes / (1024 * 1024)

        metadata: Dict[str, Any] = {
            "filename": filename,
            "media_type": media_type_label.lower(),
            "format": ext.lstrip(".").upper(),
            "size_bytes": size_bytes,
            "size_mb": round(size_mb, 2)
        }

        notice = (
            f"### {media_type_label} File Attachment: `{filename}`\n"
            f"- **Type**: {media_type_label} container ({ext.lstrip('.').upper()})\n"
            f"- **File Size**: {size_mb:.2f} MB ({size_bytes:,} bytes)\n"
            f"- **Status**: Partially Supported (Container metadata extracted)\n"
            f"- **Note**: Deep speech transcription or frame-level visual analysis requires specialized ASR / computer vision pipelines. General Chat can discuss the file metadata, format, and context."
        )

        location = f"{media_type_label} file {filename}"
        chunk = DocumentChunk(
            chunk_id=f"{file_id}_media",
            file_id=file_id,
            source=filename,
            location=location,
            section=f"{media_type_label} Metadata",
            content=notice,
            token_count=self._estimate_tokens(notice),
            metadata=metadata
        )

        summary = f"{media_type_label} file '{filename}' ({size_mb:.2f} MB, {ext.lstrip('.').upper()}). Metadata extracted; partial support declared."

        return FileAnalysisResult(
            file_id=file_id,
            filename=filename,
            capability=capability,
            state=FileProcessingState.PARTIALLY_SUPPORTED,
            summary=summary,
            chunks=[chunk],
            total_tokens=chunk.token_count,
            metadata=metadata,
            citations=[location],
            is_partially_supported=True
        )
