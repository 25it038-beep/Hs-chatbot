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

logger = logging.getLogger("hsbot.chat_context.fallback")


class FallbackAdapter(BaseFileAdapter):
    """
    Fallback adapter for arbitrary, unknown, or binary file types.
    Enforces the Any File Type Principle:
    - Never fails silently
    - Never pretends arbitrary binary content was extracted as text
    - Identifies extension, size, and magic bytes
    - Declares partial support honestly
    """

    capability = FileCapability.OTHER
    supported_extensions = []
    supported_mimes = []

    def can_handle(self, filename: str, mime_type: Optional[str] = None) -> bool:
        # Fallback adapter handles any file if no specific adapter matched
        return True

    def _estimate_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)

    async def extract(self, file_path: str, filename: str, file_id: str) -> FileAnalysisResult:
        if not os.path.exists(file_path):
            return FileAnalysisResult(
                file_id=file_id,
                filename=filename,
                capability=self.capability,
                state=FileProcessingState.FAILED,
                error=f"File not found: {file_path}"
            )

        ext = os.path.splitext(filename)[1].lower() or "(no extension)"
        size_bytes = os.path.getsize(file_path)

        # Inspect first 64 bytes to detect ASCII vs binary
        magic_hex = ""
        is_printable_ascii = False
        try:
            with open(file_path, "rb") as f:
                header_bytes = f.read(64)
                magic_hex = " ".join(f"{b:02x}" for b in header_bytes[:16])
                # Check if it might just be a text file with an unusual extension
                if header_bytes and all(b in (9, 10, 13) or 32 <= b <= 126 for b in header_bytes):
                    is_printable_ascii = True
        except Exception as e:
            logger.warning(f"Error reading header of {filename}: {e}")

        # If it happens to be plain text under an unknown extension, attempt a text read
        if is_printable_ascii and size_bytes < 500_000:
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    snippet = f.read(2000)
                location = f"File {filename}"
                content_block = (
                    f"### File: `{filename}` ({ext})\n"
                    f"Size: {size_bytes} bytes (detected plain text format)\n"
                    f"```\n{snippet}\n```"
                )
                chunk = DocumentChunk(
                    chunk_id=f"{file_id}_snippet",
                    file_id=file_id,
                    source=filename,
                    location=location,
                    section="Text Inspection",
                    content=content_block,
                    token_count=self._estimate_tokens(content_block),
                    metadata={"magic_hex": magic_hex, "size_bytes": size_bytes}
                )
                return FileAnalysisResult(
                    file_id=file_id,
                    filename=filename,
                    capability=FileCapability.TEXT,
                    state=FileProcessingState.READY,
                    summary=f"Plain text file '{filename}' ({size_bytes} bytes).",
                    chunks=[chunk],
                    total_tokens=chunk.token_count,
                    metadata={"size_bytes": size_bytes},
                    citations=[location]
                )
            except Exception:
                pass

        # Otherwise: Binary / unsupported file type with honest disclosure
        report = (
            f"### Attachment: `{filename}`\n"
            f"- **File Extension**: `{ext}`\n"
            f"- **File Size**: {size_bytes / 1024:.1f} KB ({size_bytes:,} bytes)\n"
            f"- **Header Magic Bytes**: `{magic_hex}`\n"
            f"- **Format Support**: Generic Binary / Unrecognized Extension\n"
            f"- **Notice**: The internal data structure for this file type is binary or proprietary. "
            f"Full content extraction is not available for this format, but you may ask about its purpose, header format, or conversion methods."
        )

        location = f"File {filename}"
        chunk = DocumentChunk(
            chunk_id=f"{file_id}_info",
            file_id=file_id,
            source=filename,
            location=location,
            section="Binary File Identification",
            content=report,
            token_count=self._estimate_tokens(report),
            metadata={"magic_hex": magic_hex, "size_bytes": size_bytes}
        )

        summary = f"File '{filename}' ({ext}, {size_bytes:,} bytes). Binary/unrecognized format; inspected header bytes."

        return FileAnalysisResult(
            file_id=file_id,
            filename=filename,
            capability=FileCapability.OTHER,
            state=FileProcessingState.PARTIALLY_SUPPORTED,
            summary=summary,
            chunks=[chunk],
            total_tokens=chunk.token_count,
            metadata={"magic_hex": magic_hex, "size_bytes": size_bytes},
            citations=[location],
            is_partially_supported=True
        )
