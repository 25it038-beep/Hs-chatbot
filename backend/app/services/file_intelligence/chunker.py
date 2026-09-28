"""
HSBot General Chat — Structure-Aware Chunker (V2)
Preserves natural document structure (pages, headings, slides, sheets, code symbols/line ranges).
"""
import re
from typing import Optional, Any
from app.services.file_intelligence.models import (
    FileChunk,
    FileChunkMetadata,
    FILE_LIMITS,
)


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // 4)


class StructureAwareChunker:
    """Chunks documents by their semantic/structural boundaries rather than arbitrary character slices."""

    @staticmethod
    def chunk_pdf_pages(
        file_id: str,
        filename: str,
        pages_data: list[dict[str, Any]],
        max_chars_per_chunk: int = 2400,
    ) -> list[FileChunk]:
        chunks: list[FileChunk] = []
        pos = 0
        for p in pages_data:
            page_num = p["page"]
            text = (p.get("text") or "").strip()
            if not text:
                continue
            headings = p.get("headings") or []
            section_label = headings[0] if headings else f"Page {page_num}"

            if len(text) <= max_chars_per_chunk:
                cid = f"{file_id}_p{page_num}_0"
                chunks.append(
                    FileChunk(
                        chunkId=cid,
                        fileId=file_id,
                        filename=filename,
                        text=f"[Page {page_num} | {section_label}]\n{text}",
                        tokenEstimate=estimate_tokens(text) + 12,
                        metadata=FileChunkMetadata(
                            chunkId=cid,
                            fileId=file_id,
                            filename=filename,
                            sourceType="pdf",
                            page=page_num,
                            section=section_label,
                            position=pos,
                        ),
                    )
                )
                pos += 1
            else:
                paragraphs = [para.strip() for para in re.split(r"\n\s*\n", text) if para.strip()]
                buf: list[str] = []
                buf_len = 0
                sub_idx = 0
                for para in paragraphs:
                    if buf and (buf_len + len(para) > max_chars_per_chunk):
                        block = "\n\n".join(buf)
                        cid = f"{file_id}_p{page_num}_{sub_idx}"
                        chunks.append(
                            FileChunk(
                                chunkId=cid,
                                fileId=file_id,
                                filename=filename,
                                text=f"[Page {page_num} | {section_label}]\n{block}",
                                tokenEstimate=estimate_tokens(block) + 12,
                                metadata=FileChunkMetadata(
                                    chunkId=cid,
                                    fileId=file_id,
                                    filename=filename,
                                    sourceType="pdf",
                                    page=page_num,
                                    section=section_label,
                                    position=pos,
                                ),
                            )
                        )
                        pos += 1
                        sub_idx += 1
                        buf = [para]
                        buf_len = len(para)
                    else:
                        buf.append(para)
                        buf_len += len(para)
                if buf:
                    block = "\n\n".join(buf)
                    cid = f"{file_id}_p{page_num}_{sub_idx}"
                    chunks.append(
                        FileChunk(
                            chunkId=cid,
                            fileId=file_id,
                            filename=filename,
                            text=f"[Page {page_num} | {section_label}]\n{block}",
                            tokenEstimate=estimate_tokens(block) + 12,
                            metadata=FileChunkMetadata(
                                chunkId=cid,
                                fileId=file_id,
                                filename=filename,
                                sourceType="pdf",
                                page=page_num,
                                section=section_label,
                                position=pos,
                            ),
                        )
                    )
                    pos += 1
            if len(chunks) >= FILE_LIMITS.MAX_CHUNKS_PER_FILE:
                break
        return chunks

    @staticmethod
    def chunk_docx_sections(
        file_id: str,
        filename: str,
        sections: list[dict[str, Any]],
        max_chars_per_chunk: int = 2400,
    ) -> list[FileChunk]:
        chunks: list[FileChunk] = []
        pos = 0
        for s_idx, sec in enumerate(sections):
            heading = sec.get("heading") or f"Section {s_idx + 1}"
            content = (sec.get("content") or "").strip()
            if not content:
                continue
            if len(content) <= max_chars_per_chunk:
                cid = f"{file_id}_sec{s_idx}_0"
                full_block = f"[Section: {heading}]\n{content}"
                chunks.append(
                    FileChunk(
                        chunkId=cid,
                        fileId=file_id,
                        filename=filename,
                        text=full_block,
                        tokenEstimate=estimate_tokens(full_block),
                        metadata=FileChunkMetadata(
                            chunkId=cid,
                            fileId=file_id,
                            filename=filename,
                            sourceType="docx",
                            section=heading,
                            position=pos,
                        ),
                    )
                )
                pos += 1
            else:
                paras = [p.strip() for p in content.splitlines() if p.strip()]
                buf: list[str] = []
                buf_len = 0
                sub = 0
                for p in paras:
                    if buf and buf_len + len(p) > max_chars_per_chunk:
                        block = f"[Section: {heading}]\n" + "\n".join(buf)
                        cid = f"{file_id}_sec{s_idx}_{sub}"
                        chunks.append(
                            FileChunk(
                                chunkId=cid,
                                fileId=file_id,
                                filename=filename,
                                text=block,
                                tokenEstimate=estimate_tokens(block),
                                metadata=FileChunkMetadata(
                                    chunkId=cid,
                                    fileId=file_id,
                                    filename=filename,
                                    sourceType="docx",
                                    section=heading,
                                    position=pos,
                                ),
                            )
                        )
                        pos += 1
                        sub += 1
                        buf = [p]
                        buf_len = len(p)
                    else:
                        buf.append(p)
                        buf_len += len(p)
                if buf:
                    block = f"[Section: {heading}]\n" + "\n".join(buf)
                    cid = f"{file_id}_sec{s_idx}_{sub}"
                    chunks.append(
                        FileChunk(
                            chunkId=cid,
                            fileId=file_id,
                            filename=filename,
                            text=block,
                            tokenEstimate=estimate_tokens(block),
                            metadata=FileChunkMetadata(
                                chunkId=cid,
                                fileId=file_id,
                                filename=filename,
                                sourceType="docx",
                                section=heading,
                                position=pos,
                            ),
                        )
                    )
                    pos += 1
        return chunks[: FILE_LIMITS.MAX_CHUNKS_PER_FILE]

    @staticmethod
    def chunk_spreadsheet_sheets(
        file_id: str,
        filename: str,
        source_type: str,
        sheets_data: list[dict[str, Any]],
        rows_per_chunk: int = 40,
    ) -> list[FileChunk]:
        chunks: list[FileChunk] = []
        pos = 0
        for s in sheets_data:
            sheet_name = s["sheet_name"]
            headers = s["headers"]
            col_letters = s["column_letters"]
            rows = s["rows"]
            summary_text = s.get("summary_text", "")
            last_col = col_letters[-1] if col_letters else "A"

            # Chunk 0 for each sheet: Schema + Precomputed Column Statistics & Formulas
            sum_cid = f"{file_id}_{sheet_name}_summary"
            chunks.append(
                FileChunk(
                    chunkId=sum_cid,
                    fileId=file_id,
                    filename=filename,
                    text=summary_text,
                    tokenEstimate=estimate_tokens(summary_text),
                    metadata=FileChunkMetadata(
                        chunkId=sum_cid,
                        fileId=file_id,
                        filename=filename,
                        sourceType=source_type,
                        sheet=sheet_name,
                        section=f"{sheet_name} Schema & Totals",
                        cellRange=f"A1:{last_col}{len(rows) + 1}",
                        rowStart=1,
                        rowEnd=len(rows) + 1,
                        position=pos,
                    ),
                )
            )
            pos += 1

            # Row batch chunks with exact Excel coordinates (e.g., A2:F41)
            for start_idx in range(0, len(rows), rows_per_chunk):
                batch = rows[start_idx : start_idx + rows_per_chunk]
                excel_row_start = start_idx + 2  # Row 1 is header
                excel_row_end = start_idx + len(batch) + 1
                cell_range = f"A{excel_row_start}:{last_col}{excel_row_end}"

                lines = [
                    f"[Sheet: {sheet_name} | Rows {excel_row_start}–{excel_row_end} | Cells {cell_range}]",
                    "Headers: " + " | ".join(f"{col_letters[i]}:{headers[i]}" for i in range(len(headers))),
                ]
                for offset, r in enumerate(batch):
                    r_num = excel_row_start + offset
                    row_cells = [
                        f"{col_letters[c]}{r_num}({headers[c]})={r[c]}"
                        for c in range(min(len(r), len(headers)))
                        if str(r[c]).strip() != ""
                    ]
                    if row_cells:
                        lines.append(f"Row {r_num}: " + " | ".join(row_cells))

                block_text = "\n".join(lines)
                cid = f"{file_id}_{sheet_name}_r{excel_row_start}_{excel_row_end}"
                chunks.append(
                    FileChunk(
                        chunkId=cid,
                        fileId=file_id,
                        filename=filename,
                        text=block_text,
                        tokenEstimate=estimate_tokens(block_text),
                        metadata=FileChunkMetadata(
                            chunkId=cid,
                            fileId=file_id,
                            filename=filename,
                            sourceType=source_type,
                            sheet=sheet_name,
                            rowStart=excel_row_start,
                            rowEnd=excel_row_end,
                            cellRange=cell_range,
                            position=pos,
                        ),
                    )
                )
                pos += 1
                if len(chunks) >= FILE_LIMITS.MAX_CHUNKS_PER_FILE:
                    return chunks
        return chunks

    @staticmethod
    def chunk_pptx_slides(
        file_id: str,
        filename: str,
        slides_data: list[dict[str, Any]],
    ) -> list[FileChunk]:
        chunks: list[FileChunk] = []
        for pos, s in enumerate(slides_data):
            slide_num = s["slide"]
            title = s.get("title") or f"Slide {slide_num}"
            text = s.get("text") or ""
            cid = f"{file_id}_slide_{slide_num}"
            chunks.append(
                FileChunk(
                    chunkId=cid,
                    fileId=file_id,
                    filename=filename,
                    text=text,
                    tokenEstimate=estimate_tokens(text),
                    metadata=FileChunkMetadata(
                        chunkId=cid,
                        fileId=file_id,
                        filename=filename,
                        sourceType="pptx",
                        slide=slide_num,
                        section=title,
                        position=pos,
                    ),
                )
            )
        return chunks[: FILE_LIMITS.MAX_CHUNKS_PER_FILE]

    @staticmethod
    def chunk_code_file(
        file_id: str,
        filename: str,
        code_text: str,
        language: str,
        inner_path: Optional[str] = None,
        lines_per_chunk: int = 80,
    ) -> list[FileChunk]:
        lines = code_text.splitlines()
        if not lines:
            return []

        chunks: list[FileChunk] = []
        pos = 0
        display_path = inner_path or filename

        for start in range(0, len(lines), lines_per_chunk):
            batch = lines[start : start + lines_per_chunk]
            line_start = start + 1
            line_end = start + len(batch)

            # Detect functions/classes inside this line window for symbol metadata
            block_raw = "\n".join(batch)
            syms = re.findall(
                r"(?:def|function|class|interface|struct|fn)\s+([A-Za-z_][A-Za-z0-9_]*)",
                block_raw,
            )
            sec_label = f"Symbols: {', '.join(syms[:5])}" if syms else f"Lines {line_start}–{line_end}"

            numbered_lines = [f"{line_start + i}: {l}" for i, l in enumerate(batch)]
            header = f"[Code File: {display_path} ({language}) | Lines {line_start}–{line_end}]"
            full_text = header + "\n" + "\n".join(numbered_lines)

            cid = f"{file_id}_{re.sub(r'[^a-zA-Z0-9]', '_', display_path)}_{line_start}_{line_end}"
            chunks.append(
                FileChunk(
                    chunkId=cid,
                    fileId=file_id,
                    filename=filename,
                    text=full_text,
                    tokenEstimate=estimate_tokens(full_text),
                    metadata=FileChunkMetadata(
                        chunkId=cid,
                        fileId=file_id,
                        filename=filename,
                        sourceType="code",
                        section=sec_label,
                        lineStart=line_start,
                        lineEnd=line_end,
                        innerPath=inner_path,
                        position=pos,
                    ),
                )
            )
            pos += 1
            if len(chunks) >= FILE_LIMITS.MAX_CHUNKS_PER_FILE:
                break
        return chunks

    @staticmethod
    def chunk_text_or_markdown(
        file_id: str,
        filename: str,
        text: str,
        source_type: str = "txt",
        inner_path: Optional[str] = None,
        max_chars: int = 2400,
    ) -> list[FileChunk]:
        if not text or not text.strip():
            return []

        lines = text.splitlines()
        sections: list[tuple[str, int, int, str]] = []
        curr_heading = "Document Start"
        curr_lines: list[str] = []
        sec_start_line = 1

        for idx, line in enumerate(lines, start=1):
            m = re.match(r"^(#{1,6})\s+(.+)$", line.strip())
            if m:
                if curr_lines:
                    sections.append((curr_heading, sec_start_line, idx - 1, "\n".join(curr_lines)))
                curr_heading = m.group(2).strip()
                curr_lines = [line]
                sec_start_line = idx
            else:
                curr_lines.append(line)

        if curr_lines:
            sections.append((curr_heading, sec_start_line, len(lines), "\n".join(curr_lines)))

        chunks: list[FileChunk] = []
        pos = 0
        display_name = inner_path or filename

        for heading, l_start, l_end, sec_text in sections:
            if len(sec_text) <= max_chars:
                cid = f"{file_id}_txt_{pos}"
                chunks.append(
                    FileChunk(
                        chunkId=cid,
                        fileId=file_id,
                        filename=filename,
                        text=f"[{display_name} | {heading} | Lines {l_start}–{l_end}]\n{sec_text}",
                        tokenEstimate=estimate_tokens(sec_text) + 12,
                        metadata=FileChunkMetadata(
                            chunkId=cid,
                            fileId=file_id,
                            filename=filename,
                            sourceType=source_type,
                            section=heading,
                            lineStart=l_start,
                            lineEnd=l_end,
                            innerPath=inner_path,
                            position=pos,
                        ),
                    )
                )
                pos += 1
            else:
                sec_lines = sec_text.splitlines()
                step = 60
                for offset in range(0, len(sec_lines), step):
                    sub_lines = sec_lines[offset : offset + step]
                    sub_start = l_start + offset
                    sub_end = sub_start + len(sub_lines) - 1
                    sub_block = "\n".join(sub_lines)
                    cid = f"{file_id}_txt_{pos}"
                    chunks.append(
                        FileChunk(
                            chunkId=cid,
                            fileId=file_id,
                            filename=filename,
                            text=f"[{display_name} | {heading} | Lines {sub_start}–{sub_end}]\n{sub_block}",
                            tokenEstimate=estimate_tokens(sub_block) + 12,
                            metadata=FileChunkMetadata(
                                chunkId=cid,
                                fileId=file_id,
                                filename=filename,
                                sourceType=source_type,
                                section=heading,
                                lineStart=sub_start,
                                lineEnd=sub_end,
                                innerPath=inner_path,
                                position=pos,
                            ),
                        )
                    )
                    pos += 1
            if len(chunks) >= FILE_LIMITS.MAX_CHUNKS_PER_FILE:
                break
        return chunks
