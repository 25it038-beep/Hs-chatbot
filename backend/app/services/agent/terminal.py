import asyncio
import os
import re
import shlex
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

# Regex patterns for detecting and redacting secrets
SECRET_PATTERNS = [
    re.compile(r"nvapi-[A-Za-z0-9_\-]{20,}", re.IGNORECASE),
    re.compile(r"sk-[A-Za-z0-9_\-]{20,}", re.IGNORECASE),
    re.compile(r"ghp_[A-Za-z0-9]{30,}", re.IGNORECASE),
    re.compile(r"eyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}", re.IGNORECASE),
    re.compile(r"(password|secret|token|api_key)[\s:=]+['\"]?([A-Za-z0-9_\-\.]{8,})['\"]?", re.IGNORECASE),
]

ALLOWED_COMMAND_ROOTS = {
    "python", "python3", "pip", "pip3", "pytest", "uvicorn", "flake8", "mypy", "black", "isort",
    "node", "npm", "npx", "pnpm", "yarn", "tsc", "vite", "eslint", "bun",
    "git", "echo", "cat", "ls", "dir", "mkdir", "find", "tree", "wc", "head", "tail", "grep"
}

FORBIDDEN_PATTERNS = [
    re.compile(r"\brm\s+(-[rfRF]+\s+)?/"),
    re.compile(r"\b(format|mkfs|dd|chmod\s+777|chown)\b"),
    re.compile(r"\b(curl|wget)\b.*\|\s*(bash|sh)"),
    re.compile(r"\bsudo\b"),
    re.compile(r"\bshutdown\b"),
    re.compile(r"\breboot\b"),
]

def redact_secrets(text: str) -> str:
    """Replaces sensitive tokens and keys with redacted placeholders."""
    if not text:
        return ""
    sanitized = text
    for pattern in SECRET_PATTERNS:
        sanitized = pattern.sub("[REDACTED_SECRET]", sanitized)
    return sanitized

class TerminalExecutionError(Exception):
    pass

class TerminalAgent:
    """
    Secure Terminal Execution Layer.
    Executes allowed development commands inside sandboxed workspace directories.
    """
    def __init__(self, workspace_path: Path, max_output_chars: int = 50_000):
        self.workspace_path = workspace_path.resolve()
        self.max_output_chars = max_output_chars

    def is_command_allowed(self, command_str: str) -> tuple[bool, str]:
        cmd_clean = command_str.strip()
        if not cmd_clean:
            return False, "Command string is empty"

        # Check for explicitly forbidden shell constructs
        for pat in FORBIDDEN_PATTERNS:
            if pat.search(cmd_clean):
                return False, f"Dangerous command pattern detected: {pat.pattern}"

        # Parse command binary
        parts = shlex.split(cmd_clean, posix=os.name != "nt")
        if not parts:
            return False, "Unable to parse command arguments"

        binary = Path(parts[0]).name.lower()
        # Remove .exe on windows
        if binary.endswith(".exe"):
            binary = binary[:-4]

        if binary not in ALLOWED_COMMAND_ROOTS:
            return False, f"Command '{binary}' is not permitted by workspace security policy"

        # Check git commands for remote push confirmation
        if binary == "git" and len(parts) > 1 and parts[1] == "push":
            return False, "git push is sensitive and requires explicit user confirmation"

        return True, "Allowed"

    async def execute(self, command_str: str, timeout_seconds: int = 60, sub_dir: str = "") -> Dict[str, Any]:
        t0 = time.time()
        allowed, reason = self.is_command_allowed(command_str)
        if not allowed:
            return {
                "success": False,
                "tool": "terminal",
                "command": command_str,
                "stdout": "",
                "stderr": reason,
                "exit_code": -1,
                "duration_ms": 0.0,
                "blocked": True
            }

        cwd = self.workspace_path
        if sub_dir:
            cand = (self.workspace_path / sub_dir.strip().lstrip("/\\")).resolve()
            if cand.exists() and cand.is_dir() and str(cand).startswith(str(self.workspace_path)):
                cwd = cand

        try:
            process = await asyncio.create_subprocess_shell(
                command_str,
                cwd=str(cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                # Pass clean environment without leaking internal backend tokens
                env={k: v for k, v in os.environ.items() if not k.startswith("SECRET_") and "TOKEN" not in k and "NVIDIA_API_KEY" not in k}
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                try:
                    process.kill()
                    await process.wait()
                except Exception:
                    pass
                duration_ms = (time.time() - t0) * 1000
                return {
                    "success": False,
                    "tool": "terminal",
                    "command": command_str,
                    "stdout": "",
                    "stderr": f"Command timed out after {timeout_seconds} seconds",
                    "exit_code": -1,
                    "duration_ms": round(duration_ms, 2)
                }

            stdout_text = redact_secrets(stdout_bytes.decode("utf-8", errors="replace"))
            stderr_text = redact_secrets(stderr_bytes.decode("utf-8", errors="replace"))

            if len(stdout_text) > self.max_output_chars:
                stdout_text = stdout_text[:self.max_output_chars] + f"\n... [Output truncated at {self.max_output_chars} chars]"
            if len(stderr_text) > self.max_output_chars:
                stderr_text = stderr_text[:self.max_output_chars] + f"\n... [Stderr truncated at {self.max_output_chars} chars]"

            duration_ms = (time.time() - t0) * 1000
            exit_code = process.returncode if process.returncode is not None else 0

            return {
                "success": exit_code == 0,
                "tool": "terminal",
                "command": command_str,
                "stdout": stdout_text,
                "stderr": stderr_text,
                "exit_code": exit_code,
                "duration_ms": round(duration_ms, 2)
            }
        except Exception as e:
            duration_ms = (time.time() - t0) * 1000
            return {
                "success": False,
                "tool": "terminal",
                "command": command_str,
                "stdout": "",
                "stderr": redact_secrets(str(e)),
                "exit_code": -1,
                "duration_ms": round(duration_ms, 2)
            }
