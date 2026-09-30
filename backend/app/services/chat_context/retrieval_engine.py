import os
import json
import logging
from typing import Dict, List, Optional, Any, Set
from sqlalchemy import select, or_
from app.services.chat_context.contracts import (
    DocumentChunk,
    FileAnalysisResult,
    FileProcessingState,
    FileCapability,
)
from app.services.chat_context.budget import estimate_tokens
from app.services.chat_context.file_adapters.registry import file_adapter_registry
from app.services.chat_context.ranker import chunk_ranker
from app.database import async_session
from app.models.file import GeneratedFile
from app.services.rag import RAGService

logger = logging.getLogger("hsbot.chat_context.retrieval")


class FileRetrievalEngineV2:
    """
    Production-grade file knowledge retriever for General Chat.
    Resolves files across current attachments, conversation history, and explicit user mentions.
    Delivers real, structured document content with verifiable source citations.
    """

    async def resolve_active_files(
        self,
        user_id: str,
        chat_id: Optional[str] = None,
        file_ids: Optional[List[str]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        message: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Resolves all relevant files for the current turn:
        1. Files explicitly provided in request (file_ids or attachments)
        2. Files associated with this conversation in the database
        3. Files mentioned by name in the user prompt
        """
        active_files_dict: Dict[str, Dict[str, Any]] = {}

        # 1. From request attachments / file_ids
        if attachments:
            for att in attachments:
                fid = att.get("file_id") or att.get("id") or f"att_{len(active_files_dict)}"
                active_files_dict[fid] = {
                    "id": fid,
                    "file_id": fid,
                    "filename": att.get("filename") or att.get("name") or "file",
                    "mime_type": att.get("mime_type") or att.get("type"),
                    "storage_path": att.get("storage_path") or att.get("file_path") or att.get("path"),
                    "chunks_path": att.get("chunks_path"),
                    "text": att.get("text") or att.get("content"),
                    "status": att.get("status", "READY")
                }

        if file_ids:
            async with async_session() as session:
                stmt = select(GeneratedFile).where(
                    GeneratedFile.id.in_(file_ids),
                    or_(GeneratedFile.user_id == user_id, GeneratedFile.user_id == "default_user_id")
                )
                res = await session.execute(stmt)
                for f_record in res.scalars().all():
                    active_files_dict[f_record.id] = {
                        "id": f_record.id,
                        "file_id": f_record.id,
                        "filename": f_record.filename,
                        "mime_type": f_record.mime_type,
                        "storage_path": f_record.storage_path,
                        "chunks_path": f_record.chunks_path,
                        "status": f_record.status
                    }

        # 2. From conversation association in database
        if chat_id:
            async with async_session() as session:
                stmt = select(GeneratedFile).where(
                    GeneratedFile.conversation_id == chat_id,
                    or_(GeneratedFile.user_id == user_id, GeneratedFile.user_id == "default_user_id")
                ).order_by(GeneratedFile.created_at.desc())
                res = await session.execute(stmt)
                for f_record in res.scalars().all():
                    if f_record.id not in active_files_dict:
                        active_files_dict[f_record.id] = {
                            "id": f_record.id,
                            "file_id": f_record.id,
                            "filename": f_record.filename,
                            "mime_type": f_record.mime_type,
                            "storage_path": f_record.storage_path,
                            "chunks_path": f_record.chunks_path,
                            "status": f_record.status
                        }

        # 3. From in-memory RAG cache
        # If files were already resolved from current attachments or current chat,
        # avoid pulling unrelated files from previous chats unless explicitly mentioned in prompt.
        cached_files = RAGService.get_cached_files(user_id)
        msg_lower = message.lower()
        for cf in cached_files:
            cf_id = cf.get("file_id") or cf.get("filename")
            cf_fn = (cf.get("filename") or "").lower()
            should_include = (not active_files_dict) or (cf_fn and cf_fn in msg_lower)
            if should_include and cf_id not in active_files_dict:
                active_files_dict[cf_id] = {
                    "id": cf_id,
                    "file_id": cf_id,
                    "filename": cf.get("filename"),
                    "storage_path": cf.get("file_path") or cf.get("storage_path"),
                    "mime_type": cf.get("mime_type", "application/octet-stream"),
                    "text": cf.get("text"),
                    "status": "READY"
                }

        # 4. Check explicit filename mentions in prompt
        # e.g., if user says "in report.pdf" or "look at data.xlsx"
        msg_lower = message.lower()
        for f_data in active_files_dict.values():
            fn = f_data.get("filename", "").lower()
            if fn and fn in msg_lower:
                f_data["explicitly_mentioned"] = True

        return list(active_files_dict.values())

    async def load_processed_file(self, file_info: Dict[str, Any]) -> FileAnalysisResult:
        """
        Loads pre-computed structured chunks from disk if available,
        or extracts them via FileAdapterRegistryV2.
        """
        file_id = str(file_info.get("file_id") or file_info.get("id") or "file")
        filename = file_info.get("filename") or file_info.get("name") or "document"
        storage_path = file_info.get("storage_path") or file_info.get("file_path") or file_info.get("path") or ""
        mime_type = file_info.get("mime_type") or file_info.get("type")
        chunks_path = file_info.get("chunks_path")

        # 1. Try reading pre-persisted chunks.json from disk
        if chunks_path and os.path.exists(chunks_path):
            try:
                with open(chunks_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                chunks = [DocumentChunk(**c) for c in data.get("chunks", [])]
                return FileAnalysisResult(
                    file_id=file_id,
                    filename=filename,
                    capability=FileCapability(data.get("capability", "DOCUMENT")),
                    state=FileProcessingState(data.get("state", "READY")),
                    summary=data.get("summary", ""),
                    chunks=chunks,
                    total_tokens=data.get("total_tokens", 0),
                    metadata=data.get("metadata", {}),
                    citations=data.get("citations", []),
                    is_partially_supported=data.get("is_partially_supported", False)
                )
            except Exception as e:
                logger.warning(f"Failed to read chunks file {chunks_path}: {e}")

        # 2. Extract using file adapter
        if storage_path and os.path.exists(storage_path):
            result = await file_adapter_registry.process_file(
                file_path=storage_path,
                filename=filename,
                file_id=file_id,
                mime_type=mime_type
            )
            # Persist processed chunks for future turns
            try:
                chunks_dir = os.path.dirname(storage_path)
                target_chunks_file = os.path.join(chunks_dir, f"{file_id}_chunks.json")
                with open(target_chunks_file, "w", encoding="utf-8") as f:
                    json.dump(result.to_dict(), f)
                file_info["chunks_path"] = target_chunks_file
            except Exception as e:
                logger.debug(f"Could not persist chunks json: {e}")

            return result

        # 3. Direct in-memory text support (e.g. from preview or test mocks)
        direct_text = file_info.get("text") or file_info.get("content")
        if direct_text:
            tokens = estimate_tokens(direct_text)
            lines_count = len(direct_text.splitlines())
            chunk = DocumentChunk(
                chunk_id=f"{file_id}_0",
                file_id=file_id,
                source=filename,
                location=f"'{filename}' (Lines 1-{lines_count})",
                section="Overview",
                start_line=1,
                end_line=lines_count,
                content=direct_text,
                token_count=tokens,
            )
            return FileAnalysisResult(
                file_id=file_id,
                filename=filename,
                capability=FileCapability.TEXT,
                state=FileProcessingState.READY,
                summary=direct_text[:300],
                chunks=[chunk],
                total_tokens=tokens,
                citations=[f"'{filename}' (Lines 1-{lines_count})"]
            )

        # Fallback if file missing
        return FileAnalysisResult(
            file_id=file_id,
            filename=filename,
            capability=FileCapability.OTHER,
            state=FileProcessingState.FAILED,
            error=f"Storage path not found: {storage_path}"
        )

    async def retrieve_relevant_context(
        self,
        user_id: str,
        chat_id: Optional[str],
        query: str,
        active_files: List[Dict[str, Any]],
        token_budget: int
    ) -> Dict[str, Any]:
        """
        Executes hierarchical document reasoning and BM25 chunk retrieval.
        Guarantees that real, structured content reaches the model.
        """
        if not active_files:
            return {"chunks": [], "context_text": "", "citations": [], "files_used": []}

        all_analysis: List[FileAnalysisResult] = []
        all_chunks: List[DocumentChunk] = []

        for f_info in active_files:
            analysis = await self.load_processed_file(f_info)
            all_analysis.append(analysis)
            all_chunks.extend(analysis.chunks)

        if not all_chunks:
            # Files existed but contained zero extractable chunks
            summaries = [f"- **{a.filename}**: {a.summary or a.error or 'No text content.'}" for a in all_analysis]
            summary_block = "### Attached Files:\n" + "\n".join(summaries)
            return {
                "chunks": [],
                "context_text": f"\n\n==================== ATTACHED FILE CONTEXT ====================\n{summary_block}\n================================================================",
                "citations": [],
                "files_used": [a.filename for a in all_analysis]
            }

        # Select top chunks fitting the token budget
        selected_chunks = chunk_ranker.select_top_chunks(
            chunks=all_chunks,
            query=query,
            token_budget=token_budget
        )

        citations: List[str] = []
        files_used_set: Set[str] = set()
        for c in selected_chunks:
            citations.append(c.location)
            files_used_set.add(c.source)

        # Build clean hierarchical prompt context
        file_inventory_lines = []
        for a in all_analysis:
            file_inventory_lines.append(f"- **{a.filename}** ({a.capability.value}): {a.summary}")

        extracted_evidence_lines = []
        for c in selected_chunks:
            extracted_evidence_lines.append(f"[{c.location}]:\n{c.content}")

        context_text = (
            f"\n\n==================== ATTACHED FILE CONTEXT ====================\n"
            f"### Active Documents in this Conversation:\n"
            + "\n".join(file_inventory_lines)
            + f"\n\n### Relevant Extracted Evidence (Citations Grounding):\n"
            + "\n\n".join(extracted_evidence_lines)
            + f"\n================================================================"
        )

        return {
            "chunks": selected_chunks,
            "context_text": context_text,
            "citations": list(dict.fromkeys(citations)),
            "files_used": list(files_used_set)
        }

    async def search_in_files(
        self,
        user_id: str,
        query: str,
        chat_id: Optional[str] = None,
        file_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Direct search inside uploaded files for explicit queries:
        e.g., 'Find all occurrences of revenue', 'where is the login function?'
        """
        active_files = await self.resolve_active_files(user_id=user_id, chat_id=chat_id, message=query)
        if file_id:
            active_files = [f for f in active_files if f["file_id"] == file_id]

        all_chunks: List[DocumentChunk] = []
        for f_info in active_files:
            analysis = await self.load_processed_file(f_info)
            all_chunks.extend(analysis.chunks)

        scored = chunk_ranker.score_chunks(all_chunks, query)
        matches = []
        for chunk, score in scored[:10]:
            if score > 0.5:
                matches.append({
                    "file_id": chunk.file_id,
                    "filename": chunk.source,
                    "location": chunk.location,
                    "section": chunk.section,
                    "page": chunk.page,
                    "sheet": chunk.sheet,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "content": chunk.content,
                    "score": round(score, 2)
                })

        return matches


file_retrieval_engine = FileRetrievalEngineV2()
