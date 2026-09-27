import json
import os
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query, Body, Request
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_optional_user
from app.models.user import User
from app.services.agent_v2.orchestrator import AgentOrchestratorV2
from app.services.agent_v2.understanding.sufficiency import RequirementSufficiencyEngine
from app.services.agent_v2.dna.dna_engine import ProductDNAEngine
from app.services.agent_v2.planning.planner import ImplementationPlanner
from app.services.agent_v2.models.role_router import AgentRoleRouter, agent_role_router
from app.services.agent.model_router import agent_model_registry
from app.services.workspace.workspace import get_workspace
from app.services.artifacts.engine import artifact_engine, SecretLeakDetectedError

router = APIRouter(prefix="/api/agent-v2", tags=["Agent V2"])

class UnderstandRequest(BaseModel):
    prompt: str
    workspace_id: Optional[str] = "default"

class PlanRequest(BaseModel):
    prompt: str
    workspace_id: Optional[str] = "default"
    answers: Optional[Dict[str, str]] = None

class RunRequest(BaseModel):
    prompt: str
    workspace_id: Optional[str] = "default"
    chat_id: Optional[str] = None
    autonomy_mode: Optional[str] = "AUTO"
    model: Optional[str] = "codestral"
    answers: Optional[Dict[str, str]] = None
    approved_plan: Optional[Dict[str, Any]] = None

class FileWriteRequest(BaseModel):
    path: str
    content: str
    workspace_id: Optional[str] = "default"

class TerminalRequest(BaseModel):
    command: str
    workspace_id: Optional[str] = "default"
    timeout: Optional[int] = 30

@router.get("/models")
async def get_models(user: Optional[User] = Depends(get_optional_user)):
    """Returns active NVIDIA models configured for Agent V2 with capability and health metrics."""
    return {
        "success": True,
        "models": [p.to_dict() for p in agent_model_registry.list_profiles()],
        "status": agent_model_registry.get_status()
    }

@router.get("/roles")
async def get_roles(user: Optional[User] = Depends(get_optional_user)):
    """Returns complete virtual software company employee hierarchy and assigned NVIDIA models."""
    return {
        "success": True,
        "roles": AgentRoleRouter.get_role_manifest()
    }

@router.post("/understand")
async def understand_prompt(req: UnderstandRequest, user: Optional[User] = Depends(get_optional_user)):
    """Analyzes requirements, classifies them (KNOWN, INFERRED, MISSING, AMBIGUOUS), and checks sufficiency."""
    is_sufficient, classified, question = RequirementSufficiencyEngine.evaluate(req.prompt)
    spec = RequirementSufficiencyEngine.generate_product_specification(req.prompt)
    return {
        "success": True,
        "is_sufficient": is_sufficient,
        "classified_requirements": classified,
        "question": question.to_dict() if question else None,
        "specification": spec.to_dict()
    }

@router.post("/plan")
async def generate_plan(req: PlanRequest, user: Optional[User] = Depends(get_optional_user)):
    """Synthesizes canonical ProductSpecification, ProductDNA, and ImplementationPlan with validation."""
    spec = RequirementSufficiencyEngine.generate_product_specification(req.prompt, req.answers)
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

@router.post("/run")
async def run_agent_v2(req: RunRequest, user: Optional[User] = Depends(get_optional_user)):
    """
    Executes the autonomous AI Product Company engineering loop with real NVIDIA model generation
    and streams lifecycle events as Server-Sent Events (SSE).
    """
    user_id = user.id if user else "session_user"
    orch = AgentOrchestratorV2(workspace_id=req.workspace_id)

    async def event_generator():
        try:
            async for chunk in orch.run_lifecycle(
                user_request=req.prompt,
                chat_id=req.chat_id,
                user_id=user_id,
                answers=req.answers
            ):
                data = json.dumps(chunk)
                yield f"data: {data}\n\n"
        except SecretLeakDetectedError as leak_err:
            err_data = json.dumps({
                "type": "error",
                "message": f"Security policy blocked execution: {leak_err}",
                "blocked": True
            })
            yield f"data: {err_data}\n\n"
        except Exception as e:
            err_data = json.dumps({
                "type": "error",
                "message": str(e),
                "generation_status": "FAILED"
            })
            yield f"data: {err_data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@router.get("/workspace/tree")
async def get_workspace_tree(
    workspace_id: str = Query("default"),
    user: Optional[User] = Depends(get_optional_user)
):
    user_id = user.id if user else None
    ws = get_workspace(workspace_id, user_id=user_id)
    return ws.get_project_structure()

@router.get("/workspace/file")
async def read_workspace_file(
    path: str = Query(...),
    workspace_id: str = Query("default"),
    user: Optional[User] = Depends(get_optional_user)
):
    user_id = user.id if user else None
    ws = get_workspace(workspace_id, user_id=user_id)
    res = ws.read_file(path)
    if not res.get("success"):
        raise HTTPException(status_code=404, detail=res.get("error"))
    return res

@router.post("/workspace/file")
async def write_workspace_file(
    req: FileWriteRequest,
    user: Optional[User] = Depends(get_optional_user)
):
    user_id = user.id if user else None
    ws = get_workspace(req.workspace_id, user_id=user_id)
    res = ws.write_file(req.path, req.content)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res

@router.post("/workspace/terminal")
async def execute_terminal(
    req: TerminalRequest,
    user: Optional[User] = Depends(get_optional_user)
):
    user_id = user.id if user else None
    ws = get_workspace(req.workspace_id, user_id=user_id)
    from app.services.agent.terminal import TerminalAgent
    term = TerminalAgent(ws.root)
    result = await term.run_command(req.command, timeout_seconds=req.timeout)
    return result

@router.get("/artifacts")
async def list_artifacts(
    chat_id: Optional[str] = Query(None),
    workspace_id: str = Query("default"),
    user: Optional[User] = Depends(get_optional_user)
):
    user_id = user.id if user else "session_user"
    arts = artifact_engine.list_artifacts(chat_id=chat_id, user_id=user_id)
    return {"artifacts": arts}
