"""
HSBot General Chat — File Storage, Hash Cache, Lifecycle & Controlled Content API (V2)
Separates original file storage from processed representation, enforces strict user ownership,
prevents duplicate processing via SHA-256 + parserVersion cache, and never exposes raw server paths.
"""
import os
import re
import json
import uuid
import asyncio
import aiofiles
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Any
from fastapi import UploadFile, HTTPException
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.file import GeneratedFile
from app.services.file_intelligence.models import (
    FileProcessingState,
    ProcessedFileRepresentation,
    FileChunk,
    FILE_LIMITS,
    PARSER_VERSION,
)
from app.services.file_intelligence.security import sanitize_filename, compute_sha256_file
from app.services.file_intelligence.adapters import FileAdapterRegistryV2
from app.services.file_intelligence.spreadsheet_calc import SpreadsheetCalculator


# In-memory fast LRU cache keyed by (user_id, file_id) -> ProcessedFileRepresentation
_MEMORY_REP_CACHE: dict[tuple[str, str], ProcessedFileRepresentation] = {}
# Track in-flight processing tasks so Upload + Immediate Send waits cleanly (Section 38)
_INFLIGHT_TASKS: dict[str, asyncio.Event] = {}


class FileStorageManagerV2:
    """Manages original files, processed representations, hash-based deduplication, and authorized access."""

    @staticmethod
    def _user_base_dir(user_id: str) -> Path:
        safe_uid = re.sub(r"[^a-zA-Z0-9_\-@.]", "_", str(user_id))
        base = Path(settings.upload_dir) / "users" / safe_uid
        (base / "uploads").mkdir(parents=True, exist_ok=True)
        (base / "processed").mkdir(parents=True, exist_ok=True)
        (base / "cache").mkdir(parents=True, exist_ok=True)
        return base

    @classmethod
    def get_original_dir(cls, user_id: str) -> Path:
        return cls._user_base_dir(user_id) / "uploads"

    @classmethod
    def get_processed_path(cls, user_id: str, file_id: str) -> Path:
        safe_fid = re.sub(r"[^a-zA-Z0-9_\-]", "", str(file_id))
        return cls._user_base_dir(user_id) / "processed" / f"{safe_fid}.json"

    @classmethod
    def get_hash_cache_path(cls, user_id: str, content_hash: str) -> Path:
        safe_hash = re.sub(r"[^a-fA-F0-9]", "", content_hash)
        ver = PARSER_VERSION.replace(".", "_")
        return cls._user_base_dir(user_id) / "cache" / f"{safe_hash}_v{ver}.json"

    @classmethod
    async def save_upload_stream_and_process(
        cls,
        upload_file: UploadFile,
        user_id: str,
        db: AsyncSession,
        conversation_id: Optional[str] = None,
        message_id: Optional[str] = None,
        file_id: Optional[str] = None,
    ) -> ProcessedFileRepresentation:
        """
        Stream-writes an uploaded file to disk with bounded memory, validates size limits,
        checks SHA-256 content cache, runs FileAdapterRegistryV2, and persists both DB record
        and processed representation on disk.
        """
        fid = file_id or str(uuid.uuid4())
        inflight_ev = asyncio.Event()
        _INFLIGHT_TASKS[fid] = inflight_ev

        try:
            clean_name = sanitize_filename(upload_file.filename or "unknown")
            ext = os.path.splitext(clean_name)[1] or ".bin"
            safe_disk_name = f"{fid}{ext}"
            orig_dir = cls.get_original_dir(user_id)
            orig_path = orig_dir / safe_disk_name

            max_bytes = min(settings.max_file_size_mb * 1024 * 1024, FILE_LIMITS.MAX_FILE_SIZE)
            total_written = 0

            # Stream in 64KB chunks so large files never blow up backend RAM
            async with aiofiles.open(orig_path, "wb") as out_f:
                while True:
                    chunk = await upload_file.read(65536)
                    if not chunk:
                        break
                    total_written += len(chunk)
                    if total_written > max_bytes:
                        await out_f.close()
                        try:
                            orig_path.unlink(missing_ok=True)
                        except Exception:
                            pass
                        raise HTTPException(
                            status_code=413,
                            detail=f"File '{clean_name}' exceeds the {max_bytes // (1024 * 1024)}MB size limit.",
                        )
                    await out_f.write(chunk)

            if total_written == 0:
                try:
                    orig_path.unlink(missing_ok=True)
                except Exception:
                    pass
                rep = ProcessedFileRepresentation(
                    fileId=fid,
                    userId=str(user_id),
                    conversationId=conversation_id,
                    messageId=message_id,
                    filename=clean_name,
                    mimeType=upload_file.content_type or "application/octet-stream",
                    detectedFormat="empty",
                    extension=ext.lstrip("."),
                    size=0,
                    contentHash="",
                    parserName="EmptyFileValidator",
                    status=FileProcessingState.FAILED,
                    processingStage="Failed",
                    error="Uploaded file is empty (0 bytes).",
                    createdAt=datetime.now(timezone.utc).isoformat(),
                )
                await cls._persist_representation(db, rep, str(orig_path))
                return rep

            return await cls.process_stored_file(
                orig_path=str(orig_path),
                file_id=fid,
                user_id=str(user_id),
                filename=clean_name,
                client_mime=upload_file.content_type,
                db=db,
                conversation_id=conversation_id,
                message_id=message_id,
            )
        finally:
            inflight_ev.set()
            _INFLIGHT_TASKS.pop(fid, None)

    @classmethod
    async def process_stored_file(
        cls,
        orig_path: str,
        file_id: str,
        user_id: str,
        filename: str,
        client_mime: Optional[str],
        db: AsyncSession,
        conversation_id: Optional[str] = None,
        message_id: Optional[str] = None,
        force_reprocess: bool = False,
    ) -> ProcessedFileRepresentation:
        """
        Process a file already on disk, reusing SHA-256 + parserVersion cache if unchanged.
        """
        content_hash = await asyncio.to_thread(compute_sha256_file, orig_path)
        cache_path = cls.get_hash_cache_path(user_id, content_hash)

        rep: Optional[ProcessedFileRepresentation] = None
        if not force_reprocess and cache_path.exists():
            try:
                async with aiofiles.open(cache_path, "r", encoding="utf-8") as cf:
                    cached_data = json.loads(await cf.read())
                if cached_data.get("parserVersion") == PARSER_VERSION:
                    # Clone cached representation for this file_id & filename
                    cached_data["fileId"] = file_id
                    cached_data["userId"] = str(user_id)
                    cached_data["filename"] = filename
                    if conversation_id:
                        cached_data["conversationId"] = conversation_id
                    if message_id:
                        cached_data["messageId"] = message_id
                    for ch in cached_data.get("chunks", []):
                        ch["fileId"] = file_id
                        ch["filename"] = filename
                        if "metadata" in ch and isinstance(ch["metadata"], dict):
                            ch["metadata"]["fileId"] = file_id
                            ch["metadata"]["filename"] = filename
                    rep = ProcessedFileRepresentation.model_validate(cached_data)
            except Exception:
                rep = None

        if rep is None:
            # Run parser withprocessing timeout watchdog (Section 62 & 63)
            try:
                rep = await asyncio.wait_for(
                    asyncio.to_thread(
                        FileAdapterRegistryV2.process_file,
                        orig_path,
                        file_id,
                        str(user_id),
                        filename,
                        client_mime,
                        conversation_id,
                        message_id,
                    ),
                    timeout=FILE_LIMITS.MAX_PROCESSING_TIME,
                )
            except asyncio.TimeoutError:
                rep = ProcessedFileRepresentation(
                    fileId=file_id,
                    userId=str(user_id),
                    conversationId=conversation_id,
                    messageId=message_id,
                    filename=filename,
                    mimeType=client_mime or "application/octet-stream",
                    detectedFormat="timeout",
                    extension=os.path.splitext(filename)[1].lstrip("."),
                    size=os.path.getsize(orig_path),
                    contentHash=content_hash,
                    parserName="TimeoutWatchdog",
                    status=FileProcessingState.FAILED,
                    processingStage="Timed Out",
                    error=f"File processing timed out after {int(FILE_LIMITS.MAX_PROCESSING_TIME)}s.",
                    createdAt=datetime.now(timezone.utc).isoformat(),
                )

            # Save to hash cache if READY or PARTIAL
            if rep.status in (FileProcessingState.READY, FileProcessingState.PARTIAL):
                try:
                    async with aiofiles.open(cache_path, "w", encoding="utf-8") as cf:
                        await cf.write(rep.model_dump_json())
                except Exception:
                    pass

        await cls._persist_representation(db, rep, orig_path)
        return rep

    @classmethod
    async def _persist_representation(
        cls,
        db: AsyncSession,
        rep: ProcessedFileRepresentation,
        orig_path: str,
    ) -> None:
        """Save processed JSON to disk and upsert GeneratedFile record in DB."""
        proc_path = cls.get_processed_path(rep.userId, rep.fileId)
        try:
            async with aiofiles.open(proc_path, "w", encoding="utf-8") as pf:
                await pf.write(rep.model_dump_json())
        except Exception:
            pass

        _MEMORY_REP_CACHE[(str(rep.userId), rep.fileId)] = rep

        try:
            stmt = select(GeneratedFile).where(GeneratedFile.id == rep.fileId)
            res = await db.execute(stmt)
            existing = res.scalar_one_or_none()

            preview_payload = {
                "file_id": rep.fileId,
                "filename": rep.filename,
                "detected_format": rep.detectedFormat,
                "status": rep.status.value,
                "processing_stage": rep.processingStage,
                "error": rep.error,
                "warnings": rep.warnings,
                "content_hash": rep.contentHash,
                "parser_name": rep.parserName,
                "capabilities": rep.capabilities.model_dump(),
                "structure_summary": rep.structureSummary,
                "chunk_count": len(rep.chunks),
                "total_tokens_estimate": rep.totalTokensEstimate,
                **rep.preview,
            }

            if existing:
                existing.filename = rep.filename
                existing.mime_type = rep.mimeType
                existing.file_size = rep.size
                existing.status = rep.status.value
                if rep.conversationId:
                    existing.conversation_id = rep.conversationId
                existing.preview_data = json.dumps(preview_payload)
                existing.content_data = json.dumps({
                    "content_hash": rep.contentHash,
                    "parser_version": rep.parserVersion,
                    "parser_name": rep.parserName,
                    "detected_format": rep.detectedFormat,
                    "chunk_count": len(rep.chunks),
                    "error": rep.error,
                    "message_id": rep.messageId,
                })
            else:
                gen_file = GeneratedFile(
                    id=rep.fileId,
                    user_id=str(rep.userId),
                    conversation_id=rep.conversationId,
                    filename=rep.filename,
                    storage_path=orig_path,
                    mime_type=rep.mimeType,
                    file_size=rep.size,
                    status=rep.status.value,
                    preview_data=json.dumps(preview_payload),
                    content_data=json.dumps({
                        "content_hash": rep.contentHash,
                        "parser_version": rep.parserVersion,
                        "parser_name": rep.parserName,
                        "detected_format": rep.detectedFormat,
                        "chunk_count": len(rep.chunks),
                        "error": rep.error,
                        "message_id": rep.messageId,
                    }),
                )
                db.add(gen_file)
            await db.commit()
        except Exception:
            await db.rollback()

    @classmethod
    async def wait_if_inflight(cls, file_id: str, timeout: float = 30.0) -> None:
        """Wait if a file is currently being uploaded/processed (Section 38 race condition guard)."""
        ev = _INFLIGHT_TASKS.get(file_id)
        if ev and not ev.is_set():
            try:
                await asyncio.wait_for(ev.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                pass

    @classmethod
    async def link_files_to_conversation(
        cls,
        db: AsyncSession,
        user_id: str,
        file_ids: list[str],
        conversation_id: str,
        message_id: Optional[str] = None,
    ) -> list[ProcessedFileRepresentation]:
        """
        Associate uploaded fileIds with a conversationId and messageId so follow-up questions
        and page refreshes always retain the exact file link.
        """
        linked: list[ProcessedFileRepresentation] = []
        for fid in file_ids:
            await cls.wait_if_inflight(fid)
            rep = await cls.load_representation(db, user_id, fid)
            if not rep:
                continue
            changed = False
            if conversation_id and rep.conversationId != conversation_id:
                rep.conversationId = conversation_id
                changed = True
            if message_id and rep.messageId != message_id:
                rep.messageId = message_id
                changed = True

            # Update DB record
            try:
                stmt = select(GeneratedFile).where(
                    GeneratedFile.id == fid,
                    GeneratedFile.user_id == str(user_id),
                )
                res = await db.execute(stmt)
                rec = res.scalar_one_or_none()
                if rec and conversation_id and rec.conversation_id != conversation_id:
                    rec.conversation_id = conversation_id
                    await db.commit()
            except Exception:
                await db.rollback()

            if changed:
                proc_path = cls.get_processed_path(user_id, fid)
                try:
                    async with aiofiles.open(proc_path, "w", encoding="utf-8") as pf:
                        await pf.write(rep.model_dump_json())
                except Exception:
                    pass
                _MEMORY_REP_CACHE[(str(user_id), fid)] = rep

            linked.append(rep)
        return linked

    @classmethod
    async def load_representation(
        cls,
        db: AsyncSession,
        user_id: str,
        file_id: str,
    ) -> Optional[ProcessedFileRepresentation]:
        """
        Load a user's ProcessedFileRepresentation by file_id with strict user ownership check.
        If processed JSON is missing on disk but original file exists, transparently reprocesses it.
        """
        await cls.wait_if_inflight(file_id)

        mem_key = (str(user_id), str(file_id))
        if mem_key in _MEMORY_REP_CACHE:
            return _MEMORY_REP_CACHE[mem_key]

        # Verify ownership in DB if record exists
        stmt = select(GeneratedFile).where(GeneratedFile.id == str(file_id))
        res = await db.execute(stmt)
        rec = res.scalar_one_or_none()
        if rec is not None:
            if rec.user_id and str(rec.user_id) != str(user_id):
                # Access denied: belongs to another user!
                return None

        proc_path = cls.get_processed_path(user_id, file_id)
        if proc_path.exists():
            try:
                async with aiofiles.open(proc_path, "r", encoding="utf-8") as pf:
                    data = json.loads(await pf.read())
                if str(data.get("userId")) != str(user_id):
                    return None
                rep = ProcessedFileRepresentation.model_validate(data)
                if rec and rec.conversation_id and not rep.conversationId:
                    rep.conversationId = rec.conversation_id
                _MEMORY_REP_CACHE[mem_key] = rep
                return rep
            except Exception:
                pass

        # If DB record exists and points to original file on disk, reprocess on the fly
        if rec and rec.storage_path and os.path.exists(rec.storage_path):
            return await cls.process_stored_file(
                orig_path=rec.storage_path,
                file_id=rec.id,
                user_id=str(user_id),
                filename=rec.filename,
                client_mime=rec.mime_type,
                db=db,
                conversation_id=rec.conversation_id,
            )

        return None

    @classmethod
    async def get_conversation_files(
        cls,
        db: AsyncSession,
        user_id: str,
        conversation_id: Optional[str],
    ) -> list[ProcessedFileRepresentation]:
        """Return all processed files associated with a conversation (or recent user uploads)."""
        if not user_id:
            return []

        reps: list[ProcessedFileRepresentation] = []
        seen_ids: set[str] = set()

        if conversation_id:
            stmt = (
                select(GeneratedFile)
                .where(
                    GeneratedFile.user_id == str(user_id),
                    GeneratedFile.conversation_id == str(conversation_id),
                )
                .order_by(desc(GeneratedFile.created_at))
            )
            res = await db.execute(stmt)
            records = res.scalars().all()
            for r in records:
                # Skip AI-generated deliverables that don't have a processed user upload JSON unless processed
                rep = await cls.load_representation(db, user_id, r.id)
                if rep and rep.fileId not in seen_ids:
                    seen_ids.add(rep.fileId)
                    reps.append(rep)

        return reps

    @classmethod
    async def find_user_files_by_name_or_recent(
        cls,
        db: AsyncSession,
        user_id: str,
        filename_hints: Optional[list[str]] = None,
        conversation_id: Optional[str] = None,
        limit: int = 10,
    ) -> list[ProcessedFileRepresentation]:
        """
        Resolve files by explicit filename hints or conversation history.
        """
        stmt = (
            select(GeneratedFile)
            .where(GeneratedFile.user_id == str(user_id))
            .order_by(desc(GeneratedFile.created_at))
            .limit(50)
        )
        res = await db.execute(stmt)
        all_recs = res.scalars().all()

        matched: list[ProcessedFileRepresentation] = []
        seen: set[str] = set()

        if filename_hints:
            lowered_hints = [h.lower().strip() for h in filename_hints if h.strip()]
            # Prefer files in this conversation first
            sorted_recs = sorted(
                all_recs,
                key=lambda r: (0 if (conversation_id and r.conversation_id == conversation_id) else 1),
            )
            for r in sorted_recs:
                r_name = (r.filename or "").lower()
                if any(h == r_name or h in r_name or r_name in h for h in lowered_hints):
                    proc_path = cls.get_processed_path(user_id, r.id)
                    if proc_path.exists():
                        rep = await cls.load_representation(db, user_id, r.id)
                        if rep and rep.fileId not in seen:
                            seen.add(rep.fileId)
                            matched.append(rep)

        if not matched and conversation_id:
            for r in all_recs:
                if r.conversation_id == conversation_id:
                    proc_path = cls.get_processed_path(user_id, r.id)
                    if proc_path.exists():
                        rep = await cls.load_representation(db, user_id, r.id)
                        if rep and rep.fileId not in seen:
                            seen.add(rep.fileId)
                            matched.append(rep)
                            if len(matched) >= limit:
                                break

        return matched

    # =========================================================================
    # SECTION 69: CONTROLLED INTERNAL FILE CONTENT API (WITH AUTHORIZATION)
    # =========================================================================

    @classmethod
    async def getFileMetadata(cls, db: AsyncSession, file_id: str, user_id: str) -> dict[str, Any]:
        rep = await cls.load_representation(db, user_id, file_id)
        if not rep:
            raise HTTPException(status_code=404, detail="File not found or access denied.")
        return {
            "fileId": rep.fileId,
            "userId": rep.userId,
            "conversationId": rep.conversationId,
            "messageId": rep.messageId,
            "filename": rep.filename,
            "mimeType": rep.mimeType,
            "detectedFormat": rep.detectedFormat,
            "extension": rep.extension,
            "size": rep.size,
            "contentHash": rep.contentHash,
            "parser": rep.parserName,
            "parserVersion": rep.parserVersion,
            "status": rep.status.value,
            "processingStage": rep.processingStage,
            "error": rep.error,
            "warnings": rep.warnings,
            "capabilities": rep.capabilities.model_dump(),
            "structureSummary": rep.structureSummary,
            "chunkCount": len(rep.chunks),
            "totalTokensEstimate": rep.totalTokensEstimate,
            "createdAt": rep.createdAt,
        }

    @classmethod
    async def getFilePreview(cls, db: AsyncSession, file_id: str, user_id: str) -> dict[str, Any]:
        rep = await cls.load_representation(db, user_id, file_id)
        if not rep:
            raise HTTPException(status_code=404, detail="File not found or access denied.")
        return {
            "fileId": rep.fileId,
            "filename": rep.filename,
            "detectedFormat": rep.detectedFormat,
            "mimeType": rep.mimeType,
            "size": rep.size,
            "status": rep.status.value,
            "error": rep.error,
            "capabilities": rep.capabilities.model_dump(),
            "structureSummary": rep.structureSummary,
            "textPreview": rep.textPreview,
            "preview": rep.preview,
        }

    @classmethod
    async def getFileText(cls, db: AsyncSession, file_id: str, user_id: str, max_chars: int = 100_000) -> dict[str, Any]:
        rep = await cls.load_representation(db, user_id, file_id)
        if not rep:
            raise HTTPException(status_code=404, detail="File not found or access denied.")
        return {
            "fileId": rep.fileId,
            "filename": rep.filename,
            "status": rep.status.value,
            "text": rep.fullText[:max_chars],
            "truncated": len(rep.fullText) > max_chars,
            "totalChars": len(rep.fullText),
        }

    @classmethod
    async def searchFile(cls, db: AsyncSession, file_id: str, user_id: str, query: str, top_k: int = 10) -> dict[str, Any]:
        from app.services.file_intelligence.retrieval import FileRetrievalEngineV2
        rep = await cls.load_representation(db, user_id, file_id)
        if not rep:
            raise HTTPException(status_code=404, detail="File not found or access denied.")
        hits = FileRetrievalEngineV2.search_within_file(rep, query, top_k=top_k)
        return {
            "fileId": rep.fileId,
            "filename": rep.filename,
            "query": query,
            "totalMatches": len(hits),
            "matches": hits,
        }

    @classmethod
    async def getFileChunks(cls, db: AsyncSession, file_id: str, user_id: str, chunk_ids: Optional[list[str]] = None) -> dict[str, Any]:
        rep = await cls.load_representation(db, user_id, file_id)
        if not rep:
            raise HTTPException(status_code=404, detail="File not found or access denied.")
        chunks = rep.chunks
        if chunk_ids:
            id_set = set(chunk_ids)
            chunks = [c for c in chunks if c.chunkId in id_set]
        return {
            "fileId": rep.fileId,
            "filename": rep.filename,
            "chunks": [
                {
                    "chunkId": c.chunkId,
                    "text": c.text,
                    "tokenEstimate": c.tokenEstimate,
                    "citation": c.metadata.format_citation(),
                    "metadata": c.metadata.to_compact_dict(),
                }
                for c in chunks
            ],
        }

    @classmethod
    async def getFilePage(cls, db: AsyncSession, file_id: str, user_id: str, page: int) -> dict[str, Any]:
        rep = await cls.load_representation(db, user_id, file_id)
        if not rep:
            raise HTTPException(status_code=404, detail="File not found or access denied.")
        pages = rep.structuredData.get("pages") or []
        for p in pages:
            if p.get("page") == page:
                return {
                    "fileId": rep.fileId,
                    "filename": rep.filename,
                    "page": page,
                    "content": p,
                }
        # Fallback to chunks matching page
        page_chunks = [c.text for c in rep.chunks if c.metadata.page == page]
        if page_chunks:
            return {
                "fileId": rep.fileId,
                "filename": rep.filename,
                "page": page,
                "content": {"page": page, "text": "\n\n".join(page_chunks)},
            }
        raise HTTPException(status_code=404, detail=f"Page {page} not found in {rep.filename}.")

    @classmethod
    async def getSpreadsheetRange(
        cls,
        db: AsyncSession,
        file_id: str,
        user_id: str,
        sheet: Optional[str] = None,
        cell_range: Optional[str] = None,
    ) -> dict[str, Any]:
        rep = await cls.load_representation(db, user_id, file_id)
        if not rep:
            raise HTTPException(status_code=404, detail="File not found or access denied.")
        sheets = rep.structuredData.get("sheets") or []
        if not sheets:
            raise HTTPException(status_code=400, detail=f"File '{rep.filename}' is not a spreadsheet.")
        target = sheets[0]
        if sheet:
            for s in sheets:
                if s.get("sheet_name", "").lower() == sheet.lower():
                    target = s
                    break
        calc_summary = None
        if cell_range:
            calc_summary = SpreadsheetCalculator.analyze_and_calculate(
                rep.filename, [target], f"{target.get('sheet_name', '')} {cell_range}"
            )
        return {
            "fileId": rep.fileId,
            "filename": rep.filename,
            "sheet": target.get("sheet_name"),
            "headers": target.get("headers"),
            "rowCount": target.get("row_count"),
            "columnStats": target.get("column_stats"),
            "rows": (target.get("rows") or [])[:100],
            "calculation": calc_summary,
        }

    @classmethod
    async def getCodeRange(
        cls,
        db: AsyncSession,
        file_id: str,
        user_id: str,
        start_line: int = 1,
        end_line: int = 100,
        inner_path: Optional[str] = None,
    ) -> dict[str, Any]:
        rep = await cls.load_representation(db, user_id, file_id)
        if not rep:
            raise HTTPException(status_code=404, detail="File not found or access denied.")
        if inner_path and rep.detectedFormat == "archive":
            matching = [
                c for c in rep.chunks
                if c.metadata.innerPath and inner_path.lower() in c.metadata.innerPath.lower()
            ]
            return {
                "fileId": rep.fileId,
                "filename": rep.filename,
                "innerPath": inner_path,
                "chunks": [c.text for c in matching],
            }
        lines = rep.fullText.splitlines()
        s = max(1, start_line)
        e = min(len(lines), max(s, end_line))
        numbered = [f"{ln}: {lines[ln - 1]}" for ln in range(s, e + 1)]
        return {
            "fileId": rep.fileId,
            "filename": rep.filename,
            "lineStart": s,
            "lineEnd": e,
            "totalLines": len(lines),
            "code": "\n".join(numbered),
        }
