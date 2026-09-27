"""API endpoints for AI Video Generation, Streaming, Jobs, and History."""

import os
from typing import Optional, List
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    File,
    status,
)
from fastapi.responses import StreamingResponse, FileResponse as FastApiFileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.middleware.auth import get_current_user, get_optional_user
from app.utils.security import decode_token
from app.services.video.schemas import (
    VideoGenerationRequest,
    VideoJobResponse,
    EnhancePromptRequest,
    EnhancePromptResponse,
    VideoModelCapability,
)
from app.services.video.models import model_registry
from app.services.video.jobs import video_job_manager
from app.services.video.storage import video_storage
from app.services.video.health import video_health
from app.services.video.enhancer import prompt_enhancer

router = APIRouter(prefix="/api/video", tags=["video"])


async def _resolve_user(token: Optional[str], user: Optional[User], db: AsyncSession) -> User:
    """Resolves active user from Bearer header or query token parameter."""
    if user:
        return user
    if token:
        payload = decode_token(token)
        if payload and payload.get("sub"):
            u_res = await db.execute(select(User).where(User.id == str(payload["sub"])))
            active_user = u_res.scalar_one_or_none()
            if active_user:
                return active_user
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")


@router.get("/health")
async def get_video_health():
    """Returns video subsystem health and provider availability."""
    return await video_health.get_system_health()


@router.get("/models", response_model=List[VideoModelCapability])
async def list_video_models():
    """Lists available video generation models and capabilities."""
    return model_registry.list_models()


@router.post("/enhance-prompt", response_model=EnhancePromptResponse)
async def enhance_video_prompt(
    req: EnhancePromptRequest,
    current_user: User = Depends(get_current_user),
):
    """Enhances user prompt with cinematic lighting, camera movement, and aesthetic grammar."""
    return prompt_enhancer.enhance(req.prompt, req.style or "cinematic")


@router.post("/upload-reference")
async def upload_reference_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Uploads a reference starting frame for Image-to-Video generation."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are accepted as video references.")

    content = await file.read()
    if len(content) > 15 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Reference image exceeds 15MB limit.")

    ref_id, path = video_storage.save_reference_image(
        user_id=current_user.id,
        image_bytes=content,
        original_filename=file.filename or "reference.png",
    )
    return {
        "reference_image_id": ref_id,
        "filename": file.filename,
        "size": len(content),
    }


@router.post("/generate", response_model=VideoJobResponse)
async def generate_video(
    req: VideoGenerationRequest,
    current_user: User = Depends(get_current_user),
):
    """Enqueues an asynchronous video generation job."""
    if not model_registry.is_valid_model(req.model):
        raise HTTPException(status_code=400, detail=f"Unsupported model '{req.model}'.")

    job = await video_job_manager.create_job(current_user.id, req)
    return job


@router.get("/jobs/{job_id}", response_model=VideoJobResponse)
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
):
    """Queries live execution state and elapsed time of a video job."""
    job = await video_job_manager.get_job(job_id, current_user.id)
    if not job:
        raise HTTPException(status_code=404, detail="Video job not found.")
    return job


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
):
    """Cancels a queued or executing video generation job."""
    success = await video_job_manager.cancel_job(job_id, current_user.id)
    if not success:
        raise HTTPException(status_code=400, detail="Job cannot be cancelled (it may already be completed or not exist).")
    return {"status": "cancelled", "job_id": job_id}


@router.get("/jobs", response_model=List[VideoJobResponse])
async def list_jobs(
    current_user: User = Depends(get_current_user),
):
    """Returns active and historical video generation jobs for the authenticated user."""
    return await video_job_manager.list_user_jobs(current_user.id)


@router.delete("/jobs/{job_id}")
async def delete_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
):
    """Deletes a video job and associated MP4 file."""
    deleted = await video_job_manager.delete_job(job_id, current_user.id)
    return {"status": "deleted" if deleted else "not_found", "job_id": job_id}


@router.get("/{job_id}/stream")
async def stream_video(
    job_id: str,
    request: Request,
    token: Optional[str] = Query(None),
    user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Range-streaming video endpoint (HTTP 206 Partial Content).
    Enables native HTML5 video player scrubbing, seeking, and buffering.
    """
    active_user = await _resolve_user(token, user, db)

    file_path = video_storage.get_video_path(active_user.id, job_id)
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Video file not found.")

    file_size = os.path.getsize(file_path)
    range_header = request.headers.get("range")

    if not range_header:
        # Full content response
        return FastApiFileResponse(
            path=file_path,
            media_type="video/mp4",
            headers={
                "Accept-Ranges": "bytes",
                "Content-Length": str(file_size),
            },
        )

    # Parse Range: bytes=start-end
    try:
        range_spec = range_header.replace("bytes=", "").strip()
        parts = range_spec.split("-")
        start = int(parts[0]) if parts[0] else 0
        end = int(parts[1]) if len(parts) > 1 and parts[1] else file_size - 1
        start = max(0, min(start, file_size - 1))
        end = max(start, min(end, file_size - 1))
        chunk_size = end - start + 1
    except Exception:
        raise HTTPException(status_code=416, detail="Requested range not satisfiable")

    def _file_chunk_generator(path: str, offset: int, length: int):
        with open(path, "rb") as f:
            f.seek(offset)
            remaining = length
            buffer_size = 64 * 1024
            while remaining > 0:
                read_amount = min(remaining, buffer_size)
                data = f.read(read_amount)
                if not data:
                    break
                remaining -= len(data)
                yield data

    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(chunk_size),
        "Content-Type": "video/mp4",
    }

    return StreamingResponse(
        _file_chunk_generator(file_path, start, chunk_size),
        status_code=206,
        headers=headers,
    )


@router.get("/{job_id}/download")
async def download_video(
    job_id: str,
    token: Optional[str] = Query(None),
    user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Downloads the MP4 video with attachment headers."""
    active_user = await _resolve_user(token, user, db)

    file_path = video_storage.get_video_path(active_user.id, job_id)
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Video file not found.")

    return FastApiFileResponse(
        path=file_path,
        media_type="video/mp4",
        filename=f"{job_id}.mp4",
        headers={"Content-Disposition": f'attachment; filename="{job_id}.mp4"'},
    )
