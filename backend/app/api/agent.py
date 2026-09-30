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
    model: Optional[str] = "llama-3.2-11b"
    engine_version: Optional[str] = "v2"
    answers: Optional[Dict[str, str]] = None

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

class ClassifyModeRequest(BaseModel):
    prompt: str

@router.post("/classify-mode")
async def classify_chat_mode(
    req: ClassifyModeRequest,
    user: User = Depends(get_current_user)
):
    """
    Classifies prompt between GENERAL_CHAT and AGENT mode.
    Guides the UI to activate autonomous realization when an application creation imperative is detected.
    """
    from app.services.agent.mode_classifier import agent_mode_classifier
    result = agent_mode_classifier.classify(req.prompt)
    return {
        "success": True,
        "classification": result.to_dict()
    }

@router.get("/models")
async def get_agent_models(
    user: User = Depends(get_current_user)
):
    """Returns the Agent Model Registry status, capabilities, and health metrics."""
    from app.services.agent.model_router import agent_model_registry
    return {
        "success": True,
        "registry": agent_model_registry.get_status()
    }

@router.get("/roles")
async def get_agent_roles(
    user: User = Depends(get_current_user)
):
    """Returns the complete Virtual Engineering Organization role directory with assigned models and responsibilities."""
    from app.services.agent_v2.models.role_router import AgentRoleRouter
    return {
        "success": True,
        "roles": AgentRoleRouter.get_role_manifest()
    }

@router.post("/models/{model_id}/reset-health")
async def reset_model_health(
    model_id: str,
    user: User = Depends(get_current_user)
):
    """Resets the circuit breaker and health state for a specific agent model."""
    from app.services.agent.model_router import agent_model_registry
    agent_model_registry.reset_health(model_id)
    return {
        "success": True,
        "message": f"Circuit breaker and health reset for model '{model_id}'."
    }

@router.get("/state")
async def get_agent_state(
    workspace_id: str = "default",
    user: User = Depends(get_current_user)
):
    orchestrator = AgentOrchestrator(workspace_id=workspace_id, user_id=user.id)
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
    from app.services.agent_v2.understanding.sufficiency import RequirementSufficiencyEngine
    from app.services.agent_v2.dna.dna_engine import ProductDNAEngine
    from app.services.agent_v2.planning.planner import ImplementationPlanner

    spec = RequirementSufficiencyEngine.generate_product_specification(req.prompt)
    dna, tech_stack = ProductDNAEngine.build_dna(spec, req.prompt)
    plan = ImplementationPlanner.generate_plan(spec, dna, tech_stack)
    is_valid, validation_errors = ImplementationPlanner.validate_plan(plan)

    return {
        "success": True,
        "plan": plan.to_dict(),
        "is_valid": is_valid,
        "validation_errors": validation_errors,
        "specification": spec.to_dict(),
        "dna": dna.to_dict(),
        "tech_stack": tech_stack.to_dict()
    }

@router.post("/understand-prompt")
async def understand_user_prompt(
    req: UnderstandPromptRequest,
    user: User = Depends(get_current_user)
):
    """
    Analyzes prompt through the Agent V2 Requirement Sufficiency and Product Specification Engine.
    Evaluates requirement completeness, detects missing criteria, and determines adaptive questions.
    """
    from app.services.agent_v2.understanding.sufficiency import RequirementSufficiencyEngine
    is_sufficient, classified, question = RequirementSufficiencyEngine.evaluate(req.prompt)
    spec = RequirementSufficiencyEngine.generate_product_specification(req.prompt)

    return {
        "success": True,
        "is_sufficient": is_sufficient,
        "classified_requirements": classified,
        "adaptive_question": question.to_dict() if question else None,
        "specification": spec.to_dict()
    }

