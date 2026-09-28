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

logger = logging.getLogger("hsbot.chat_context.code")


class CodeAdapter(BaseFileAdapter):
    capability = FileCapability.CODE
    supported_extensions = [
        ".py", ".ts", ".tsx", ".js", ".jsx", ".java", ".cpp", ".c", ".h", ".hpp",
        ".cs", ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".scala", ".sh",
        ".bash", ".zsh", ".ps1", ".sql", ".html", ".css", ".scss", ".less",
        ".vue", ".svelte", ".proto", ".graphql", ".gql", ".lua", ".r", ".dart",
        ".yaml", ".yml", ".json", ".toml"
    ]
    supported_mimes = [
        "text/x-python", "application/javascript", "text/javascript",
        "text/typescript", "text/x-c", "text/x-java-source", "text/x-sh",
        "application/json", "application/x-yaml", "text/x-sql"
    ]

    CHUNK_LINES = 60
    OVERLAP_LINES = 5

    def _estimate_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)

    def _detect_definitions(self, lines: List[str]) -> List[str]:
        defs = []
        pattern = re.compile(
            r'^\s*(def |class |async def |function |const |export default |public class |private |protected |fn |func |type |interface |struct )\s*([a-zA-Z0-9_]+)'
        )
        for line in lines:
            m = pattern.search(line)
            if m:
                defs.append(m.group(2))
        return defs[:10]

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
                raw_lines = f.readlines()

            total_lines = len(raw_lines)
            if total_lines == 0:
                return FileAnalysisResult(
                    file_id=file_id,
                    filename=filename,
                    capability=self.capability,
                    state=FileProcessingState.READY,
                    summary=f"Empty code file '{filename}'.",
                    chunks=[],
                    total_tokens=0
                )

            chunks: List[DocumentChunk] = []
            citations: List[str] = []
            all_defs: List[str] = []
            ext = os.path.splitext(filename)[1].lower()

            start_idx = 0
            chunk_num = 1

            while start_idx < total_lines:
                end_idx = min(start_idx + self.CHUNK_LINES, total_lines)
                batch_lines = raw_lines[start_idx:end_idx]
                chunk_defs = self._detect_definitions(batch_lines)
                all_defs.extend(chunk_defs)

                line_start_num = start_idx + 1
                line_end_num = end_idx

                header_label = f"Lines {line_start_num}-{line_end_num}"
                if chunk_defs:
                    header_label += f" ({', '.join(chunk_defs[:3])})"

                # Format code with line numbers for reference
                numbered_lines = []
                for offset, line_content in enumerate(batch_lines):
                    curr_num = line_start_num + offset
                    numbered_lines.append(f"{curr_num:4d} | {line_content.rstrip()}")

                code_block = (
                    f"### `{filename}` [{header_label}]:\n"
                    f"```{ext.lstrip('.')}\n"
                    + "\n".join(numbered_lines)
                    + "\n```"
                )

                chunk_id = f"{file_id}_L{line_start_num}-{line_end_num}"
                location = f"Lines {line_start_num}-{line_end_num} of {filename}"
                token_count = self._estimate_tokens(code_block)

                chunk = DocumentChunk(
                    chunk_id=chunk_id,
                    file_id=file_id,
                    source=filename,
                    location=location,
                    section=header_label,
                    start_line=line_start_num,
                    end_line=line_end_num,
                    content=code_block,
                    token_count=token_count,
                    metadata={
                        "language": ext.lstrip("."),
                        "definitions": chunk_defs,
                        "start_line": line_start_num,
                        "end_line": line_end_num
                    }
                )
                chunks.append(chunk)
                citations.append(location)

                if end_idx >= total_lines:
                    break
                start_idx += (self.CHUNK_LINES - self.OVERLAP_LINES)
                chunk_num += 1

            total_tokens = sum(c.token_count for c in chunks)
            unique_defs = list(dict.fromkeys(all_defs))
            summary = f"Code file: '{filename}' ({total_lines} lines, {len(chunks)} chunks, ~{total_tokens} tokens)."
            if unique_defs:
                summary += f"\nSymbols: {', '.join(unique_defs[:15])}"

            return FileAnalysisResult(
                file_id=file_id,
                filename=filename,
                capability=self.capability,
                state=FileProcessingState.READY,
                summary=summary,
                chunks=chunks,
                total_tokens=total_tokens,
                metadata={"total_lines": total_lines, "definitions": unique_defs},
                citations=citations
            )

        except Exception as e:
            logger.error(f"Error parsing code file {filename}: {e}")
            return FileAnalysisResult(
                file_id=file_id,
                filename=filename,
                capability=self.capability,
                state=FileProcessingState.FAILED,
                error=f"Error reading code file: {str(e)}"
            )
