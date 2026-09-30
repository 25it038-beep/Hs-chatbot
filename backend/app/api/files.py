import os
import json
import uuid
import hashlib
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
import aiofiles
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import FileResponse as FastApiFileResponse, JSONResponse
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.database import get_db
from app.middleware.auth import get_current_user, get_optional_user
from app.models.user import User
from app.models.file import GeneratedFile
from app.services.rag import RAGService
from app.services.chat_context.file_adapters.registry import file_adapter_registry
from app.services.chat_context.retrieval_engine import file_retrieval_engine
from app.services.nvidia.chat import NvidiaChatProvider
from app.services.nvidia.vision import NvidiaVisionProvider
from app.config import settings

logger = logging.getLogger("hsbot.files")
_logger = logger
router = APIRouter(prefix="/api/files", tags=["files"])

chat_provider = NvidiaChatProvider()
vision_provider = NvidiaVisionProvider()


UNSUPPORTED_EXECUTABLE_EXTENSIONS = {
    ".exe", ".dll", ".bat", ".cmd", ".msi", ".scr", ".com", ".pif", ".vbs", ".jar", ".apk", ".dmg", ".iso"
}


class FileResponse(BaseModel):
    id: str
    filename: str
    size: int
    content_type: str
    category: Optional[str] = "document"
    extension: Optional[str] = ""
    status: str = "READY"
    content_ready: bool = True
    source: Optional[str] = "picker"
    processing_stage: str = "READY"
    text_preview: str = ""
    chunk_count: int = 0
    total_tokens: int = 0
    citations: List[str] = []
    error: Optional[str] = None
    analysis: Optional[str] = None
    download_url: Optional[str] = None
    url: Optional[str] = None


class FileStatusResponse(BaseModel):
    id: Optional[str] = None
    file_id: Optional[str] = None
    filename: str
    status: str
    content_ready: bool = True
    processing_stage: str = "READY"
    size: int
    content_type: str
    chunk_count: int = 0
    total_tokens: int = 0
    text_preview: str = ""
    citations: List[str] = []
    capabilities: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: Optional[str] = None


def _get_user_dirs(user_id: str) -> tuple[str, str]:
    original_dir = os.path.join(settings.upload_dir, "users", str(user_id), "original")
    processed_dir = os.path.join(settings.upload_dir, "users", str(user_id), "processed")
    os.makedirs(original_dir, exist_ok=True)
    os.makedirs(processed_dir, exist_ok=True)
    return original_dir, processed_dir


