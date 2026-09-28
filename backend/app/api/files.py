import os
import json
import uuid
from pathlib import Path
from typing import Optional, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import FileResponse as FastApiFileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.database import get_db
from app.middleware.auth import get_current_user, get_optional_user
from app.models.user import User
from app.models.file import GeneratedFile
from app.services.rag import RAGService
from app.services.file_intelligence import (
    FileStorageManagerV2,
    FileProcessingState,
    FILE_LIMITS,
    get_recent_provenance,
)
from app.config import settings

router = APIRouter(prefix="/api/files", tags=["files"])


class FileResponse(BaseModel):
    id: str
    fileId: str = ""
    filename: str
    size: int
    content_type: str
    mimeType: str = ""
    detected_format: str = "txt"
    status: str = "READY"
    processing_stage: str = "Ready"
    error: Optional[str] = None
    warnings: list[str] = Field(default_factory=list)
    content_hash: str = ""
    parser: str = ""
    capabilities: dict[str, Any] = Field(default_factory=dict)
    structure_summary: dict[str, Any] = Field(default_factory=dict)
    preview: dict[str, Any] = Field(default_factory=dict)
    text_preview: str = ""
    chunk_count: int = 0
    estimated_tokens: int = 0
    conversation_id: Optional[str] = None
    analysis: Optional[str] = None
    created_at: Optional[str] = None


def _rep_to_file_response(rep) -> FileResponse:
    return FileResponse(
        id=rep.fileId,
        fileId=rep.fileId,
        filename=rep.filename,
        size=rep.size,
        content_type=rep.mimeType,
        mimeType=rep.mimeType,
        detected_format=rep.detectedFormat,
        status=rep.status.value,
        processing_stage=rep.processingStage,
        error=rep.error,
        warnings=rep.warnings,
        content_hash=rep.contentHash,
        parser=rep.parserName,
        capabilities=rep.capabilities.model_dump(),
        structure_summary=rep.structureSummary,
        preview=rep.preview,
        text_preview=rep.textPreview[:500],
        chunk_count=len(rep.chunks),
        estimated_tokens=rep.totalTokensEstimate,
        conversation_id=rep.conversationId,
        analysis=None,
        created_at=rep.createdAt,
    )


@router.post("/upload", response_model=FileResponse)
async def upload_file(
    file: UploadFile = File(...),
    analyze: bool = Form(False),
    conversation_id: Optional[str] = Form(None),
    message_id: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rep = await FileStorageManagerV2.save_upload_stream_and_process(
        upload_file=file,
        user_id=str(current_user.id),
        db=db,
        conversation_id=conversation_id,
        message_id=message_id,
    )

    # Also populate RAGService cache for backward compatibility
    if rep.status in (FileProcessingState.READY, FileProcessingState.PARTIAL) and rep.fullText:
        orig_dir = FileStorageManagerV2.get_original_dir(str(current_user.id))
        matches = list(orig_dir.glob(f"{rep.fileId}*"))
        fpath = str(matches[0]) if matches else ""
        RAGService.cache_file(
            str(current_user.id),
            rep.filename,
            fpath,
            rep.fullText,
            rep.fileId,
        )

    return _rep_to_file_response(rep)


@router.post("/upload-multiple")
async def upload_multiple_files(
    files: list[UploadFile] = File(...),
    analyze: bool = Form(False),
    conversation_id: Optional[str] = Form(None),
    message_id: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if len(files) > FILE_LIMITS.MAX_FILES_PER_MESSAGE:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {FILE_LIMITS.MAX_FILES_PER_MESSAGE} files allowed per upload.",
        )

    results: list[FileResponse] = []
    total_bytes = 0

    for f in files:
        rep = await FileStorageManagerV2.save_upload_stream_and_process(
            upload_file=f,
            user_id=str(current_user.id),
            db=db,
            conversation_id=conversation_id,
            message_id=message_id,
        )
        total_bytes += rep.size
        if total_bytes > FILE_LIMITS.MAX_TOTAL_UPLOAD_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"Total upload size exceeds {FILE_LIMITS.MAX_TOTAL_UPLOAD_SIZE // (1024 * 1024)}MB limit.",
            )
        if rep.status in (FileProcessingState.READY, FileProcessingState.PARTIAL) and rep.fullText:
            orig_dir = FileStorageManagerV2.get_original_dir(str(current_user.id))
            matches = list(orig_dir.glob(f"{rep.fileId}*"))
            fpath = str(matches[0]) if matches else ""
            RAGService.cache_file(
                str(current_user.id),
                rep.filename,
                fpath,
                rep.fullText,
                rep.fileId,
            )
        results.append(_rep_to_file_response(rep))

    return {"files": results}


