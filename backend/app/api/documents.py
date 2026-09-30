from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.message import Message
from app.models.chat import Chat
import os
import re
import uuid
from app.services.document_service import document_service
from app.services.document_service.service import normalize_format
from app.services.workspace.files import save_file, get_chat_workspace_dir
from app.config import settings

router = APIRouter(prefix="/api/documents", tags=["documents"])


class GenerateRequest(BaseModel):
    title: Optional[str] = "AI Chat Responses"
    content: Optional[Any] = None
    responses: Optional[List[str]] = None
    ai_responses: Optional[List[str]] = None
    format: str  # any format: pdf, docx, pptx, xlsx, csv, tsv, md, txt, html, json, xml, yaml, rtf, tex, py, js, sql, or custom ext
    filename: Optional[str] = None
    chat_id: Optional[str] = None
    message_id: Optional[str] = None
    include_all_responses: Optional[bool] = False


@router.post("/generate")
async def generate_document(
    req: GenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    chat_id = req.chat_id or str(uuid.uuid4())
    fmt = normalize_format(req.format)
    title = (req.title or "AI Chat Responses").strip() or "AI Chat Responses"

    ai_responses: List[str] = []
    if req.ai_responses:
        ai_responses.extend([r for r in req.ai_responses if isinstance(r, str) and r.strip()])
    if req.responses:
        ai_responses.extend([r for r in req.responses if isinstance(r, str) and r.strip()])
    if not ai_responses and isinstance(req.content, str) and req.content.strip():
        ai_responses.append(req.content.strip())
    elif not ai_responses and isinstance(req.content, dict) and req.content.get("aiResponses"):
        ai_responses.extend([
            r for r in req.content.get("aiResponses", [])
            if isinstance(r, str) and r.strip()
        ])

    # If chat_id is provided and either no content was sent or include_all_responses=True, load AI responses from the chat
    if req.chat_id and (not ai_responses or req.include_all_responses):
        chat_res = await db.execute(
            select(Chat).where(Chat.id == req.chat_id, Chat.user_id == str(current_user.id))
        )
        chat_obj = chat_res.scalar_one_or_none()
        if chat_obj:
            if title == "AI Chat Responses" and chat_obj.title and chat_obj.title != "New Chat":
                title = chat_obj.title
            stmt = select(Message).where(Message.chat_id == req.chat_id, Message.role == "assistant").order_by(Message.created_at)
            msg_res = await db.execute(stmt)
            db_msgs = msg_res.scalars().all()
            if req.message_id:
                db_msgs = [m for m in db_msgs if str(m.id) == str(req.message_id)]
            db_texts = [
                m.content.strip()
                for m in db_msgs
                if m.content and m.content.strip() and not m.content.strip().startswith("Done — ")
            ]
            if db_texts:
                ai_responses = db_texts

    if not ai_responses:
        if isinstance(req.content, str) and req.content.strip():
            ai_responses = [req.content.strip()]
        else:
            ai_responses = [f"# {title}"]

    safe_base = re.sub(r'[^a-zA-Z0-9_\- ]', '', (req.filename or title).rsplit('.', 1)[0]).strip()
    safe_base = re.sub(r'\s+', '_', safe_base)[:50] or "AI_Chat_Responses"
    if safe_base.lower().endswith(f".{fmt}"):
        filename = safe_base
    else:
        filename = f"{safe_base}.{fmt}"

    if isinstance(req.content, dict) and req.content.get("sections"):
        structured = dict(req.content)
        structured.setdefault("title", title)
        if ai_responses and not structured.get("ai_responses"):
            structured["ai_responses"] = ai_responses
    else:
        structured = document_service.parse_ai_responses_to_content(ai_responses, fmt, title)

    file_info = await document_service.generate_file(
        fmt=fmt,
        filename=filename,
        title=title,
        content=structured,
        conversation_id=str(chat_id),
        user_id=str(current_user.id),
        db=db,
        user_prompt=title,
    )

    return {
        "id": file_info["id"],
        "name": file_info["filename"],
        "filename": file_info["filename"],
        "path": file_info["path"],
        "format": fmt,
        "type": file_info["mime_type"],
        "mime_type": file_info["mime_type"],
        "size": file_info["file_size"],
        "file_size": file_info["file_size"],
        "url": file_info["download_url"],
        "download_url": file_info["download_url"],
        "preview_data": file_info.get("preview_data"),
        "verification": file_info.get("verification"),
        "chat_id": chat_id,
    }

@router.get("/conversations/{chat_id}/files")
async def list_files(chat_id: str, current_user: User = Depends(get_current_user)):
    workspace = get_chat_workspace_dir(str(current_user.id), chat_id)
    if not os.path.exists(workspace):
        return {"files": []}
    files = []
    for f in os.listdir(workspace):
        fp = os.path.join(workspace, f)
        if os.path.isfile(fp):
            files.append({
                "filename": f,
                "size": os.path.getsize(fp),
                "path": fp
            })
    return {"files": files}

@router.get("/download")
async def download_file(chat_id: str, filename: str, current_user: User = Depends(get_current_user)):
    safe_filename = os.path.basename(filename)
    workspace = get_chat_workspace_dir(str(current_user.id), chat_id)
    fp = os.path.join(workspace, safe_filename)
    resolved = os.path.abspath(fp)
    if not resolved.startswith(os.path.abspath(workspace)) or not os.path.isfile(resolved):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=resolved, filename=safe_filename)