@router.post("/run")
async def run_agent(
    req: RunAgentRequest,
    user: User = Depends(get_current_user)
):
    """
    Executes the autonomous agent engineering loop via AgentOrchestratorV2 and streams
    all 16 lifecycle stages as real-time SSE chunks.
    """
    from app.services.agent_v2.orchestrator import AgentOrchestratorV2
    orch_v2 = AgentOrchestratorV2(workspace_id=req.workspace_id)

    async def event_generator_v2():
        try:
            async for chunk in orch_v2.run_lifecycle(
                user_request=req.prompt,
                chat_id=req.chat_id,
                user_id=user.id,
                answers=req.answers
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

    return StreamingResponse(event_generator_v2(), media_type="text/event-stream")

@router.get("/workspace/tree")
async def get_workspace_tree(
    workspace_id: str = "default",
    user: User = Depends(get_current_user)
):
    ws = get_workspace(workspace_id, user_id=user.id)
    return ws.get_project_structure()

@router.get("/workspace/file")
async def read_workspace_file(
    path: str = Query(..., description="Relative file path"),
    workspace_id: str = "default",
    start_line: Optional[int] = None,
    end_line: Optional[int] = None,
    user: User = Depends(get_current_user)
):
    ws = get_workspace(workspace_id, user_id=user.id)
    res = ws.read_file(path, start_line=start_line, end_line=end_line)
    if not res.get("success"):
        raise HTTPException(status_code=404, detail=res.get("error"))
    return res

@router.post("/workspace/file")
async def write_workspace_file(
    req: FileWriteRequest,
    user: User = Depends(get_current_user)
):
    ws = get_workspace(req.workspace_id, user_id=user.id)
    res = ws.write_file(req.path, req.content)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res

@router.post("/workspace/file/edit")
async def edit_workspace_file(
    req: FileEditRequest,
    user: User = Depends(get_current_user)
):
    ws = get_workspace(req.workspace_id, user_id=user.id)
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
    ws = get_workspace(workspace_id, user_id=user.id)
    res = ws.delete_file(path)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res

@router.get("/workspace/download-zip")
async def download_workspace_zip(
    workspace_id: str = "default",
    user: User = Depends(get_current_user)
):
    ws = get_workspace(workspace_id, user_id=user.id)
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
    ws = get_workspace(req.workspace_id, user_id=user.id)
    term = TerminalAgent(ws.root)
    result = await term.execute(req.command, timeout_seconds=req.timeout or 30)
    return result

@router.get("/artifacts")
async def list_artifacts(
    chat_id: Optional[str] = None,
    user: User = Depends(get_current_user)
):
    artifacts = artifact_engine.list_artifacts(chat_id=chat_id, user_id=user.id)
    return {"artifacts": artifacts}

@router.get("/artifacts/{artifact_id}/download")
async def download_artifact(
    artifact_id: str,
    user: User = Depends(get_current_user)
):
    record = artifact_engine.get_artifact(artifact_id)
    if not record:
        from app.services.artifacts.universal_engine_v2 import ArtifactStorageAndVersionManager
        v2_res = ArtifactStorageAndVersionManager.get_artifact_bytes(str(user.id), artifact_id)
        if v2_res:
            rec, _ = v2_res
            user_v2_dir = ArtifactStorageAndVersionManager._user_artifact_dir(str(user.id))
            file_path = Path(user_v2_dir) / rec["storageReference"]
            if file_path.exists():
                return FileResponse(
                    path=file_path,
                    filename=rec["filename"],
                    media_type=rec.get("mimeType", "application/octet-stream"),
                )
    if not record or (record.get("user_id") and record["user_id"] != user.id):
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
    from app.services.artifacts.registry import artifact_registry
    art = artifact_registry.get(artifact_id)
    if not art:
        from app.services.artifacts.universal_engine_v2 import (
            ArtifactStorageAndVersionManager,
            UniversalArtifactEngineV2,
        )
        v2_rec = ArtifactStorageAndVersionManager.get_artifact(str(user.id), artifact_id)
        if v2_rec:
            return UniversalArtifactEngineV2.format_delivery_card(v2_rec)
    if not art or (art.user_id and art.user_id != user.id):
        raise HTTPException(status_code=404, detail="Artifact preview unavailable")

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
    from app.services.artifacts.registry import artifact_registry
    art = artifact_registry.get(artifact_id)
    if not art:
        from app.services.artifacts.universal_engine_v2 import ArtifactStorageAndVersionManager
        v2_res = ArtifactStorageAndVersionManager.get_artifact_bytes(str(user.id), artifact_id)
        if v2_res:
            rec, raw_bytes = v2_res
            ext = rec.get("extension", "")
            if ext in ("pdf", "docx", "doc", "xlsx", "xls", "pptx", "ppt", "odt", "ods", "odp", "zip", "png", "jpg", "jpeg", "webp"):
                content_str = json.dumps(rec.get("spec") or rec.get("preview") or {}, indent=2, ensure_ascii=False)
            else:
                content_str = raw_bytes.decode("utf-8", errors="replace")
            return {"artifact_id": artifact_id, "filename": rec["filename"], "content": content_str}
    if not art or (art.user_id and art.user_id != user.id):
        raise HTTPException(status_code=404, detail="Artifact content unavailable")

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
        from app.services.artifacts.universal_engine_v2 import ArtifactStorageAndVersionManager
        v2_rec = ArtifactStorageAndVersionManager.get_artifact(str(user.id), artifact_id)
        if v2_rec:
            return {
                "artifact_id": v2_rec["artifactId"],
                "current_version": v2_rec.get("version", 1),
                "versions": [
                    {
                        "version": v.get("version", 1),
                        "timestamp": v.get("createdAt", ""),
                        "summary": v.get("prompt", "Updated artifact"),
                        "size": v.get("size", 0),
                        "artifact_id": v.get("artifactId", artifact_id),
                    }
                    for v in v2_rec.get("versionHistory", [])
                ],
            }
    if not art or (art.user_id and art.user_id != user.id):
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
    from app.services.artifacts.registry import artifact_registry
    art = artifact_registry.get(artifact_id)
    if not art:
        import uuid
        from app.services.artifacts.universal_engine_v2 import (
            ArtifactStorageAndVersionManager,
            UniversalArtifactEngineV2,
        )
        from app.services.artifacts.output_intent_engine import OutputIntentResult, OutputMode
        v2_rec = ArtifactStorageAndVersionManager.get_artifact(str(user.id), artifact_id)
        if v2_rec:
            ext = v2_rec["extension"]
            edit_intent = OutputIntentResult(
                mode=OutputMode.FILE,
                primary_format=ext,
                formats=[ext],
                filename=v2_rec["filename"],
                topic=(v2_rec.get("spec") or {}).get("title") or v2_rec["filename"],
                is_followup_edit=True,
                edit_instructions=req.instruction,
            )
            res = UniversalArtifactEngineV2.execute(
                user_id=str(user.id),
                conversation_id=v2_rec.get("conversationId") or "general",
                message_id=str(uuid.uuid4()),
                user_message=req.instruction,
                intent=edit_intent,
                parent_artifact_id=artifact_id,
            )
            if res.get("status") == "completed" and res.get("artifacts"):
                return {"success": True, "artifact": res["artifacts"][0], "message": res.get("summary_message", "Updated")}
            raise HTTPException(status_code=400, detail=res.get("message", "Edit failed"))
    if not art or (art.user_id and art.user_id != user.id):
        raise HTTPException(status_code=404, detail="Artifact not found")

    from app.services.artifacts.editor import artifact_editor
    success, updated_art, msg = await artifact_editor.edit_artifact(artifact_id, req.instruction, req.target)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "artifact": updated_art.to_dict(), "message": msg}

