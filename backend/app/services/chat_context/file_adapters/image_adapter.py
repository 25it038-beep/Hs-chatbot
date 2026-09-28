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

logger = logging.getLogger("hsbot.chat_context.image")


class ImageAdapter(BaseFileAdapter):
    capability = FileCapability.IMAGE
    supported_extensions = [
        ".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg", ".tiff", ".ico"
    ]
    supported_mimes = [
        "image/png", "image/jpeg", "image/webp", "image/gif", "image/bmp", "image/svg+xml"
    ]

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

        ext = os.path.splitext(filename)[1].lower()
        size_bytes = os.path.getsize(file_path)
        metadata: Dict[str, Any] = {
            "filename": filename,
            "format": ext.lstrip(".").upper(),
            "size_bytes": size_bytes,
            "file_path": file_path
        }

        if ext == ".svg":
            # SVG XML inspection
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    svg_content = f.read(4000)

                summary = f"Vector Image (SVG): '{filename}' ({size_bytes} bytes)."
                chunk_content = f"### Vector Graphic (SVG): `{filename}`\nFile size: {size_bytes} bytes.\nSVG Snippet:\n```xml\n{svg_content[:1500]}\n```"
                location = f"Vector Graphic {filename}"
                chunk = DocumentChunk(
                    chunk_id=f"{file_id}_svg",
                    file_id=file_id,
                    source=filename,
                    location=location,
                    section="SVG Vector Graphic",
                    content=chunk_content,
                    token_count=self._estimate_tokens(chunk_content),
                    metadata=metadata
                )
                return FileAnalysisResult(
                    file_id=file_id,
                    filename=filename,
                    capability=self.capability,
                    state=FileProcessingState.READY,
                    summary=summary,
                    chunks=[chunk],
                    total_tokens=chunk.token_count,
                    metadata=metadata,
                    citations=[location]
                )
            except Exception as e:
                logger.error(f"Error inspecting SVG {filename}: {e}")

        # Raster image via PIL
        try:
            from PIL import Image
            with Image.open(file_path) as img:
                width, height = img.size
                img_format = img.format or ext.lstrip(".").upper()
                mode = img.mode

                metadata["width"] = width
                metadata["height"] = height
                metadata["mode"] = mode
                metadata["format"] = img_format

                summary = f"Image: '{filename}' ({width}x{height} px, {mode}, {img_format}, {size_bytes / 1024:.1f} KB)."
                chunk_content = (
                    f"### Image Attachment: `{filename}`\n"
                    f"- **Dimensions**: {width} × {height} pixels\n"
                    f"- **Format**: {img_format} ({mode})\n"
                    f"- **File Size**: {size_bytes / 1024:.1f} KB\n"
                    f"- **Path**: `{file_path}`\n"
                )
                location = f"Image {filename} ({width}x{height})"
                chunk = DocumentChunk(
                    chunk_id=f"{file_id}_img",
                    file_id=file_id,
                    source=filename,
                    location=location,
                    section=f"Image {filename}",
                    content=chunk_content,
                    token_count=self._estimate_tokens(chunk_content),
                    metadata=metadata
                )

                return FileAnalysisResult(
                    file_id=file_id,
                    filename=filename,
                    capability=self.capability,
                    state=FileProcessingState.READY,
                    summary=summary,
                    chunks=[chunk],
                    total_tokens=chunk.token_count,
                    metadata=metadata,
                    citations=[location]
                )

        except Exception as e:
            logger.warning(f"Failed to inspect image with PIL: {e}")
            summary = f"Image: '{filename}' ({size_bytes} bytes)."
            chunk_content = f"### Image Attachment: `{filename}`\nFile size: {size_bytes} bytes."
            location = f"Image {filename}"
            chunk = DocumentChunk(
                chunk_id=f"{file_id}_img",
                file_id=file_id,
                source=filename,
                location=location,
                section="Image",
                content=chunk_content,
                token_count=self._estimate_tokens(chunk_content),
                metadata=metadata
            )
            return FileAnalysisResult(
                file_id=file_id,
                filename=filename,
                capability=self.capability,
                state=FileProcessingState.READY,
                summary=summary,
                chunks=[chunk],
                total_tokens=chunk.token_count,
                metadata=metadata,
                citations=[location]
            )