@router.get("/provenance")
async def list_file_provenance(
    current_user: User = Depends(get_current_user),
):
    """Returns recent file-to-answer provenance instrumentation records."""
    return {"provenance": get_recent_provenance(50)}


@router.get("/conversation/{conversation_id}")
async def list_conversation_files(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all processed files linked to a specific conversation for the authenticated user."""
    reps = await FileStorageManagerV2.get_conversation_files(db, str(current_user.id), conversation_id)
    return {"files": [_rep_to_file_response(r) for r in reps]}


@router.get("/{file_id}/status")
async def get_file_status(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Section 68: Safe status endpoint exposing fileId, status, processingStage, error, metadata."""
    meta = await FileStorageManagerV2.getFileMetadata(db, file_id, str(current_user.id))
    return {
        "fileId": meta["fileId"],
        "filename": meta["filename"],
        "status": meta["status"],
        "processingStage": meta["processingStage"],
        "error": meta["error"],
        "warnings": meta["warnings"],
        "metadata": meta,
    }


@router.post("/{file_id}/retry", response_model=FileResponse)
async def retry_file_processing(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Section 40 & 64: Retry processing a failed file without re-uploading."""
    stmt = select(GeneratedFile).where(GeneratedFile.id == file_id)
    res = await db.execute(stmt)
    rec = res.scalar_one_or_none()
    if not rec or (rec.user_id and str(rec.user_id) != str(current_user.id)):
        raise HTTPException(status_code=404, detail="File not found")
    if not rec.storage_path or not os.path.exists(rec.storage_path):
        raise HTTPException(status_code=404, detail="Original file not found on storage")

    rep = await FileStorageManagerV2.process_stored_file(
        orig_path=rec.storage_path,
        file_id=rec.id,
        user_id=str(current_user.id),
        filename=rec.filename,
        client_mime=rec.mime_type,
        db=db,
        conversation_id=rec.conversation_id,
        force_reprocess=True,
    )
    return _rep_to_file_response(rep)


@router.delete("/{file_id}")
async def delete_uploaded_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(GeneratedFile).where(GeneratedFile.id == file_id)
    res = await db.execute(stmt)
    rec = res.scalar_one_or_none()
    if not rec or (rec.user_id and str(rec.user_id) != str(current_user.id)):
        raise HTTPException(status_code=404, detail="File not found")
    rec.status = FileProcessingState.DELETED.value
    await db.delete(rec)
    await db.commit()
    proc_path = FileStorageManagerV2.get_processed_path(str(current_user.id), file_id)
    try:
        proc_path.unlink(missing_ok=True)
    except Exception:
        pass
    return {"status": "DELETED", "fileId": file_id}


# =========================================================================
# SECTION 69: CONTROLLED FILE CONTENT API ENDPOINTS
# =========================================================================

@router.get("/{file_id}/metadata")
async def api_get_file_metadata(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await FileStorageManagerV2.getFileMetadata(db, file_id, str(current_user.id))


@router.get("/{file_id}/text")
async def api_get_file_text(
    file_id: str,
    max_chars: int = Query(100000, ge=100, le=500000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await FileStorageManagerV2.getFileText(db, file_id, str(current_user.id), max_chars=max_chars)


@router.get("/{file_id}/search")
async def api_search_file(
    file_id: str,
    q: str = Query(..., min_length=1),
    top_k: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await FileStorageManagerV2.searchFile(db, file_id, str(current_user.id), query=q, top_k=top_k)


@router.get("/{file_id}/chunks")
async def api_get_file_chunks(
    file_id: str,
    ids: Optional[str] = Query(None, description="Comma-separated chunkIds"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    chunk_ids = [i.strip() for i in ids.split(",") if i.strip()] if ids else None
    return await FileStorageManagerV2.getFileChunks(db, file_id, str(current_user.id), chunk_ids=chunk_ids)


@router.get("/{file_id}/page/{page}")
async def api_get_file_page(
    file_id: str,
    page: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await FileStorageManagerV2.getFilePage(db, file_id, str(current_user.id), page=page)


@router.get("/{file_id}/spreadsheet")
async def api_get_spreadsheet_range(
    file_id: str,
    sheet: Optional[str] = Query(None),
    range: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await FileStorageManagerV2.getSpreadsheetRange(
        db, file_id, str(current_user.id), sheet=sheet, cell_range=range
    )


@router.get("/{file_id}/code")
async def api_get_code_range(
    file_id: str,
    start: int = Query(1, ge=1),
    end: int = Query(100, ge=1),
    inner_path: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await FileStorageManagerV2.getCodeRange(
        db, file_id, str(current_user.id), start_line=start, end_line=end, inner_path=inner_path
    )


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
                active_user = User(id=str(payload["sub"]), email="", username="user", hashed_password="")

    if not active_user:
        raise HTTPException(status_code=401, detail="Authentication required to download files.")

    stmt = select(GeneratedFile).where(GeneratedFile.id == file_id)
    res = await db.execute(stmt)
    file_record = res.scalar_one_or_none()

    file_path = None
    filename = "download"
    media_type = "application/octet-stream"

    if file_record:
        if file_record.user_id and str(file_record.user_id) != str(active_user.id):
            raise HTTPException(status_code=404, detail="File not found")
        file_path = file_record.storage_path
        filename = file_record.filename
        media_type = file_record.mime_type
    else:
        user_dir = os.path.join(settings.upload_dir, "users", str(active_user.id), "uploads")
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
    """Returns structured preview and design specification data with strict tenant isolation."""
    from app.utils.security import decode_token

    active_user = user
    if not active_user and token:
        payload = decode_token(token)
        if payload and payload.get("sub"):
            u_res = await db.execute(select(User).where(User.id == str(payload["sub"])))
            active_user = u_res.scalar_one_or_none()
            if not active_user:
                active_user = User(id=str(payload["sub"]), email="", username="user", hashed_password="")

    if not active_user:
        raise HTTPException(status_code=401, detail="Authentication required to preview files.")

    stmt = select(GeneratedFile).where(GeneratedFile.id == file_id)
    res = await db.execute(stmt)
    file_record = res.scalar_one_or_none()

    if not file_record or (file_record.user_id and str(file_record.user_id) != str(active_user.id)):
        raise HTTPException(status_code=404, detail="File not found")

    preview_json = {}
    if file_record.preview_data:
        try:
            preview_json = json.loads(file_record.preview_data)
        except Exception:
            pass

    design_json = {}
    if file_record.design_spec:
        try:
            design_json = json.loads(file_record.design_spec)
        except Exception:
            pass

    verification_json = {}
    if getattr(file_record, "verification_result", None):
        try:
            verification_json = json.loads(file_record.verification_result)
        except Exception:
            pass

    ext = file_record.filename.split(".")[-1].lower() if file_record.filename else "file"

    return {
        "file_id": file_record.id,
        "filename": file_record.filename,
        "format": ext,
        "size": file_record.file_size,
        "status": file_record.status,
        "download_url": f"/api/files/{file_record.id}/download",
        "design_spec": design_json,
        "preview": preview_json,
        "verification": verification_json,
    }
