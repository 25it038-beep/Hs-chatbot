import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from app.services.agent_v2.core.contracts import ToolPermissionLevel
from app.services.agent.terminal import TerminalAgent, redact_secrets

logger = logging.getLogger("hsbot.agent_v2.tools")

class ToolPermissionDeniedError(Exception):
    pass


class AgentToolOrchestrator:
    """
    Controlled & observable tool execution engine (§28, §62, §63).
    Classifies commands into permission tiers and redacts sensitive tokens.
    """

    # Disallowed dangerous patterns
    BLOCKED_PATTERNS = [
        "rm -rf /", ":(){ :|:& };:", "dd if=/dev/zero",
        "chmod -r 777 /", "mkfs", "shutdown", "reboot"
    ]

    def __init__(self, terminal: TerminalAgent):
        self.terminal = terminal
        self.audit_log: List[Dict[str, Any]] = []

    def classify_tool_action(self, command: str) -> ToolPermissionLevel:
        cmd_lower = command.strip().lower()
        if any(cmd_lower.startswith(p) for p in ["cat ", "ls ", "dir ", "echo ", "git status", "git log"]):
            return ToolPermissionLevel.READ_ONLY
        elif any(w in cmd_lower for w in ["rm -rf", "delete", "drop database", "format"]):
            return ToolPermissionLevel.DESTRUCTIVE
        elif any(w in cmd_lower for w in ["curl ", "wget ", "ssh ", "sendmail"]):
            return ToolPermissionLevel.EXTERNAL_ACTION
        return ToolPermissionLevel.SAFE_WRITE

    async def execute_command(
        self,
        command: str,
        task_id: Optional[str] = None,
        timeout_seconds: int = 30
    ) -> Dict[str, Any]:
        level = self.classify_tool_action(command)

        if level == ToolPermissionLevel.DESTRUCTIVE or any(p in command for p in self.BLOCKED_PATTERNS):
            logger.warning(f"Blocked destructive command: {command}")
            return {
                "success": False,
                "command": command,
                "blocked": True,
                "error": "Destructive command execution blocked by AgentToolOrchestrator policy."
            }

        res = await self.terminal.execute(command, timeout_seconds=timeout_seconds)

        entry = {
            "task_id": task_id,
            "command": redact_secrets(command),
            "permission_level": level.value,
            "exit_code": res.get("exit_code"),
            "success": res.get("success", False)
        }
        self.audit_log.append(entry)

        return res
