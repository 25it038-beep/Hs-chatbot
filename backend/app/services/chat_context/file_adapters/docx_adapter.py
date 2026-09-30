import os
import logging
from typing import Dict, List, Optional, Any, Tuple
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
            import re
            doc = docx.Document(file_path)

            # 1. Parse paragraphs with heuristic heading & question detection
            raw_sections: List[Tuple[str, List[str]]] = []
            current_section = "Introduction"
            current_buffer: List[str] = []

            for p in doc.paragraphs:
                txt = p.text.strip()
                if not txt:
                    continue

                is_heading = False
                if p.style and hasattr(p.style, "name") and p.style.name and p.style.name.startswith("Heading"):
                    is_heading = True
                elif len(txt) <= 80 and (
                    re.match(r"^(?:part\s+[a-z0-9]|unit\s+[a-z0-9]|module\s+[a-z0-9]|chapter\s+[a-z0-9]|section\s+[a-z0-9])", txt, re.I)
                    or (p.runs and any(r.bold for r in p.runs if r.text.strip()) and len(txt) < 50)
                ):
                    is_heading = True

                if is_heading:
                    if current_buffer:
                        raw_sections.append((current_section, current_buffer))
                        current_buffer = []
                    current_section = txt
                    current_buffer.append(f"## {txt}")
                else:
                    current_buffer.append(txt)

            if current_buffer:
                raw_sections.append((current_section, current_buffer))

            # 2. Break large sections into bounded chunks (max CHUNK_PARAGRAPHS paras)
            section_chunks: List[Tuple[str, str]] = []
            for sec_name, para_list in raw_sections:
                if not para_list:
                    continue
                if len(para_list) <= self.CHUNK_PARAGRAPHS:
                    section_chunks.append((sec_name, "\n\n".join(para_list)))
                else:
                    total_batches = (len(para_list) + self.CHUNK_PARAGRAPHS - 1) // self.CHUNK_PARAGRAPHS
                    for b_idx in range(total_batches):
                        batch = para_list[b_idx * self.CHUNK_PARAGRAPHS : (b_idx + 1) * self.CHUNK_PARAGRAPHS]
                        label = f"{sec_name} (Part {b_idx + 1})" if total_batches > 1 else sec_name
                        section_chunks.append((label, "\n\n".join(batch)))

            # If document had no paragraphs but had text in tables
            if not section_chunks and not doc.tables:
                all_raw = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
                if all_raw:
                    section_chunks.append(("Overview", "\n\n".join(all_raw)))

            # 3. Parse tables (questions and data often reside in Word tables)
            for t_idx, table in enumerate(doc.tables):
                t_rows = []
                for row in table.rows:
                    cells = [cell.text.strip() for cell in row.cells]
                    # Deduplicate adjacent identical cells from merged cells
                    deduped = []
                    for c in cells:
                        if not deduped or c != deduped[-1]:
                            deduped.append(c)
                    row_line = " | ".join(deduped)
                    if row_line.strip():
                        t_rows.append(row_line)

                if t_rows:
                    t_batch_size = 20
                    total_t_batches = (len(t_rows) + t_batch_size - 1) // t_batch_size
                    for b_idx in range(total_t_batches):
                        batch = t_rows[b_idx * t_batch_size : (b_idx + 1) * t_batch_size]
                        label = f"Table {t_idx + 1}" + (f" (Part {b_idx + 1})" if total_t_batches > 1 else "")
                        table_md = f"### {label}:\n" + "\n".join(batch)
                        section_chunks.append((label, table_md))

            # 4. Assemble DocumentChunks
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
            summary = f"Word document '{filename}' with {len(doc.paragraphs)} paragraphs, {len(doc.tables)} tables, {len(chunks)} sections (~{total_tokens} tokens)."

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
