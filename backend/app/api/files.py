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
router = APIRouter(prefix="/api/files", tags=["files"])

chat_provider = NvidiaChatProvider()
vision_provider = NvidiaVisionProvider()


class FileResponse(BaseModel):
    id: str
    filename: str
    size: int
    content_type: str
    status: str = "READY"
    processing_stage: str = "READY"
    text_preview: str = ""
    chunk_count: int = 0
    total_tokens: int = 0
    citations: List[str] = []
    error: Optional[str] = None
    analysis: Optional[str] = None


class FileStatusResponse(BaseModel):
    file_id: str
    filename: str
    status: str
    processing_stage: str
    size: int
    content_type: str
    chunk_count: int = 0
    total_tokens: int = 0
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


@router.post("/upload", response_model=FileResponse)
async def upload_file(
    file: UploadFile = File(...),
    chat_id: Optional[str] = Form(None),
    message_id: Optional[str] = Form(None),
    analyze: bool = Form(False),
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
    if len(content) > max_size:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.max_file_size_mb}MB limit")

    content_hash = hashlib.sha256(content).hexdigest()
    original_filename = file.filename or "unknown"
    content_type = file.content_type or "application/octet-stream"
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
            text_snippet = analysis_res.summary or full_text[:500]

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

    return FileResponse(
        id=file_id,
        filename=original_filename,
        size=len(content),
        content_type=content_type,
        status=status_val,
        processing_stage=processing_stage,
        text_preview=text_snippet[:500],
        chunk_count=chunk_count,
        total_tokens=total_tokens,
        citations=citations,
        error=err_msg,
        analysis=analysis_report,
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

    return FileStatusResponse(
        file_id=rec.id,
        filename=rec.filename,
        status=rec.status,
        processing_stage=rec.processing_stage or "READY",
        size=rec.file_size,
        content_type=rec.mime_type,
        chunk_count=meta.get("chunk_count", 0),
        total_tokens=meta.get("total_tokens", 0),
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
    """Returns the clean extracted text content for the file without exposing raw paths."""
    stmt = select(GeneratedFile).where(
        GeneratedFile.id == file_id,
        or_(GeneratedFile.user_id == current_user.id, GeneratedFile.user_id == "default_user_id")
    )
    res = await db.execute(stmt)
    rec = res.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="File not found")

    if rec.extracted_text_path and os.path.exists(rec.extracted_text_path):
        with open(rec.extracted_text_path, "r", encoding="utf-8") as f:
            text = f.read()
        return {"file_id": rec.id, "filename": rec.filename, "content": text}

    if rec.chunks_path and os.path.exists(rec.chunks_path):
        with open(rec.chunks_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        chunks = data.get("chunks", [])
        text = "\n\n".join(c.get("content", "") for c in chunks)
        return {"file_id": rec.id, "filename": rec.filename, "content": text}

    raise HTTPException(status_code=404, detail="Extracted content not found")


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
