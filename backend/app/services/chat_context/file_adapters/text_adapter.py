import os
import re
import logging
from typing import Dict, List, Optional, Any
from app.services.chat_context.contracts import (
    FileCapability,
    FileProcessingState,
    DocumentChunk,
    FileAnalysisResult
)
from app.services.chat_context.file_adapters.base import BaseFileAdapter

logger = logging.getLogger("hsbot.chat_context.text")


class TextAdapter(BaseFileAdapter):
    capability = FileCapability.TEXT
    supported_extensions = [
        ".txt", ".md", ".markdown", ".rst", ".log", ".text",
        ".env", ".ini", ".cfg", ".conf", ".rtf"
    ]
    supported_mimes = [
        "text/plain", "text/markdown", "text/x-rst", "text/x-log"
    ]

    MAX_CHUNK_TOKENS = 600

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

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            if not content.strip():
                return FileAnalysisResult(
                    file_id=file_id,
                    filename=filename,
                    capability=self.capability,
                    state=FileProcessingState.READY,
                    summary=f"Empty text file '{filename}'.",
                    chunks=[],
                    total_tokens=0
                )

            lines = content.splitlines()
            total_lines = len(lines)
            chunks: List[DocumentChunk] = []
            citations: List[str] = []

            # Check if markdown with headers
            header_pattern = re.compile(r'^(#{1,6})\s+(.+)$')
            current_section_title = "Overview"
            current_lines = []
            current_start_line = 1

            sections = []

            for line_idx, line in enumerate(lines):
                line_num = line_idx + 1
                m = header_pattern.match(line)
                if m:
                    # Flush current buffer if non-empty
                    if current_lines:
                        sec_text = "\n".join(current_lines).strip()
                        if sec_text:
                            sections.append((current_section_title, current_start_line, line_num - 1, sec_text))
                    current_section_title = m.group(2).strip()
                    current_start_line = line_num
                    current_lines = [line]
                else:
                    current_lines.append(line)
                    # If buffer is getting too long (> 3000 chars and at an empty line), flush as sub-section
                    if len("\n".join(current_lines)) > 2500 and not line.strip():
                        sec_text = "\n".join(current_lines).strip()
                        if sec_text:
                            sections.append((current_section_title, current_start_line, line_num, sec_text))
                        current_start_line = line_num + 1
                        current_lines = []

            if current_lines:
                sec_text = "\n".join(current_lines).strip()
                if sec_text:
                    sections.append((current_section_title, current_start_line, total_lines, sec_text))

            # If no markdown sections formed, split by paragraphs or line blocks
            if not sections:
                paragraphs = content.split("\n\n")
                buf = []
                p_start = 1
                curr_line_count = 0
                for p in paragraphs:
                    p = p.strip()
                    if not p:
                        continue
                    p_lines = p.count("\n") + 1
                    buf.append(p)
                    curr_line_count += p_lines
                    if len("\n\n".join(buf)) > 1500:
                        sec_text = "\n\n".join(buf)
                        sections.append((f"Lines {p_start}-{p_start + curr_line_count}", p_start, p_start + curr_line_count, sec_text))
                        p_start += curr_line_count + 1
                        buf = []
                        curr_line_count = 0
                if buf:
                    sec_text = "\n\n".join(buf)
                    sections.append((f"Lines {p_start}-{p_start + curr_line_count}", p_start, p_start + curr_line_count, sec_text))

            # Assemble DocumentChunks
            for idx, (sec_name, start_l, end_l, sec_content) in enumerate(sections):
                chunk_id = f"{file_id}_sec{idx + 1}"
                location = f"'{sec_name}' (Lines {start_l}-{end_l}) of {filename}"
                token_count = self._estimate_tokens(sec_content)

                chunk = DocumentChunk(
                    chunk_id=chunk_id,
                    file_id=file_id,
                    source=filename,
                    location=location,
                    section=sec_name,
                    start_line=start_l,
                    end_line=end_l,
                    content=f"### {filename} - {sec_name}:\n{sec_content}",
                    token_count=token_count,
                    metadata={"section": sec_name, "start_line": start_l, "end_line": end_l}
                )
                chunks.append(chunk)
                citations.append(location)

            total_tokens = sum(c.token_count for c in chunks)
            summary = f"Text document: '{filename}' ({total_lines} lines, {len(chunks)} sections, ~{total_tokens} tokens)."

            return FileAnalysisResult(
                file_id=file_id,
                filename=filename,
                capability=self.capability,
                state=FileProcessingState.READY,
                summary=summary,
                chunks=chunks,
                total_tokens=total_tokens,
                metadata={"total_lines": total_lines, "section_count": len(chunks)},
                citations=citations
            )

        except Exception as e:
            logger.error(f"Error parsing text file {filename}: {e}")
            return FileAnalysisResult(
                file_id=file_id,
                filename=filename,
                capability=self.capability,
                state=FileProcessingState.FAILED,
                error=f"Error reading text document: {str(e)}"
            )
