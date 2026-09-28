import os
import zipfile
import tarfile
import logging
from typing import Dict, List, Optional, Any
from app.services.chat_context.contracts import (
    FileCapability,
    FileProcessingState,
    DocumentChunk,
    FileAnalysisResult
)
from app.services.chat_context.file_adapters.base import BaseFileAdapter

logger = logging.getLogger("hsbot.chat_context.archive")


class ArchiveAdapter(BaseFileAdapter):
    capability = FileCapability.ARCHIVE
    supported_extensions = [".zip", ".tar", ".gz", ".tgz", ".bz2", ".tbz2"]
    supported_mimes = [
        "application/zip", "application/x-zip-compressed", "application/x-tar",
        "application/gzip", "application/x-bzip2"
    ]

    MAX_INSPECT_FILES = 200
    MAX_PREVIEW_BYTES = 4000

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
        chunks: List[DocumentChunk] = []
        citations: List[str] = []
        file_tree = []
        total_entries = 0
        total_uncompressed_size = 0

        try:
            if ext == ".zip":
                with zipfile.ZipFile(file_path, "r") as zf:
                    infolist = zf.infolist()
                    total_entries = len(infolist)
                    for info in infolist[:self.MAX_INSPECT_FILES]:
                        total_uncompressed_size += info.file_size
                        prefix = "[DIR] " if info.is_dir() else f"[{info.file_size:>8} B] "
                        file_tree.append(f"{prefix}{info.filename}")

                    # Preview top text/readme file if exists
                    for info in infolist:
                        base = os.path.basename(info.filename).lower()
                        if not info.is_dir() and (base.startswith("readme") or base in ["package.json", "requirements.txt", "pyproject.toml"]):
                            try:
                                with zf.open(info) as item_file:
                                    snippet = item_file.read(self.MAX_PREVIEW_BYTES).decode("utf-8", errors="replace")
                                    p_chunk = DocumentChunk(
                                        chunk_id=f"{file_id}_preview_{base[:10]}",
                                        file_id=file_id,
                                        source=filename,
                                        location=f"File '{info.filename}' in {filename}",
                                        section=f"Archive Entry: {info.filename}",
                                        content=f"### Archive '{filename}' -> `{info.filename}`:\n```\n{snippet}\n```",
                                        token_count=self._estimate_tokens(snippet),
                                        metadata={"archive_path": info.filename}
                                    )
                                    chunks.append(p_chunk)
                                    citations.append(f"'{info.filename}' in {filename}")
                                    break
                            except Exception as e:
                                logger.warning(f"Failed to preview {info.filename} in zip: {e}")

            elif ext in [".tar", ".gz", ".tgz", ".bz2", ".tbz2"]:
                mode = "r:*" if ext != ".tar" else "r:"
                with tarfile.open(file_path, mode) as tf:
                    members = tf.getmembers()
                    total_entries = len(members)
                    for m in members[:self.MAX_INSPECT_FILES]:
                        total_uncompressed_size += m.size
                        prefix = "[DIR] " if m.isdir() else f"[{m.size:>8} B] "
                        file_tree.append(f"{prefix}{m.name}")

            # Create tree listing chunk
            tree_content = f"### Archive Directory Tree: `{filename}` ({total_entries} items, {total_uncompressed_size / 1024:.1f} KB uncompressed):\n```\n"
            tree_content += "\n".join(file_tree[:100])
            if total_entries > 100:
                tree_content += f"\n... and {total_entries - 100} more items."
            tree_content += "\n```"

            loc = f"Archive structure of {filename}"
            tree_chunk = DocumentChunk(
                chunk_id=f"{file_id}_tree",
                file_id=file_id,
                source=filename,
                location=loc,
                section="Archive Structure",
                content=tree_content,
                token_count=self._estimate_tokens(tree_content),
                metadata={"total_entries": total_entries, "uncompressed_bytes": total_uncompressed_size}
            )
            chunks.insert(0, tree_chunk)
            citations.append(loc)

            total_tokens = sum(c.token_count for c in chunks)
            summary = f"Archive: '{filename}' containing {total_entries} files/folders (~{total_uncompressed_size / 1024:.1f} KB uncompressed)."

            return FileAnalysisResult(
                file_id=file_id,
                filename=filename,
                capability=self.capability,
                state=FileProcessingState.READY,
                summary=summary,
                chunks=chunks,
                total_tokens=total_tokens,
                metadata={"total_entries": total_entries, "uncompressed_size": total_uncompressed_size},
                citations=citations
            )

        except Exception as e:
            logger.error(f"Error inspecting archive {filename}: {e}")
            return FileAnalysisResult(
                file_id=file_id,
                filename=filename,
                capability=self.capability,
                state=FileProcessingState.FAILED,
                error=f"Error inspecting archive: {str(e)}"
            )
