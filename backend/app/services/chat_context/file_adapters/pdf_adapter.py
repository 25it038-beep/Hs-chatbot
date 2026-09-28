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

logger = logging.getLogger("hsbot.chat_context.pdf")


class PDFAdapter(BaseFileAdapter):
    capability = FileCapability.PDF
    supported_extensions = [".pdf"]
    supported_mimes = ["application/pdf"]

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

        chunks: List[DocumentChunk] = []
        citations: List[str] = []
        total_pages = 0
        extracted_text_blocks = []

        # 1. Try PyMuPDF (fitz)
        try:
            import fitz
            doc = fitz.open(file_path)
            total_pages = len(doc)

            for page_idx in range(total_pages):
                page = doc[page_idx]
                page_num = page_idx + 1
                text = page.get_text("text").strip()

                if not text:
                    continue

                chunk_id = f"{file_id}_p{page_num}"
                location = f"Page {page_num} of {filename}"
                token_count = self._estimate_tokens(text)

                chunk = DocumentChunk(
                    chunk_id=chunk_id,
                    file_id=file_id,
                    source=filename,
                    location=location,
                    page=page_num,
                    section=f"Page {page_num}",
                    content=text,
                    token_count=token_count,
                    metadata={"page": page_num}
                )
                chunks.append(chunk)
                citations.append(location)
                extracted_text_blocks.append(text[:200])

            doc.close()

        except ImportError:
            # 2. Fallback: pdfplumber or pypdf
            try:
                import pypdf
                reader = pypdf.PdfReader(file_path)
                total_pages = len(reader.pages)

                for page_idx, page in enumerate(reader.pages):
                    page_num = page_idx + 1
                    text = page.extract_text() or ""
                    text = text.strip()

                    if not text:
                        continue

                    chunk_id = f"{file_id}_p{page_num}"
                    location = f"Page {page_num} of {filename}"
                    token_count = self._estimate_tokens(text)

                    chunk = DocumentChunk(
                        chunk_id=chunk_id,
                        file_id=file_id,
                        source=filename,
                        location=location,
                        page=page_num,
                        section=f"Page {page_num}",
                        content=text,
                        token_count=token_count,
                        metadata={"page": page_num}
                    )
                    chunks.append(chunk)
                    citations.append(location)
                    extracted_text_blocks.append(text[:200])

            except Exception as e:
                logger.error(f"Failed to read PDF with fallback reader: {e}")
                return FileAnalysisResult(
                    file_id=file_id,
                    filename=filename,
                    capability=self.capability,
                    state=FileProcessingState.FAILED,
                    error=f"Could not parse PDF: {str(e)}"
                )

        except Exception as e:
            logger.error(f"Error parsing PDF with PyMuPDF: {e}")
            return FileAnalysisResult(
                file_id=file_id,
                filename=filename,
                capability=self.capability,
                state=FileProcessingState.FAILED,
                error=f"Error reading PDF: {str(e)}"
            )

        total_tokens = sum(c.token_count for c in chunks)
        is_partial = False
        state = FileProcessingState.READY

        if total_pages > 0 and len(chunks) == 0:
            summary = f"PDF document '{filename}' has {total_pages} pages, but contains scanned images or non-extractable text."
            is_partial = True
            state = FileProcessingState.PARTIALLY_SUPPORTED
        else:
            summary = f"PDF document '{filename}' with {total_pages} pages, {len(chunks)} text pages extracted, ~{total_tokens} tokens."

        return FileAnalysisResult(
            file_id=file_id,
            filename=filename,
            capability=self.capability,
            state=state,
            summary=summary,
            chunks=chunks,
            total_tokens=total_tokens,
            total_pages=total_pages,
            metadata={"total_pages": total_pages, "extracted_pages": len(chunks)},
            citations=citations,
            is_partially_supported=is_partial
        )
