import json
import os
from pathlib import Path
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.services.agent.orchestrator import AgentOrchestrator
from app.services.agent.prompt_understanding import PromptUnderstandingEngine
from app.services.workspace.workspace import get_workspace
from app.services.artifacts.engine import artifact_engine, SecretLeakDetectedError

router = APIRouter(prefix="/api/agent", tags=["Agent"])

class RunAgentRequest(BaseModel):
    prompt: str
    workspace_id: Optional[str] = "default"
    chat_id: Optional[str] = None
    autonomy_mode: Optional[str] = "AUTO"
    model: Optional[str] = "llama-3.1-70b"

class PlanRequest(BaseModel):
    prompt: str
    workspace_id: Optional[str] = "default"

class UnderstandPromptRequest(BaseModel):
    prompt: str
    workspace_id: Optional[str] = "default"
    target_file: Optional[str] = None
    scope: Optional[str] = "workspace"

class FileWriteRequest(BaseModel):
    path: str
    content: str
    workspace_id: Optional[str] = "default"

class FileEditRequest(BaseModel):
    path: str
    target_content: str
    replacement_content: str
    workspace_id: Optional[str] = "default"

class TerminalCommandRequest(BaseModel):
    command: str
    workspace_id: Optional[str] = "default"
    timeout: Optional[int] = 30

@router.get("/state")
async def get_agent_state(
    workspace_id: str = "default",
    user: User = Depends(get_current_user)
):
    orchestrator = AgentOrchestrator(workspace_id=workspace_id)
    summary = orchestrator.repo_intel.summarize_context()
    return {
        "status": orchestrator.state,
        "workspace_id": workspace_id,
        "context": summary,
        "autonomy_mode": orchestrator.autonomy_mode
    }

@router.post("/plan")
async def plan_agent_task(
    req: PlanRequest,
    user: User = Depends(get_current_user)
):
    orchestrator = AgentOrchestrator(workspace_id=req.workspace_id)
    plan = await orchestrator.generate_plan(req.prompt)
    return {
        "success": True,
        "plan": plan.to_dict()
    }

@router.post("/understand-prompt")
async def understand_user_prompt(
    req: UnderstandPromptRequest,
    user: User = Depends(get_current_user)
):
    """
    Analyzes prompt through the 48-section HSBOT Prompt Understanding Pipeline.
    Runs BEFORE requirement discovery, adaptive quiz, tool calling, or execution.
    """
    orchestrator = AgentOrchestrator(workspace_id=req.workspace_id)
    engine = PromptUnderstandingEngine(orchestrator.repo_intel.summarize_context())
    understanding = engine.analyze(
        prompt=req.prompt,
        target_file=req.target_file,
        scope=req.scope or "workspace"
    )
    return {
        "success": True,
        "understanding": understanding.to_dict()
    }

@router.post("/run")
async def run_agent(
    req: RunAgentRequest,
    user: User = Depends(get_current_user)
):
    """
    Executes the autonomous agent engineering loop and streams progress events as SSE chunks.
    """
    orchestrator = AgentOrchestrator(
        workspace_id=req.workspace_id,
        autonomy_mode=req.autonomy_mode
    )

    async def event_generator():
        try:
            async for chunk in orchestrator.run_autonomous_loop(
                user_request=req.prompt,
                chat_id=req.chat_id,
                user_id=user.id,
                model=req.model or "llama-3.1-70b"
            ):
                data = json.dumps(chunk)
                yield f"data: {data}\n\n"
        except SecretLeakDetectedError as leak_err:
            err_data = json.dumps({
                "type": "error",
                "message": str(leak_err),
                "blocked": True
            })
            yield f"data: {err_data}\n\n"
        except Exception as e:
            err_data = json.dumps({
                "type": "error",
                "message": str(e)
            })
            yield f"data: {err_data}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/workspace/tree")
async def get_workspace_tree(
    workspace_id: str = "default",
    user: User = Depends(get_current_user)
):
    ws = get_workspace(workspace_id)
    return ws.get_project_structure()

@router.get("/workspace/file")
async def read_workspace_file(
    path: str = Query(..., description="Relative file path"),
    workspace_id: str = "default",
    start_line: Optional[int] = None,
    end_line: Optional[int] = None,
    user: User = Depends(get_current_user)
):
    ws = get_workspace(workspace_id)
    res = ws.read_file(path, start_line=start_line, end_line=end_line)
    if not res.get("success"):
        raise HTTPException(status_code=404, detail=res.get("error"))
    return res

@router.post("/workspace/file")
async def write_workspace_file(
    req: FileWriteRequest,
    user: User = Depends(get_current_user)
):
    ws = get_workspace(req.workspace_id)
    res = ws.write_file(req.path, req.content)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res

