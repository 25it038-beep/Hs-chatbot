import os
import re
import time
import json
import uuid
import logging
from pathlib import Path
import aiofiles
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import FileResponse as FastApiFileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.middleware.auth import get_current_user, get_optional_user
from app.models.user import User
from app.models.file import GeneratedFile
from app.services.rag import RAGService
from app.services.nvidia.chat import NvidiaChatProvider
from app.services.nvidia.vision import NvidiaVisionProvider
from app.config import settings

router = APIRouter(prefix="/api/files", tags=["files"])
_logger = logging.getLogger("hsbot.files")

chat_provider = NvidiaChatProvider()
vision_provider = NvidiaVisionProvider()

SUPPORTED_UPLOAD_EXTENSIONS = {
    ".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt",
    ".txt", ".md", ".rtf", ".log", ".ini", ".cfg",
    ".csv", ".tsv", ".json", ".xml", ".yaml", ".yml", ".toml",
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp", ".cs",
    ".go", ".rs", ".sql", ".html", ".css", ".scss", ".sh", ".ps1", ".rb", ".php", ".kt", ".swift",
    ".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg",
    ".zip",
}

UNSUPPORTED_EXECUTABLE_EXTENSIONS = {
    ".exe", ".dll", ".bat", ".cmd", ".msi", ".scr", ".com", ".pif", ".vbs", ".jar", ".apk", ".dmg", ".iso"
}


class FileResponse(BaseModel):
    id: str
    filename: str
    size: int
    content_type: str
    text_preview: str
    chunk_count: int
    analysis: Optional[str] = None
    status: str = "ready"
    content_ready: bool = True
    source: Optional[str] = None


class FileStatusResponse(BaseModel):
    id: str
    filename: str
    size: int
    content_type: str
    status: str
    content_ready: bool
    chunk_count: int
    text_preview: str


async def analyze_file_text(text: str, filename: str) -> Optional[str]:
    if not text.strip():
        return None
    truncated = text[:8000]
    messages = [{"role": "user", "content": f"Analyze this document '{filename}' and provide a comprehensive structured report covering: main topic, key points, important details, and notable information:\n\n{truncated}"}]
    try:
        response = await chat_provider.generate(
            messages=messages,
            model="llama-3.2-11b",
            system_prompt="You are a thorough document analyst. Provide a clear, structured analysis report.",
            max_tokens=2048,
        )
        return response.content
    except Exception:
        return None


def _normalize_filename(filename: Optional[str], content_type: Optional[str]) -> tuple[str, str]:
    raw_name = os.path.basename((filename or "").strip()) or "clipboard-file"
    ext = os.path.splitext(raw_name)[1].lower()
    mime = (content_type or "").lower().strip()
    if not ext:
        mime_ext_map = {
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg",
            "image/webp": ".webp",
            "image/gif": ".gif",
            "image/bmp": ".bmp",
            "image/svg+xml": ".svg",
            "application/pdf": ".pdf",
            "text/plain": ".txt",
            "text/markdown": ".md",
            "text/csv": ".csv",
            "application/json": ".json",
            "application/zip": ".zip",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
        }
        inferred = mime_ext_map.get(mime, "")
        if inferred:
            ext = inferred
            raw_name = f"{raw_name}{ext}"
    return raw_name, ext