@router.post("/upload", response_model=FileResponse, status_code=201)
async def upload_file(
    file: UploadFile = File(...),
    chat_id: Optional[str] = Form(None),
    message_id: Optional[str] = Form(None),
    analyze: bool = Query(False),
    source: str = Query("picker"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Durable file upload and intelligent extraction:
    - Validates size limit (50MB)
    - Computes content SHA-256 hash for duplicate detection
    - Stores original file securely under users/{user_id}/original/
    - Runs universal structure-aware parsing
    - Persists structured chunks and extracted text under users/{user_id}/processed/
    - Records file ownership, status, and conversation link in database
    """
    max_size = settings.max_file_size_mb * 1024 * 1024
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file (0 bytes) cannot be uploaded.")
    if len(content) > max_size:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.max_file_size_mb}MB limit")

    original_filename = file.filename or "unknown"
    ext = os.path.splitext(original_filename)[1].lower()
    content_type = file.content_type or "application/octet-stream"
    if ext in UNSUPPORTED_EXECUTABLE_EXTENSIONS or content[:2] == b"MZ":
        raise HTTPException(status_code=400, detail=f"Unsupported format ({ext or content_type}). Executable files cannot be uploaded.")

    content_hash = hashlib.sha256(content).hexdigest()
    original_dir, processed_dir = _get_user_dirs(current_user.id)

    # 1. Duplicate detection: check if exact file was previously processed for this user
    dup_stmt = select(GeneratedFile).where(
        GeneratedFile.user_id == current_user.id,
        GeneratedFile.content_hash == content_hash,
        GeneratedFile.status.in_(["ready", "READY", "partial", "PARTIAL"])
    ).order_by(GeneratedFile.created_at.desc())
    dup_res = await db.execute(dup_stmt)
    existing_file = dup_res.scalars().first()

    file_id = str(uuid.uuid4())
    ext = os.path.splitext(original_filename)[1] or ".bin"
    safe_name = f"{file_id}{ext}"
    original_path = os.path.join(original_dir, safe_name)

    # Save original file
    async with aiofiles.open(original_path, "wb") as f:
        await f.write(content)

    chunks_path = os.path.join(processed_dir, f"{file_id}_chunks.json")
    extracted_text_path = os.path.join(processed_dir, f"{file_id}_extracted.txt")
    full_text = ""
    text_snippet = ""

    if existing_file and existing_file.chunks_path and os.path.exists(existing_file.chunks_path):
        # Instant reuse of existing processed chunks
        logger.info(f"Duplicate file detected ({content_hash[:8]}). Reusing pre-extracted chunks.")
        try:
            with open(existing_file.chunks_path, "r", encoding="utf-8") as f:
                cached_data = json.load(f)
            with open(chunks_path, "w", encoding="utf-8") as f:
                json.dump(cached_data, f)
            if existing_file.extracted_text_path and os.path.exists(existing_file.extracted_text_path):
                import shutil
                shutil.copy2(existing_file.extracted_text_path, extracted_text_path)
            else:
                chunks = cached_data.get("chunks", [])
                full_text = "\n\n".join(c.get("content", "") for c in chunks)
                with open(extracted_text_path, "w", encoding="utf-8") as f:
                    f.write(full_text)
            text_snippet = cached_data.get("summary", "")
            chunk_count = len(cached_data.get("chunks", []))
            total_tokens = cached_data.get("total_tokens", 0)
            citations = cached_data.get("citations", [])
            status_val = existing_file.status
            processing_stage = "READY"
        except Exception:
            existing_file = None

    if not existing_file or not os.path.exists(chunks_path) or not os.path.exists(extracted_text_path):
        # Run universal file adapter extraction
        try:
            analysis_res = await file_adapter_registry.process_file(
                file_path=original_path,
                filename=original_filename,
                file_id=file_id,
                mime_type=content_type,
                use_cache=True
            )
            # Persist chunks JSON
            with open(chunks_path, "w", encoding="utf-8") as f:
                json.dump(analysis_res.to_dict(), f)

            # Persist clean text
            full_text = "\n\n".join(c.content for c in analysis_res.chunks)
            with open(extracted_text_path, "w", encoding="utf-8") as f:
                f.write(full_text)

            chunk_count = len(analysis_res.chunks)
            total_tokens = analysis_res.total_tokens
            citations = analysis_res.citations
            text_snippet = full_text[:500] if full_text.strip() else (analysis_res.summary or "")

            if analysis_res.state.value == "FAILED":
                status_val = "FAILED"
                processing_stage = "FAILED"
                err_msg = analysis_res.error or "Extraction failed"
            elif analysis_res.is_partially_supported:
                status_val = "PARTIAL"
                processing_stage = "READY"
                err_msg = None
            else:
                status_val = "READY"
                processing_stage = "READY"
                err_msg = None

        except Exception as e:
            logger.error(f"Error extracting uploaded file {original_filename}: {e}", exc_info=True)
            status_val = "FAILED"
            processing_stage = "FAILED"
            err_msg = str(e)
            chunk_count = 0
            total_tokens = 0
            citations = []
            text_snippet = ""
    else:
        err_msg = None

    # Persist in GeneratedFile database table
    try:
        metadata_dict = {
            "chunk_count": chunk_count,
            "total_tokens": total_tokens,
            "citations": citations,
            "content_hash": content_hash
        }
        gen_file = GeneratedFile(
            id=file_id,
            user_id=current_user.id,
            conversation_id=chat_id,
            message_id=message_id,
            filename=original_filename,
            storage_path=original_path,
            mime_type=content_type,
            file_size=len(content),
            content_hash=content_hash,
            status=status_val,
            processing_stage=processing_stage,
            error_message=err_msg,
            chunks_path=chunks_path,
            extracted_text_path=extracted_text_path,
            metadata_json=json.dumps(metadata_dict),
            content_data=full_text if 'full_text' in locals() and full_text else text_snippet,
        )
        db.add(gen_file)
        await db.commit()
    except Exception as e:
        logger.warning(f"Error persisting GeneratedFile record: {e}")
        await db.rollback()

    # Cache in RAGService for legacy compatibility
    cache_body = (full_text[:50000] if full_text else text_snippet) or ""
    RAGService.cache_file(current_user.id, original_filename, original_path, cache_body, file_id)

    # Optional background analysis if requested
    analysis_report = None
    if analyze and status_val != "FAILED":
        if content_type.startswith("image/"):
            try:
                resp = await vision_provider.analyze(
                    image_data=content,
                    prompt="Analyze this image in detail. Describe the scene, objects, people, text visible, and notable elements.",
                    mime_type=content_type,
                )
                analysis_report = resp.content or None
            except Exception:
                pass

    category = "image" if content_type.startswith("image/") else "code" if ext in (".py", ".js", ".ts", ".html", ".css", ".json", ".sql") else "spreadsheet" if ext in (".csv", ".tsv", ".xlsx", ".xls") else "document"
    status_lower = "ready" if status_val in ("ready", "READY") else status_val.lower()
    return FileResponse(
        id=file_id,
        filename=original_filename,
        size=len(content),
        content_type=content_type,
        category=category,
        extension=ext,
        status=status_lower,
        content_ready=status_val in ("ready", "READY"),
        source=source,
        processing_stage=processing_stage,
        text_preview=text_snippet[:500],
        chunk_count=chunk_count,
        total_tokens=total_tokens,
        citations=citations,
        error=err_msg,
        analysis=analysis_report,
        download_url=f"/api/files/{file_id}/download",
        url=f"/api/files/{file_id}/content",
    )


@router.post("/upload-multiple")
async def upload_multiple_files(
    files: list[UploadFile] = File(...),
    chat_id: Optional[str] = Form(None),
    message_id: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    results = []
    for file in files:
        res = await upload_file(
            file=file,
            chat_id=chat_id,
            message_id=message_id,
            analyze=False,
            current_user=current_user,
            db=db
        )
        results.append(res)
    return {"files": results}


@router.get("/{file_id}/status", response_model=FileStatusResponse)
async def get_file_status(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns the live status, processing stage, and chunk details for an attachment."""
    stmt = select(GeneratedFile).where(
        GeneratedFile.id == file_id,
        or_(GeneratedFile.user_id == current_user.id, GeneratedFile.user_id == "default_user_id")
    )
    res = await db.execute(stmt)
    rec = res.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="File not found")

    meta = {}
    if rec.metadata_json:
        try:
            meta = json.loads(rec.metadata_json)
        except Exception:
            pass

    adapter = file_adapter_registry.get_adapter(rec.filename, rec.mime_type)
    capabilities = adapter.get_capabilities().to_dict() if adapter else None

    status_str = "ready" if rec.status in ("ready", "READY") else (rec.status.lower() if rec.status else "ready")
    content_is_ready = status_str == "ready"

    preview = rec.content_data[:500] if getattr(rec, "content_data", None) else ""
    if not preview and rec.extracted_text_path and os.path.exists(rec.extracted_text_path):
        try:
            with open(rec.extracted_text_path, "r", encoding="utf-8") as f:
                preview = f.read(500)
        except Exception:
            pass

    return FileStatusResponse(
        id=rec.id,
        file_id=rec.id,
        filename=rec.filename,
        status=status_str,
        content_ready=content_is_ready,
        processing_stage=rec.processing_stage or "READY",
        size=rec.file_size,
        content_type=rec.mime_type,
        chunk_count=meta.get("chunk_count", 0),
        total_tokens=meta.get("total_tokens", 0),
        text_preview=preview,
        citations=meta.get("citations", []),
        capabilities=capabilities,
        error=rec.error_message,
        created_at=rec.created_at.isoformat() if rec.created_at else None
    )


@router.get("/{file_id}/content")
async def get_file_content(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns the raw file content bytes or stream with tenant isolation."""
    from starlette.responses import FileResponse as StarletteFileResponse, Response

    stmt = select(GeneratedFile).where(
        GeneratedFile.id == file_id,
        or_(GeneratedFile.user_id == current_user.id, GeneratedFile.user_id == "default_user_id")
    )
    res = await db.execute(stmt)
    rec = res.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = rec.storage_path
    if file_path and os.path.exists(file_path):
        return StarletteFileResponse(
            path=file_path,
            media_type=rec.mime_type or "application/octet-stream",
            filename=rec.filename,
        )

    if rec.extracted_text_path and os.path.exists(rec.extracted_text_path):
        return StarletteFileResponse(
            path=rec.extracted_text_path,
            media_type="text/plain; charset=utf-8",
            filename=rec.filename,
        )

    if rec.content_data:
        return Response(content=rec.content_data, media_type="text/plain; charset=utf-8")

    raise HTTPException(status_code=404, detail="File content not found")


@router.get("/{file_id}/search")
async def search_in_file(
    file_id: str,
    q: str = Query(..., description="Query to search within file chunks"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Direct search within the file chunks."""
    stmt = select(GeneratedFile).where(
        GeneratedFile.id == file_id,
        or_(GeneratedFile.user_id == current_user.id, GeneratedFile.user_id == "default_user_id")
    )
    res = await db.execute(stmt)
    rec = res.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="File not found")

    matches = await file_retrieval_engine.search_in_files(
        user_id=current_user.id,
        query=q,
        file_id=file_id
    )
    return {"file_id": file_id, "query": q, "matches": matches}


@router.get("/{file_id}/download")
async def download_file(
    file_id: str,
    token: Optional[str] = Query(None),
    user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Downloads a file by file_id as a real binary FileResponse with strict tenant isolation."""
    from app.utils.security import decode_token

    active_user = user
    if not active_user and token:
        payload = decode_token(token)
        if payload and payload.get("sub"):
            u_res = await db.execute(select(User).where(User.id == str(payload["sub"])))
            active_user = u_res.scalar_one_or_none()

    if not active_user:
        raise HTTPException(status_code=401, detail="Authentication required to download files.")

    stmt = select(GeneratedFile).where(GeneratedFile.id == file_id)
    res = await db.execute(stmt)
    file_record = res.scalar_one_or_none()

    file_path = None
    filename = "download"
    media_type = "application/octet-stream"

    if file_record:
        if file_record.user_id and file_record.user_id not in (active_user.id, "default_user_id"):
            raise HTTPException(status_code=404, detail="File not found")
        file_path = file_record.storage_path
        filename = file_record.filename
        media_type = file_record.mime_type
    else:
        user_dir = os.path.join(settings.upload_dir, "users", str(active_user.id), "original")
        if os.path.exists(user_dir):
            for fname in os.listdir(user_dir):
                if fname.startswith(file_id):
                    file_path = os.path.join(user_dir, fname)
                    filename = fname
                    break

    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    resolved = Path(file_path).resolve()
    allowed_bases = [
        Path(settings.upload_dir).resolve(),
        Path(settings.storage_dir).resolve(),
        Path("./data").resolve(),
        Path("./storage").resolve(),
    ]
    is_safe = False
    for base in allowed_bases:
        try:
            resolved.relative_to(base)
            is_safe = True
            break
        except ValueError:
            pass

    if not is_safe:
        raise HTTPException(status_code=403, detail="Access denied")

    return FastApiFileResponse(
        path=file_path,
        filename=filename,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{file_id}/preview")
async def preview_file(
    file_id: str,
    token: Optional[str] = Query(None),
    user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns structured preview data with strict tenant isolation."""
    from app.utils.security import decode_token

    active_user = user
    if not active_user and token:
        payload = decode_token(token)
        if payload and payload.get("sub"):
            u_res = await db.execute(select(User).where(User.id == str(payload["sub"])))
            active_user = u_res.scalar_one_or_none()

    if not active_user:
        raise HTTPException(status_code=401, detail="Authentication required to preview files.")

    stmt = select(GeneratedFile).where(GeneratedFile.id == file_id)
    res = await db.execute(stmt)
    file_record = res.scalar_one_or_none()

    if not file_record or (file_record.user_id and file_record.user_id not in (active_user.id, "default_user_id")):
        raise HTTPException(status_code=404, detail="File not found")

    preview_json = {}
    if file_record.preview_data:
        try:
            preview_json = json.loads(file_record.preview_data)
        except Exception:
            preview_json = {}

    # If chunks exist, provide sample preview
    if not preview_json and file_record.chunks_path and os.path.exists(file_record.chunks_path):
        try:
            with open(file_record.chunks_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            chunks = data.get("chunks", [])
            preview_json = {
                "summary": data.get("summary", ""),
                "sample_chunks": [c.get("content") for c in chunks[:3]],
                "citations": data.get("citations", []),
                "chunk_count": len(chunks)
            }
        except Exception:
            pass

    design_spec_json = None
    if file_record.design_spec:
        try:
            design_spec_json = json.loads(file_record.design_spec)
        except Exception:
            design_spec_json = None

    verification_json = None
    if file_record.verification_result:
        try:
            verification_json = json.loads(file_record.verification_result)
        except Exception:
            verification_json = None

    return {
        "file_id": file_record.id,
        "filename": file_record.filename,
        "format": file_record.filename.split(".")[-1].lower(),
        "size": file_record.file_size,
        "status": file_record.status,
        "download_url": f"/api/files/{file_record.id}/download",
        "preview": preview_json,
        "design_spec": design_spec_json,
        "verification": verification_json,
    }


async def resolve_conversation_file_context(
    db: AsyncSession,
    user_id: Optional[str],
    chat_id: Optional[str],
    file_ids: Optional[list[str]],
    message_text: str,
    client_attachments: Optional[list[dict]] = None,
) -> tuple[str, list[dict]]:
    """
    Validates file ownership, links uploaded files to the conversation, loads extracted content
    (for both newly attached files and existing conversation files for follow-up questions),
    and returns (context_block_for_system_prompt, verified_message_attachments).
    """
    if not user_id:
        return "", []

    client_meta_by_id = {}
    if client_attachments:
        for ca in client_attachments:
            if isinstance(ca, dict):
                cid = ca.get("id") or ca.get("fileId")
                if cid:
                    client_meta_by_id[str(cid)] = ca

    requested_ids = [str(fid).strip() for fid in (file_ids or []) if fid and str(fid).strip()]
    verified_attachments: list[dict] = []
    active_records: list[GeneratedFile] = []
    seen_ids: set[str] = set()

    # 1. Verify explicitly attached fileIds from the current message
    if requested_ids:
        stmt = select(GeneratedFile).where(
            GeneratedFile.id.in_(requested_ids),
            GeneratedFile.user_id == str(user_id),
        )
        res = await db.execute(stmt)
        records_by_id = {r.id: r for r in res.scalars().all()}
        dirty = False
        for fid in requested_ids:
            rec = records_by_id.get(fid)
            if not rec or rec.status not in ("ready", "READY", "partial", "PARTIAL"):
                continue
            fpath = rec.storage_path or getattr(rec, "original_path", None)
            if not fpath or not os.path.exists(fpath):
                continue
            if chat_id and rec.conversation_id != str(chat_id):
                rec.conversation_id = str(chat_id)
                dirty = True
            if rec.id not in seen_ids:
                seen_ids.add(rec.id)
                active_records.append(rec)
            cm = client_meta_by_id.get(str(rec.id), {})
            verified_attachments.append({
                "id": rec.id,
                "fileId": rec.id,
                "name": cm.get("name") or rec.filename,
                "filename": rec.filename,
                "type": cm.get("type") or rec.mime_type or "application/octet-stream",
                "mimeType": cm.get("type") or rec.mime_type or "application/octet-stream",
                "size": rec.file_size,
                "source": cm.get("source", "picker"),
                "download_url": f"/api/files/{rec.id}/download",
            })
        if dirty:
            try:
                await db.commit()
            except Exception:
                await db.rollback()

    # 2. Also load previously attached files in this conversation for follow-up questions
    if chat_id:
        stmt_conv = (
            select(GeneratedFile)
            .where(
                GeneratedFile.conversation_id == str(chat_id),
                GeneratedFile.user_id == str(user_id),
                GeneratedFile.status.in_(["ready", "READY", "partial", "PARTIAL"]),
            )
            .order_by(GeneratedFile.created_at)
        )
        res_conv = await db.execute(stmt_conv)
        for rec in res_conv.scalars().all():
            fpath = rec.storage_path or rec.original_path
            if rec.id not in seen_ids and fpath and os.path.exists(fpath):
                seen_ids.add(rec.id)
                active_records.append(rec)

    if not active_records:
        return "", verified_attachments

    rag = RAGService(db, str(user_id))
    context_sections: list[str] = []

    # Optional vector search for targeted chunks when Qdrant is active
    rag_chunks = await rag.search_similar(message_text)
    if rag_chunks:
        context_sections.append(f"Retrieved Semantic Chunks:\n{rag_chunks}")

    # Direct grounded content from each conversation file
    per_file_budget = max(4000, 36000 // max(1, len(active_records)))
    for rec in active_records:
        cached = RAGService.get_cached_file_by_id(str(user_id), rec.id)
        text_body = (cached["text"] if cached else None) or rec.content_data or ""
        fpath = rec.storage_path or rec.original_path

        ext = os.path.splitext(rec.filename or "")[1].lower()
        is_image = (rec.mime_type or "").startswith("image/") or ext in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp")

        if is_image and (not text_body or text_body.startswith("Image Attachment:")) and fpath and os.path.exists(fpath):
            try:
                async with aiofiles.open(fpath, "rb") as img_f:
                    img_bytes = await img_f.read()
                v_prompt = (
                    f"Analyze this image '{rec.filename}' thoroughly. "
                    f"User question: {message_text or 'Describe all visible text, objects, layout, data, and details.'}"
                )
                v_resp = await vision_provider.analyze(
                    image_data=img_bytes,
                    prompt=v_prompt,
                    mime_type=rec.mime_type if (rec.mime_type or "").startswith("image/") else "image/png",
                )
                if v_resp and v_resp.content:
                    text_body = f"{text_body}\nVisual Analysis:\n{v_resp.content}".strip()
                    rec.content_data = text_body
                    try:
                        await db.commit()
                    except Exception:
                        await db.rollback()
                    RAGService.cache_file(str(user_id), rec.filename, fpath, text_body, rec.id)
            except Exception as exc:
                _logger.warning("[FILE_CONTEXT] vision analysis fallback for file_id=%s: %s", rec.id, exc)

        if not text_body.strip() and fpath and os.path.exists(fpath):
            try:
                proc = await rag.process_file(fpath, rec.filename, rec.id)
                text_body = proc.get("text", "")
                if text_body.strip():
                    rec.content_data = text_body
                    try:
                        await db.commit()
                    except Exception:
                        await db.rollback()
                    RAGService.cache_file(str(user_id), rec.filename, fpath, text_body, rec.id)
            except Exception:
                pass

        if text_body.strip():
            excerpt = text_body[:per_file_budget]
            context_sections.append(
                f"=== ATTACHED FILE: {rec.filename} (fileId: {rec.id}, type: {rec.mime_type}, size: {rec.file_size} bytes) ===\n"
                f"{excerpt}"
            )

    if not context_sections:
        return "", verified_attachments

    full_context = (
        "CRITICAL GROUNDED FILE CONTEXT:\n"
        "The user has attached the following verified file(s) to this conversation. "
        "Base your answer directly on the actual extracted content below. Never claim you only received a filename.\n\n"
        + "\n\n".join(context_sections)
    )
    return full_context, verified_attachments


@router.delete("/{file_id}", status_code=204)
async def delete_uploaded_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Removes an uploaded file owned by the current user from DB, disk, and RAG cache."""
    from fastapi.responses import Response

    stmt = select(GeneratedFile).where(GeneratedFile.id == file_id)
    res = await db.execute(stmt)
    file_record = res.scalar_one_or_none()

    if not file_record or (file_record.user_id and file_record.user_id != current_user.id):
        raise HTTPException(status_code=404, detail="File not found")

    storage_path = file_record.storage_path
    RAGService.remove_cached_file(current_user.id, file_id)
    await db.delete(file_record)
    await db.commit()

    if storage_path and os.path.exists(storage_path):
        try:
            os.remove(storage_path)
        except OSError:
            pass

    _logger.info("[UPLOAD] deleted file_id=%s user_id=%s", file_id, current_user.id)
    return Response(status_code=204)


class ArtifactV2GenerateRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = "general"
    message_id: Optional[str] = ""
    ai_content: Optional[str] = ""
    parent_artifact_id: Optional[str] = None
    uploaded_sources: Optional[list[dict]] = None


class ArtifactV2EditRequest(BaseModel):
    instruction: str
    conversation_id: Optional[str] = "general"


class ArtifactV2ConvertRequest(BaseModel):
    target_format: str
    conversation_id: Optional[str] = "general"


class ArtifactV2RenameRequest(BaseModel):
    filename: str


@router.get("/artifacts-v2/formats")
async def list_artifact_v2_formats():
    from app.services.artifacts.universal_engine_v2 import ArtifactFormatRegistryV2
    return {"formats": ArtifactFormatRegistryV2.list_all()}


@router.post("/artifacts-v2/generate")
async def generate_artifact_v2(
    req: ArtifactV2GenerateRequest,
    current_user: User = Depends(get_current_user),
):
    from app.services.artifacts.universal_engine_v2 import UniversalArtifactEngineV2
    result = UniversalArtifactEngineV2.execute(
        user_id=str(current_user.id),
        conversation_id=req.conversation_id or "general",
        message_id=req.message_id or str(uuid.uuid4()),
        user_message=req.message,
        ai_content=req.ai_content or "",
        uploaded_sources=req.uploaded_sources or [],
        parent_artifact_id=req.parent_artifact_id,
    )
    return result


@router.get("/artifacts-v2/{artifact_id}/download")
async def download_artifact_v2(
    artifact_id: str,
    token: Optional[str] = Query(None),
    user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    from fastapi.responses import Response
    from app.utils.security import decode_token
    from app.services.artifacts.universal_engine_v2 import ArtifactStorageAndVersionManager

    active_user = user
    if not active_user and token:
        payload = decode_token(token)
        if payload and payload.get("sub"):
            u_res = await db.execute(select(User).where(User.id == str(payload["sub"])))
            active_user = u_res.scalar_one_or_none()

    if not active_user:
        raise HTTPException(status_code=401, detail="Authentication required to download artifacts.")

    res = ArtifactStorageAndVersionManager.get_artifact_bytes(str(active_user.id), artifact_id)
    if not res:
        raise HTTPException(status_code=404, detail="Artifact not found")

    record, data_bytes = res
    return Response(
        content=data_bytes,
        media_type=record["mimeType"],
        headers={
            "Content-Disposition": f'attachment; filename="{record["filename"]}"',
            "Content-Length": str(len(data_bytes)),
            "X-Artifact-Version": str(record.get("version", 1)),
            "X-Artifact-SHA256": record.get("hash", ""),
        },
    )


@router.get("/artifacts-v2/{artifact_id}/preview")
async def preview_artifact_v2(
    artifact_id: str,
    current_user: User = Depends(get_current_user),
):
    from app.services.artifacts.universal_engine_v2 import (
        ArtifactStorageAndVersionManager,
        UniversalArtifactEngineV2,
    )
    rec = ArtifactStorageAndVersionManager.get_artifact(str(current_user.id), artifact_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return UniversalArtifactEngineV2.format_delivery_card(rec)


@router.get("/artifacts-v2/{artifact_id}/versions")
async def get_artifact_v2_versions(
    artifact_id: str,
    current_user: User = Depends(get_current_user),
):
    from app.services.artifacts.universal_engine_v2 import ArtifactStorageAndVersionManager
    rec = ArtifactStorageAndVersionManager.get_artifact(str(current_user.id), artifact_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return {
        "artifactId": rec["artifactId"],
        "rootArtifactId": rec.get("rootArtifactId", rec["artifactId"]),
        "currentVersion": rec.get("version", 1),
        "versions": rec.get("versionHistory", []),
    }


@router.post("/artifacts-v2/{artifact_id}/edit")
async def edit_artifact_v2(
    artifact_id: str,
    req: ArtifactV2EditRequest,
    current_user: User = Depends(get_current_user),
):
    from app.services.artifacts.universal_engine_v2 import (
        ArtifactStorageAndVersionManager,
        UniversalArtifactEngineV2,
    )
    from app.services.artifacts.output_intent_engine import OutputIntentResult, OutputMode

    rec = ArtifactStorageAndVersionManager.get_artifact(str(current_user.id), artifact_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Artifact not found")

    ext = rec["extension"]
    edit_intent = OutputIntentResult(
        mode=OutputMode.FILE,
        primary_format=ext,
        formats=[ext],
        filename=rec["filename"],
        topic=(rec.get("spec") or {}).get("title") or rec["filename"],
        is_followup_edit=True,
        edit_instructions=req.instruction,
    )
    result = UniversalArtifactEngineV2.execute(
        user_id=str(current_user.id),
        conversation_id=req.conversation_id or rec.get("conversationId") or "general",
        message_id=str(uuid.uuid4()),
        user_message=req.instruction,
        intent=edit_intent,
        parent_artifact_id=artifact_id,
    )
    return result


@router.post("/artifacts-v2/{artifact_id}/convert")
async def convert_artifact_v2(
    artifact_id: str,
    req: ArtifactV2ConvertRequest,
    current_user: User = Depends(get_current_user),
):
    from app.services.artifacts.universal_engine_v2 import (
        ArtifactStorageAndVersionManager,
        UniversalArtifactEngineV2,
    )
    from app.services.artifacts.output_intent_engine import OutputIntentResult, OutputMode, sanitize_filename

    rec = ArtifactStorageAndVersionManager.get_artifact(str(current_user.id), artifact_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Artifact not found")

    target_fmt = req.target_format.lower().lstrip(".")
    stem = os.path.splitext(rec["filename"])[0]
    new_fname = sanitize_filename(f"{stem}.{target_fmt}", default_stem=stem, ext=target_fmt)

    conv_intent = OutputIntentResult(
        mode=OutputMode.FILE,
        primary_format=target_fmt,
        formats=[target_fmt],
        filename=new_fname,
        topic=(rec.get("spec") or {}).get("title") or stem,
        is_conversion=True,
        source_format=rec["extension"],
    )
    result = UniversalArtifactEngineV2.execute(
        user_id=str(current_user.id),
        conversation_id=req.conversation_id or rec.get("conversationId") or "general",
        message_id=str(uuid.uuid4()),
        user_message=f"Convert {rec['filename']} to {target_fmt.upper()}",
        intent=conv_intent,
        parent_artifact_id=artifact_id,
    )
    return result


@router.patch("/artifacts-v2/{artifact_id}/rename")
async def rename_artifact_v2(
    artifact_id: str,
    req: ArtifactV2RenameRequest,
    current_user: User = Depends(get_current_user),
):
    from app.services.artifacts.universal_engine_v2 import (
        ArtifactStorageAndVersionManager,
        UniversalArtifactEngineV2,
    )
    rec = ArtifactStorageAndVersionManager.rename_artifact(str(current_user.id), artifact_id, req.filename)
    if not rec:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return UniversalArtifactEngineV2.format_delivery_card(rec)


@router.delete("/artifacts-v2/{artifact_id}")
async def delete_artifact_v2(
    artifact_id: str,
    current_user: User = Depends(get_current_user),
):
    from app.services.artifacts.universal_engine_v2 import ArtifactStorageAndVersionManager
    deleted = ArtifactStorageAndVersionManager.delete_artifact(str(current_user.id), artifact_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return {"deleted": True, "artifactId": artifact_id}