@router.post("/workspace/file/edit")
async def edit_workspace_file(
    req: FileEditRequest,
    user: User = Depends(get_current_user)
):
    ws = get_workspace(req.workspace_id)
    res = ws.edit_file(req.path, req.target_content, req.replacement_content)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res

@router.delete("/workspace/file")
async def delete_workspace_file(
    path: str = Query(..., description="Relative file path"),
    workspace_id: str = "default",
    user: User = Depends(get_current_user)
):
    ws = get_workspace(workspace_id)
    res = ws.delete_file(path)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res

@router.get("/workspace/download-zip")
async def download_workspace_zip(
    workspace_id: str = "default",
    user: User = Depends(get_current_user)
):
    ws = get_workspace(workspace_id)
    zip_res = artifact_engine.create_zip_project(
        workspace_dir=ws.root,
        zip_filename=f"{workspace_id}-workspace.zip",
        user_id=user.id
    )
    if not zip_res.get("success"):
        raise HTTPException(status_code=500, detail="Failed to create workspace archive")
    record = zip_res["artifact"]
    file_path = Path(record["storage_path"])
    return FileResponse(
        path=file_path,
        filename=record["filename"],
        media_type="application/zip"
    )

@router.post("/workspace/terminal")
async def run_terminal_command(
    req: TerminalCommandRequest,
    user: User = Depends(get_current_user)
):
    from app.services.agent.terminal import TerminalAgent
    ws = get_workspace(req.workspace_id)
    term = TerminalAgent(ws.root)
    result = await term.execute(req.command, timeout_seconds=req.timeout or 30)
    return result

@router.get("/artifacts")
async def list_artifacts(
    chat_id: Optional[str] = None,
    user: User = Depends(get_current_user)
):
    artifacts = artifact_engine.list_artifacts(chat_id=chat_id)
    return {"artifacts": artifacts}

@router.get("/artifacts/{artifact_id}/download")
async def download_artifact(
    artifact_id: str,
    user: User = Depends(get_current_user)
):
    record = artifact_engine.get_artifact(artifact_id)
    if not record:
        raise HTTPException(status_code=404, detail="Artifact not found")

    file_path = Path(record["storage_path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File missing from storage")

    return FileResponse(
        path=file_path,
        filename=record["filename"],
        media_type=record.get("mime_type", "application/octet-stream")
    )

@router.get("/artifacts/{artifact_id}/preview")
async def get_artifact_preview(
    artifact_id: str,
    user: User = Depends(get_current_user)
):
    from app.services.artifacts.preview import artifact_preview
    res = artifact_preview.get_preview(artifact_id)
    if not res:
        raise HTTPException(status_code=404, detail="Artifact preview unavailable")
    return res

@router.get("/artifacts/{artifact_id}/content")
async def get_artifact_content(
    artifact_id: str,
    user: User = Depends(get_current_user)
):
    from app.services.artifacts.preview import artifact_preview
    res = artifact_preview.get_content(artifact_id)
    if not res:
        raise HTTPException(status_code=404, detail="Artifact content unavailable")
    return res

@router.get("/artifacts/{artifact_id}/versions")
async def get_artifact_versions(
    artifact_id: str,
    user: User = Depends(get_current_user)
):
    from app.services.artifacts.registry import artifact_registry
    art = artifact_registry.get(artifact_id)
    if not art:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return {"artifact_id": art.artifact_id, "current_version": art.version, "versions": [v.to_dict() for v in art.versions]}

class ArtifactEditRequest(BaseModel):
    instruction: str
    target: Optional[str] = None

@router.post("/artifacts/{artifact_id}/edit")
async def edit_artifact_route(
    artifact_id: str,
    req: ArtifactEditRequest,
    user: User = Depends(get_current_user)
):
    from app.services.artifacts.editor import artifact_editor
    success, art, msg = await artifact_editor.edit_artifact(artifact_id, req.instruction, req.target)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "artifact": art.to_dict(), "message": msg}

@router.post("/artifacts/{artifact_id}/restore/{version}")
async def restore_artifact_version_route(
    artifact_id: str,
    version: int,
    user: User = Depends(get_current_user)
):
    from app.services.artifacts.registry import artifact_registry
    art = artifact_registry.restore_version(artifact_id, version)
    if not art:
        raise HTTPException(status_code=400, detail=f"Could not restore version {version}")
    return {"success": True, "artifact": art.to_dict()}

class ArtifactConvertRequest(BaseModel):
    target_format: str

@router.post("/artifacts/{artifact_id}/convert")
async def convert_artifact_route(
    artifact_id: str,
    req: ArtifactConvertRequest,
    user: User = Depends(get_current_user)
):
    from app.services.artifacts.editor import artifact_editor
    success, art, msg = await artifact_editor.convert_artifact(artifact_id, req.target_format)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "artifact": art.to_dict(), "message": msg}

