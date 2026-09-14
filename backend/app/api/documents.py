from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict
from app.middleware.auth import get_current_user
from app.models.user import User
import os, uuid
from app.services.document_service.pdf import generate_simple_pdf
from app.services.document_service.docx import generate_simple_docx
from app.services.document_service.pptx import generate_simple_pptx
from app.services.document_service.xlsx import generate_simple_xlsx
from app.services.document_service.csv import generate_csv
from app.services.document_service.markdown import generate_simple_markdown
from app.services.workspace.files import save_file, get_chat_workspace_dir
from app.config import settings

router = APIRouter(prefix="/api/documents", tags=["documents"])

class GenerateRequest(BaseModel):
    title: str
    content: str
    format: str  # pdf, docx, pptx, xlsx, csv, md
    chat_id: Optional[str] = None

@router.post("/generate")
async def generate_document(req: GenerateRequest, current_user: User = Depends(get_current_user)):
    chat_id = req.chat_id or str(uuid.uuid4())
    workspace = get_chat_workspace_dir(str(current_user.id), chat_id)
    os.makedirs(workspace, exist_ok=True)
    
    file_id = str(uuid.uuid4())
    fmt = req.format.lower()
    
    if fmt == "pdf":
        filename = f"{file_id}.pdf"
        path = os.path.join(workspace, filename)
        generate_simple_pdf(req.content, path, req.title)
    elif fmt == "docx":
        filename = f"{file_id}.docx"
        path = os.path.join(workspace, filename)
        generate_simple_docx(req.title, req.content, path)
    elif fmt == "pptx":
        filename = f"{file_id}.pptx"
        path = os.path.join(workspace, filename)
        bullets = [p.strip("- ") for p in req.content.split("\n") if p.strip()]
        from app.services.document_service.pptx import generate_simple_pptx
        generate_simple_pptx(req.title, bullets or ["Content"], path)
    elif fmt == "xlsx":
        filename = f"{file_id}.xlsx"
        path = os.path.join(workspace, filename)
        # simple single sheet from text lines
        data = [req.content.split("\n")]
        generate_simple_xlsx(req.title, data, path)
    elif fmt == "csv":
        filename = f"{file_id}.csv"
        path = os.path.join(workspace, filename)
        rows = [line.split(",") for line in req.content.split("\n")]
        generate_csv(rows, path)
    elif fmt in ["md", "markdown"]:
        filename = f"{file_id}.md"
        path = os.path.join(workspace, filename)
        generate_simple_markdown(req.title, req.content, path)
    else:
        raise HTTPException(status_code=400, detail="Unsupported format")
    
    return {
        "id": file_id,
        "filename": filename,
        "path": path,
        "format": fmt,
        "chat_id": chat_id
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
