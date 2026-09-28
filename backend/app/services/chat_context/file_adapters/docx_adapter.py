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

logger = logging.getLogger("hsbot.chat_context.docx")


class DOCXAdapter(BaseFileAdapter):
    capability = FileCapability.WORD_DOCUMENT
    supported_extensions = [".docx", ".doc"]
    supported_mimes = [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword"
    ]

    CHUNK_PARAGRAPHS = 25

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
        if ext == ".doc":
            # Binary .doc legacy format - partial support explanation
            return FileAnalysisResult(
                file_id=file_id,
                filename=filename,
                capability=self.capability,
                state=FileProcessingState.PARTIALLY_SUPPORTED,
                summary=f"Legacy binary Word document (.doc). Please save as .docx for complete structural extraction.",
                is_partially_supported=True
            )

        chunks: List[DocumentChunk] = []
        citations: List[str] = []

        try:
            import docx
            doc = docx.Document(file_path)

            paragraphs_text = []
            current_section = "Introduction"

            # Parse paragraphs and headings
            section_chunks = []
            current_buffer = []

            for p in doc.paragraphs:
                txt = p.text.strip()
                if not txt:
                    continue

                if p.style and p.style.name.startswith("Heading"):
                    if current_buffer:
                        section_chunks.append((current_section, "\n\n".join(current_buffer)))
                        current_buffer = []
                    current_section = txt
                else:
                    current_buffer.append(txt)

            if current_buffer:
                section_chunks.append((current_section, "\n\n".join(current_buffer)))

            # If no headings found, split by fixed paragraph count
            if not section_chunks:
                all_paras = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
                for i in range(0, max(1, len(all_paras)), self.CHUNK_PARAGRAPHS):
                    batch = all_paras[i:i + self.CHUNK_PARAGRAPHS]
                    section_chunks.append((f"Section {len(section_chunks) + 1}", "\n\n".join(batch)))

            # Parse tables
            table_texts = []
            for t_idx, table in enumerate(doc.tables):
                t_rows = []
                for row in table.rows:
                    t_rows.append(" | ".join(cell.text.strip() for cell in row.cells))
                if t_rows:
                    table_md = f"Table {t_idx + 1}:\n" + "\n".join(t_rows[:50])
                    section_chunks.append((f"Table {t_idx + 1}", table_md))

            # Assemble DocumentChunks
            for idx, (sec_name, sec_content) in enumerate(section_chunks):
                if not sec_content.strip():
                    continue
                chunk_id = f"{file_id}_sec{idx + 1}"
                location = f"Section '{sec_name}' of {filename}"
                token_count = self._estimate_tokens(sec_content)

                chunk = DocumentChunk(
                    chunk_id=chunk_id,
                    file_id=file_id,
                    source=filename,
                    location=location,
                    section=sec_name,
                    content=sec_content,
                    token_count=token_count,
                    metadata={"section_index": idx + 1, "heading": sec_name}
                )
                chunks.append(chunk)
                citations.append(location)

            total_tokens = sum(c.token_count for c in chunks)
            summary = f"Word document '{filename}' with {len(doc.paragraphs)} paragraphs, {len(doc.tables)} tables, ~{total_tokens} tokens."

            return FileAnalysisResult(
                file_id=file_id,
                filename=filename,
                capability=self.capability,
                state=FileProcessingState.READY,
                summary=summary,
                chunks=chunks,
                total_tokens=total_tokens,
                metadata={"paragraphs": len(doc.paragraphs), "tables": len(doc.tables)},
                citations=citations
            )

        except Exception as e:
            logger.error(f"Error parsing DOCX file: {e}")
            return FileAnalysisResult(
                file_id=file_id,
                filename=filename,
                capability=self.capability,
                state=FileProcessingState.FAILED,
                error=f"Error reading Word document: {str(e)}"
            )