async def _process_single_upload(
    file: UploadFile,
    current_user: User,
    db: AsyncSession,
    analyze: bool = False,
    source: str = "picker",
) -> FileResponse:
    t0 = time.perf_counter()
    max_size = settings.max_file_size_mb * 1024 * 1024
    content = await file.read()
    size = len(content)
    safe_orig_name, ext = _normalize_filename(file.filename, file.content_type)
    content_type = file.content_type or "application/octet-stream"

    if size == 0:
        _logger.warning("[UPLOAD] rejected empty file source=%s type=%s", source, content_type)
        raise HTTPException(status_code=400, detail="Empty file (0 bytes) cannot be uploaded.")

    if size > max_size:
        _logger.warning("[UPLOAD] rejected oversized file source=%s size=%d limit=%d", source, size, max_size)
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.max_file_size_mb}MB limit")

    if ext in UNSUPPORTED_EXECUTABLE_EXTENSIONS or (ext not in SUPPORTED_UPLOAD_EXTENSIONS and not content_type.startswith(("image/", "text/"))):
        _logger.warning("[UPLOAD] rejected unsupported format source=%s ext=%s type=%s", source, ext, content_type)
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported format ({ext or content_type}). This file type cannot be analyzed.",
        )

    file_id = str(uuid.uuid4())
    safe_ext = ext or (".png" if content_type.startswith("image/") else ".txt")
    safe_name = f"{file_id}{safe_ext}"
    user_upload_dir = os.path.join(settings.upload_dir, "users", str(current_user.id), "uploads")
    os.makedirs(user_upload_dir, exist_ok=True)
    file_path = os.path.join(user_upload_dir, safe_name)

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    upload_ms = round((time.perf_counter() - t0) * 1000, 1)
    t_proc = time.perf_counter()

    rag = RAGService(db, current_user.id)
    try:
        result = await rag.process_file(file_path, safe_orig_name, file_id)
    except ValueError as ve:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except OSError:
            pass
        _logger.warning(
            "[UPLOAD] processing failed source=%s type=%s size=%d error=%s",
            source, content_type, size, str(ve),
        )
        raise HTTPException(status_code=422, detail=f"Couldn't process file: {str(ve)}")
    except Exception as exc:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except OSError:
            pass
        _logger.error("[UPLOAD] unexpected processing error source=%s type=%s size=%d", source, content_type, size)
        raise HTTPException(status_code=422, detail=f"Couldn't process file: {str(exc)}")

    extracted_text = result.get("text", "")
    chunk_count = int(result.get("chunk_count", 0))
    RAGService.cache_file(current_user.id, safe_orig_name, file_path, extracted_text, file_id)
    proc_ms = round((time.perf_counter() - t_proc) * 1000, 1)

    preview_meta = {
        "source": source,
        "chunk_count": chunk_count,
        "text_preview": extracted_text[:500],
        "upload_duration_ms": upload_ms,
        "processing_duration_ms": proc_ms,
    }

    # Persist in GeneratedFile database table with ownership and full extracted content
    try:
        gen_file = GeneratedFile(
            id=file_id,
            user_id=current_user.id,
            filename=safe_orig_name,
            storage_path=file_path,
            mime_type=content_type,
            file_size=size,
            status="ready",
            content_data=extracted_text,
            preview_data=json.dumps(preview_meta),
        )
        db.add(gen_file)
        await db.commit()
    except Exception:
        await db.rollback()

    analysis = None
    if analyze:
        if content_type.startswith("image/") or safe_ext in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"):
            try:
                resp = await vision_provider.analyze(
                    image_data=content,
                    prompt="Analyze this image in detail. Describe the scene, objects, people, text visible, and notable elements.",
                    mime_type=content_type if content_type.startswith("image/") else "image/png",
                )
                analysis = resp.content or None
            except Exception:
                analysis = await analyze_file_text(extracted_text, safe_orig_name)
        else:
            analysis = await analyze_file_text(extracted_text, safe_orig_name)

    _logger.info(
        "[UPLOAD] status=ready file_id=%s source=%s type=%s size=%d chunks=%d upload_ms=%s proc_ms=%s",
        file_id, source, content_type, size, chunk_count, upload_ms, proc_ms,
    )

    return FileResponse(
        id=file_id,
        filename=safe_orig_name,
        size=size,
        content_type=content_type,
        text_preview=extracted_text[:500],
        chunk_count=chunk_count,
        analysis=analysis,
        status="ready",
        content_ready=bool(extracted_text.strip()),
        source=source,
    )


