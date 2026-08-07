import os
import uuid
import aiofiles
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.services.rag import RAGService
from app.services.nvidia.chat import NvidiaChatProvider
from app.config import settings

router = APIRouter(prefix="/api/files", tags=["files"])

chat_provider = NvidiaChatProvider()


class FileResponse(BaseModel):
    id: str
    filename: str
    size: int
    content_type: str
    text_preview: str
    chunk_count: int
    analysis: Optional[str] = None


async def analyze_file_text(text: str, filename: str) -> Optional[str]:
    if not text.strip():
        return None
    truncated = text[:8000]
    messages = [{"role": "user", "content": f"Analyze this document '{filename}' and provide a comprehensive structured report covering: main topic, key points, important details, and notable information:\n\n{truncated}"}]
    try:
        response = await chat_provider.generate(
            messages=messages,
            model="glm-5.2",
            system_prompt="You are a thorough document analyst. Provide a clear, structured analysis report.",
            max_tokens=2048,
        )
        return response.content
    except Exception:
        return None


@router.post("/upload", response_model=FileResponse)
async def upload_file(
    file: UploadFile = File(...),
    analyze: bool = Form(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    max_size = settings.max_file_size_mb * 1024 * 1024
    content = await file.read()
    if len(content) > max_size:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.max_file_size_mb}MB limit")

    file_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename or "unknown")[1] or ".bin"
    safe_name = f"{file_id}{ext}"
    file_path = os.path.join(settings.upload_dir, safe_name)

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    rag = RAGService(db, current_user.id)
    result = await rag.process_file(file_path, file.filename or "unknown", file_id)

    RAGService.cache_file(current_user.id, file.filename or "unknown", file_path, result["text"], file_id)

    analysis = await analyze_file_text(result["text"], file.filename or "unknown") if analyze else None

    return FileResponse(
        id=file_id,
        filename=file.filename or "unknown",
        size=len(content),
        content_type=file.content_type or "application/octet-stream",
        text_preview=result["text"][:500],
        chunk_count=result["chunk_count"],
        analysis=analysis,
    )


@router.post("/upload-multiple")
async def upload_multiple_files(
    files: list[UploadFile] = File(...),
    analyze: bool = Form(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    results = []
    for file in files:
        max_size = settings.max_file_size_mb * 1024 * 1024
        content = await file.read()
        if len(content) > max_size:
            continue
        file_id = str(uuid.uuid4())
        ext = os.path.splitext(file.filename or "unknown")[1] or ".bin"
        safe_name = f"{file_id}{ext}"
        file_path = os.path.join(settings.upload_dir, safe_name)
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)
        rag = RAGService(db, current_user.id)
        result = await rag.process_file(file_path, file.filename or "unknown", file_id)
        analysis = await analyze_file_text(result["text"], file.filename or "unknown") if analyze else None
        results.append(FileResponse(
            id=file_id,
            filename=file.filename or "unknown",
            size=len(content),
            content_type=file.content_type or "application/octet-stream",
            text_preview=result["text"][:500],
            chunk_count=result["chunk_count"],
            analysis=analysis,
        ))
    return {"files": results}
