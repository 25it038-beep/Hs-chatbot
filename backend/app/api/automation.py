"""API routes for OS automation engine."""

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.config import settings
from app.middleware.auth import get_current_user
from app.models.user import User
from app.services.automation.engine import automation_engine
from app.utils.security import decode_token

logger = logging.getLogger("hsbot.api.automation")

router = APIRouter(prefix="/api/automation", tags=["automation"])


class CommandRequest(BaseModel):
    command: str
    user_id: Optional[str] = None


class ConfirmRequest(BaseModel):
    action_id: str
    confirmed: bool = True
    choice: Optional[str] = None
    user_id: Optional[str] = None


def _require_local():
    """OS automation only works when the backend runs on the user's machine."""
    if not settings.os_automation_available:
        raise HTTPException(
            status_code=503,
            detail="OS automation runs on your computer. Connect to the local backend (localhost:8000) to use it — the cloud backend cannot touch your PC.",
        )


def _response_dict(response) -> dict:
    return response.to_dict() if hasattr(response, "to_dict") else {
        "success": response.success,
        "action_id": response.action_id,
        "message": response.message,
        "result": response.result,
        "error": response.error,
        "requires_confirmation": response.requires_confirmation,
        "confirmation_prompt": response.confirmation_prompt,
        "execution_time_ms": response.execution_time_ms,
        "spoken": getattr(response, "spoken", None),
        "options": getattr(response, "options", None),
        "step_index": getattr(response, "step_index", 1),
        "total_steps": getattr(response, "total_steps", 1),
    }


@router.post("/command")
async def execute_command(data: CommandRequest, current_user: User = Depends(get_current_user)) -> dict:
    """Execute an automation command (possibly a chain of commands)."""
    _require_local()
    if not data.command or not data.command.strip():
        raise HTTPException(status_code=400, detail="Command is required")
    user_id = data.user_id or current_user.id
    response = await automation_engine.process_command(data.command, user_id)
    return _response_dict(response)


@router.post("/confirm")
async def confirm_action(data: ConfirmRequest, current_user: User = Depends(get_current_user)) -> dict:
    """Confirm or cancel a pending automation action (with optional ambiguity choice)."""
    _require_local()
    user_id = data.user_id or current_user.id
    response = await automation_engine.confirm_action(
        data.action_id, data.confirmed, user_id, choice=data.choice
    )
    return _response_dict(response)


@router.post("/cancel")
async def cancel_active(current_user: User = Depends(get_current_user)) -> dict:
    """Cancel the currently running automation chain."""
    _require_local()
    cancelled = await automation_engine.cancel()
    return {"success": cancelled, "message": "Execution cancelled." if cancelled else "No active execution."}


@router.get("/action/{action_id}")
async def get_action_status(action_id: str, current_user: User = Depends(get_current_user)) -> dict:
    """Get the status of a specific action."""
    _require_local()
    status = automation_engine.get_action_status(action_id)
    if not status:
        raise HTTPException(status_code=404, detail="Action not found")
    return status


@router.get("/status")
async def get_status(current_user: User = Depends(get_current_user)) -> dict:
    """Get engine + executor status (device status for the Automation UI)."""
    from app.services.automation.isolated_executor import get_isolated_executor
    executor = get_isolated_executor()
    return {
        "automation_available": settings.os_automation_available,
        "platform": "windows",
        "engine": {
            "active_processes": executor.get_active_count(),
            "max_workers": executor.max_workers,
            "pending_confirmations": len(automation_engine.pending_confirmations),
        },
        "voice_listener": _voice_status(),
        "examples": [
            "Open Chrome",
            "Open VS Code",
            "Check CPU and RAM usage",
            "Create a folder called Projects",
            "Take a screenshot",
            "Set volume to 60%",
            "Search Google for Python tutorials",
        ],
    }