@router.post("/artifacts/{artifact_id}/restore/{version}")
async def restore_artifact_version_route(
    artifact_id: str,
    version: int,
    user: User = Depends(get_current_user)
):
    from app.services.artifacts.registry import artifact_registry
    existing_art = artifact_registry.get(artifact_id)
    if not existing_art or (existing_art.user_id and existing_art.user_id != user.id):
        raise HTTPException(status_code=404, detail="Artifact not found")

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
    from app.services.artifacts.registry import artifact_registry
    existing_art = artifact_registry.get(artifact_id)
    if not existing_art:
        import uuid
        from app.services.artifacts.universal_engine_v2 import (
            ArtifactStorageAndVersionManager,
            UniversalArtifactEngineV2,
        )
        from app.services.artifacts.output_intent_engine import OutputIntentResult, OutputMode, sanitize_filename
        v2_rec = ArtifactStorageAndVersionManager.get_artifact(str(user.id), artifact_id)
        if v2_rec:
            target_fmt = req.target_format.lower().lstrip(".")
            stem = os.path.splitext(v2_rec["filename"])[0]
            new_fname = sanitize_filename(f"{stem}.{target_fmt}", default_stem=stem, ext=target_fmt)
            conv_intent = OutputIntentResult(
                mode=OutputMode.FILE,
                primary_format=target_fmt,
                formats=[target_fmt],
                filename=new_fname,
                topic=(v2_rec.get("spec") or {}).get("title") or stem,
                is_conversion=True,
                source_format=v2_rec["extension"],
            )
            res = UniversalArtifactEngineV2.execute(
                user_id=str(user.id),
                conversation_id=v2_rec.get("conversationId") or "general",
                message_id=str(uuid.uuid4()),
                user_message=f"Convert {v2_rec['filename']} to {target_fmt.upper()}",
                intent=conv_intent,
                parent_artifact_id=artifact_id,
            )
            if res.get("status") == "completed" and res.get("artifacts"):
                return {"success": True, "artifact": res["artifacts"][0], "message": res.get("summary_message", "Converted")}
            raise HTTPException(status_code=400, detail=res.get("message", "Conversion failed"))
    if not existing_art or (existing_art.user_id and existing_art.user_id != user.id):
        raise HTTPException(status_code=404, detail="Artifact not found")

    from app.services.artifacts.editor import artifact_editor
    success, art, msg = await artifact_editor.convert_artifact(artifact_id, req.target_format)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "artifact": art.to_dict(), "message": msg}