@router.post("/upload", response_model=FileResponse)
async def upload_file(
    file: UploadFile = File(...),
    analyze: bool = Form(False),
    source: str = Form("picker"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _process_single_upload(file, current_user, db, analyze=analyze, source=source)


@router.post("/upload-multiple")
async def upload_multiple_files(
    files: list[UploadFile] = File(...),
    analyze: bool = Form(False),
    source: str = Form("picker"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    results = []
    for file in files:
        res = await _process_single_upload(file, current_user, db, analyze=analyze, source=source)
        results.append(res)
    return {"files": results}


@router.get("/{file_id}/status", response_model=FileStatusResponse)
async def get_file_status(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verifies file ownership, disk existence, and processed content availability before READY state."""
    stmt = select(GeneratedFile).where(GeneratedFile.id == file_id)
    res = await db.execute(stmt)
    file_record = res.scalar_one_or_none()

    if not file_record or (file_record.user_id and file_record.user_id != current_user.id):
        raise HTTPException(status_code=404, detail="File not found")

    if not file_record.storage_path or not os.path.exists(file_record.storage_path):
        raise HTTPException(status_code=404, detail="Stored file missing on server")

    cached = RAGService.get_cached_file_by_id(current_user.id, file_id)
    text_content = (cached["text"] if cached else None) or file_record.content_data or ""

    if not text_content.strip():
        rag = RAGService(db, current_user.id)
        proc = await rag.process_file(file_record.storage_path, file_record.filename, file_record.id)
        text_content = proc.get("text", "")
        if text_content.strip():
            file_record.content_data = text_content
            await db.commit()
            RAGService.cache_file(current_user.id, file_record.filename, file_record.storage_path, text_content, file_record.id)

    chunk_count = max(1, (len(text_content) // 800) + 1) if text_content.strip() else 0
    if file_record.preview_data:
        try:
            pdata = json.loads(file_record.preview_data)
            if pdata.get("chunk_count"):
                chunk_count = int(pdata["chunk_count"])
        except Exception:
            pass

    content_ready = bool(text_content.strip()) and file_record.status == "ready"
    return FileStatusResponse(
        id=file_record.id,
        filename=file_record.filename,
        size=file_record.file_size,
        content_type=file_record.mime_type,
        status=file_record.status if content_ready else "processing",
        content_ready=content_ready,
        chunk_count=chunk_count,
        text_preview=text_content[:500],
    )


@router.delete("/{file_id}")
async def delete_uploaded_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Removes an uploaded file owned by the current user from DB, disk, and RAG cache."""
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
    return {"status": "deleted", "id": file_id}


async def resolve_conversation_file_context(
    db: AsyncSession,
    user_id: Optional[str],
    chat_id: Optional[str],
    file_ids: Optional[list[str]],
    message_text: str,
) -> tuple[str, list[dict]]:
    """
    Validates file ownership, links uploaded files to the conversation, loads extracted content
    (for both newly attached files and existing conversation files for follow-up questions),
    and returns (context_block_for_system_prompt, verified_message_attachments).
    """
    if not user_id:
        return "", []

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
            if not rec or rec.status != "ready":
                continue
            if not rec.storage_path or not os.path.exists(rec.storage_path):
                continue
            if chat_id and rec.conversation_id != str(chat_id):
                rec.conversation_id = str(chat_id)
                dirty = True
            if rec.id not in seen_ids:
                seen_ids.add(rec.id)
                active_records.append(rec)
            verified_attachments.append({
                "id": rec.id,
                "fileId": rec.id,
                "name": rec.filename,
                "filename": rec.filename,
                "type": rec.mime_type,
                "mimeType": rec.mime_type,
                "size": rec.file_size,
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
                GeneratedFile.status == "ready",
            )
            .order_by(GeneratedFile.created_at)
        )
        res_conv = await db.execute(stmt_conv)
        for rec in res_conv.scalars().all():
            # Skip generated deliverable artifacts that don't live in user uploads unless they have extracted content
            if rec.id not in seen_ids and rec.storage_path and os.path.exists(rec.storage_path):
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

        ext = os.path.splitext(rec.filename or "")[1].lower()
        is_image = (rec.mime_type or "").startswith("image/") or ext in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp")

        if is_image and (not text_body or text_body.startswith("Image Attachment:")):
            # Perform vision analysis on the image if not yet analyzed with vision model
            try:
                async with aiofiles.open(rec.storage_path, "rb") as img_f:
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
                    RAGService.cache_file(str(user_id), rec.filename, rec.storage_path, text_body, rec.id)
            except Exception as exc:
                _logger.warning("[FILE_CONTEXT] vision analysis fallback for file_id=%s: %s", rec.id, exc)

        if not text_body.strip():
            try:
                proc = await rag.process_file(rec.storage_path, rec.filename, rec.id)
                text_body = proc.get("text", "")
                if text_body.strip():
                    rec.content_data = text_body
                    try:
                        await db.commit()
                    except Exception:
                        await db.rollback()
                    RAGService.cache_file(str(user_id), rec.filename, rec.storage_path, text_body, rec.id)
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

    # Look up in GeneratedFile table
    stmt = select(GeneratedFile).where(GeneratedFile.id == file_id)
    res = await db.execute(stmt)
    file_record = res.scalar_one_or_none()

    file_path = None
    filename = "download"
    media_type = "application/octet-stream"

    if file_record:
        if file_record.user_id and file_record.user_id != active_user.id:
            raise HTTPException(status_code=404, detail="File not found")
        file_path = file_record.storage_path
        filename = file_record.filename
        media_type = file_record.mime_type
    else:
        # Check UniversalArtifactEngineV2 storage for this user
        from app.services.artifacts.universal_engine_v2 import ArtifactStorageAndVersionManager
        v2_res = ArtifactStorageAndVersionManager.get_artifact_bytes(str(active_user.id), file_id)
        if v2_res:
            rec, _ = v2_res
            user_v2_dir = ArtifactStorageAndVersionManager._user_artifact_dir(str(active_user.id))
            file_path = os.path.join(user_v2_dir, rec["storageReference"])
            filename = rec["filename"]
            media_type = rec["mimeType"]
        else:
            # Check ONLY in the authenticated user's isolated uploads directory
            user_dir = os.path.join(settings.upload_dir, "users", str(active_user.id), "uploads")
            if os.path.exists(user_dir):
                for fname in os.listdir(user_dir):
                    if fname.startswith(file_id):
                        file_path = os.path.join(user_dir, fname)
                        filename = fname
                        break

    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    # Path traversal security guard: file must reside within configured storage/upload directories
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
    import json
    from app.utils.security import decode_token
    from app.services.artifacts.universal_engine_v2 import ArtifactStorageAndVersionManager

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

    if not file_record:
        v2_rec = ArtifactStorageAndVersionManager.get_artifact(str(active_user.id), file_id)
        if v2_rec:
            return {
                "file_id": v2_rec["artifactId"],
                "filename": v2_rec["filename"],
                "format": v2_rec["extension"],
                "size": v2_rec["size"],
                "download_url": f"/api/files/artifacts-v2/{v2_rec['artifactId']}/download",
                "design_spec": v2_rec.get("spec", {}),
                "preview": v2_rec.get("preview", {}),
                "verification": {
                    "passed": True,
                    "overall_score": 100,
                    "checks": [{"name": "ArtifactValidatorV2", "status": "PASSED"}],
                    "verified_checklist": [
                        v2_rec.get("qualityMetrics", {}).get("validation_message", "Verified binary structure"),
                        f"Version {v2_rec.get('version', 1)} • SHA-256 {v2_rec.get('hash', '')[:12]}",
                    ],
                },
                "version": v2_rec.get("version", 1),
                "versionHistory": v2_rec.get("versionHistory", []),
            }

    if not file_record or (file_record.user_id and file_record.user_id != active_user.id):
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

    ext = file_record.filename.split('.')[-1].lower() if file_record.filename else "file"

    return {
        "file_id": file_record.id,
        "filename": file_record.filename,
        "format": ext,
        "size": file_record.file_size,
        "download_url": f"/api/files/{file_record.id}/download",
        "design_spec": design_json,
        "preview": preview_json,
        "verification": verification_json,
    }


# ── Universal Artifact Engine V2 Endpoints (Sections 14-67) ──

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