def _voice_status() -> dict:
    try:
        from app.services.voice.listener import get_voice_listener
        listener = get_voice_listener()
        return {
            "state": listener.get_state(),
            "microphone_enabled": listener.microphone_enabled,
            "continuous_mode": listener.continuous_conversation_enabled,
        }
    except Exception:
        return {"state": "stopped", "microphone_enabled": False, "continuous_mode": False}


@router.get("/log")
async def get_execution_log(limit: int = 50, user_id: Optional[str] = None,
                            current_user: User = Depends(get_current_user)) -> dict:
    """Get recent execution log."""
    _require_local()
    uid = user_id or current_user.id
    log_entries = automation_engine.get_execution_log(limit, uid)
    return {"entries": log_entries, "count": len(log_entries)}


@router.get("/executor/status")
async def get_executor_status(current_user: User = Depends(get_current_user)) -> dict:
    """Get isolated executor status."""
    from app.services.automation.isolated_executor import get_isolated_executor
    executor = get_isolated_executor()
    return {
        "active_processes": executor.get_active_count(),
        "max_workers": executor.max_workers,
        "status": "running",
    }


@router.get("/examples")
async def get_examples() -> dict:
    """Get example automation commands."""
    return {
        "examples": [
            {"command": "Open Chrome", "intent": "open_application"},
            {"command": "Close Discord", "intent": "close_application"},
            {"command": "Create a folder called MyProject", "intent": "create_folder"},
            {"command": "Check CPU usage", "intent": "get_cpu_usage"},
            {"command": "Take a screenshot", "intent": "take_screenshot"},
            {"command": "Open Downloads folder", "intent": "open_folder"},
            {"command": "Set volume to 50%", "intent": "set_volume"},
            {"command": "Lock the screen", "intent": "lock_screen"},
            {"command": "Run npm install", "intent": "run_command"},
            {"command": "Press Ctrl+S", "intent": "key_press"},
        ]
    }


@router.get("/categories")
async def get_categories() -> dict:
    """Get all available automation categories."""
    return {
        "categories": [
            {"name": "Application", "icon": "app", "count": 6},
            {"name": "File", "icon": "file", "count": 8},
            {"name": "Folder", "icon": "folder", "count": 8},
            {"name": "Keyboard", "icon": "keyboard", "count": 2},
            {"name": "Mouse", "icon": "mouse", "count": 5},
            {"name": "Window", "icon": "window", "count": 7},
            {"name": "System", "icon": "settings", "count": 14},
            {"name": "Browser", "icon": "globe", "count": 7},
            {"name": "Process", "icon": "cpu", "count": 5},
            {"name": "Terminal", "icon": "terminal", "count": 2},
        ]
    }


@router.websocket("/ws")
async def automation_ws(websocket: WebSocket, token: str = ""):
    """Realtime automation event stream: step/confirmation/action events + cancel commands.

    Auth mirrors get_current_user: a valid JWT identifies the user; a missing or
    invalid token falls back to the default local user (the WS is local-only).
    """
    if token:
        try:
            payload = decode_token(token)
            if not payload or payload.get("type") != "access":
                # fall back to default user, like the REST endpoints
                pass
        except Exception:
            pass
    if not settings.os_automation_available:
        await websocket.close(code=4403, reason="automation unavailable on cloud")
        return

    await websocket.accept()
    queue = automation_engine.subscribe()
    recv_task = asyncio.ensure_future(_receive_loop(websocket))
    try:
        # Push initial status
        await websocket.send_json({"type": "connected", "status": "ok"})
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=0.5)
                await websocket.send_json(event)
            except asyncio.TimeoutError:
                continue
    except (WebSocketDisconnect, Exception) as e:
        logger.debug(f"Automation WS closed: {e}")
    finally:
        automation_engine.unsubscribe(queue)
        recv_task.cancel()
        try:
            await websocket.close()
        except Exception:
            pass


async def _receive_loop(websocket: WebSocket):
    """Read client messages (cancel etc.) and dispatch."""
    try:
        while True:
            message = await websocket.receive_json()
            if isinstance(message, dict):
                if message.get("type") == "cancel":
                    await automation_engine.cancel()
                elif message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
    except Exception:
        pass
