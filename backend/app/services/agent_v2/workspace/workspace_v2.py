import os
import shutil
import difflib
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from app.services.agent_v2.core.contracts import CheckpointType

logger = logging.getLogger("hsbot.agent_v2.workspace")

class WorkspaceSecurityError(Exception):
    pass


class AgentWorkspaceV2:
    """
    Real Project Workspace Engine for Agent V2 (§29, §30, §56, §57).
    Tracks real project files, checkpoints, file-safety validations, and atomic diffs.
    """

    def __init__(self, root_dir: Path):
        self.root = root_dir.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.checkpoints_dir = self.root / ".agent_checkpoints"
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)
        self._change_history: List[Dict[str, Any]] = []

    def _resolve_safe_path(self, rel_path: str) -> Path:
        target = (self.root / rel_path).resolve()
        if not str(target).startswith(str(self.root)):
            raise WorkspaceSecurityError(f"Path traversal detected: {rel_path}")
        return target

    def write_file(self, rel_path: str, content: str, task_id: Optional[str] = None, reason: Optional[str] = None) -> Dict[str, Any]:
        target = self._resolve_safe_path(rel_path)
        target.parent.mkdir(parents=True, exist_ok=True)

        old_content = ""
        is_new = not target.exists()
        if not is_new:
            try:
                old_content = target.read_text(encoding="utf-8", errors="replace")
            except Exception:
                old_content = ""

        target.write_text(content, encoding="utf-8")

        diff = ""
        if not is_new and old_content != content:
            diff_lines = difflib.unified_diff(
                old_content.splitlines(keepends=True),
                content.splitlines(keepends=True),
                fromfile=f"a/{rel_path}",
                tofile=f"b/{rel_path}"
            )
            diff = "".join(diff_lines)

        entry = {
            "path": rel_path,
            "task_id": task_id,
            "reason": reason or ("Created" if is_new else "Modified"),
            "size": len(content),
            "is_new": is_new,
            "diff": diff
        }
        self._change_history.append(entry)

        return {
            "success": True,
            "path": rel_path,
            "bytes_written": len(content),
            "is_new": is_new,
            "diff": diff
        }

    def read_file(self, rel_path: str) -> Dict[str, Any]:
        target = self._resolve_safe_path(rel_path)
        if not target.exists():
            return {"success": False, "error": f"File not found: {rel_path}"}
        content = target.read_text(encoding="utf-8", errors="replace")
        return {"success": True, "path": rel_path, "content": content, "size": len(content)}

    def list_files(self) -> List[str]:
        files = []
        for p in self.root.rglob("*"):
            if p.is_file() and not str(p).startswith(str(self.checkpoints_dir)):
                rel = str(p.relative_to(self.root)).replace("\\", "/")
                files.append(rel)
        files.sort()
        return files

    def create_checkpoint(self, checkpoint_name: str, stage: CheckpointType) -> str:
        """Saves a snapshot of workspace files for rollback recovery (§56)."""
        cp_id = f"cp_{int(os.times().elapsed * 100)}_{stage.value.lower()}"
        cp_path = self.checkpoints_dir / cp_id
        cp_path.mkdir(parents=True, exist_ok=True)

        for rel in self.list_files():
            src = self.root / rel
            dst = cp_path / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

        logger.info(f"Created workspace checkpoint '{cp_id}' at stage {stage.value}")
        return cp_id

    def restore_checkpoint(self, cp_id: str) -> bool:
        """Rollback workspace to earlier checkpoint upon regression (§57)."""
        cp_path = self.checkpoints_dir / cp_id
        if not cp_path.exists():
            return False

        for f in self.list_files():
            (self.root / f).unlink(missing_ok=True)

        for p in cp_path.rglob("*"):
            if p.is_file():
                rel = p.relative_to(cp_path)
                dst = self.root / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, dst)

        logger.info(f"Restored workspace to checkpoint '{cp_id}'")
        return True

    def get_change_history(self) -> List[Dict[str, Any]]:
        return list(self._change_history)
