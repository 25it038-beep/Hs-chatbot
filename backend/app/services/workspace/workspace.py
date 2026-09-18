import os
import re
import difflib
import time
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
from app.config import settings

class WorkspaceSecurityError(Exception):
    pass

class WorkspaceManager:
    """
    Secure Workspace Abstraction.
    Provides sandboxed file operations with path traversal prevention,
    atomic edits, unified diff generation, and structured audit events.
    """
    def __init__(self, workspace_id: str = "default", base_dir: Optional[str] = None):
        self.workspace_id = workspace_id
        if base_dir:
            self.root = Path(base_dir).resolve()
        else:
            default_root = Path(settings.upload_dir) / "workspaces" / workspace_id
            self.root = default_root.resolve()
        
        self.root.mkdir(parents=True, exist_ok=True)
        self.audit_log: List[Dict[str, Any]] = []

    def _resolve_safe_path(self, relative_path: str) -> Path:
        """Ensure path is within the workspace root and normalize it."""
        clean = relative_path.strip().lstrip("/\\")
        # Prevent obvious directory traversal sequences
        if ".." in clean.split("/") or ".." in clean.split("\\"):
            raise WorkspaceSecurityError(f"Access denied: Directory traversal detected in '{relative_path}'")

        target = (self.root / clean).resolve()
        try:
            target.relative_to(self.root)
        except ValueError:
            raise WorkspaceSecurityError(f"Access denied: Path '{relative_path}' points outside workspace root")

        return target

    def _log_audit(self, tool: str, path: str, args: Dict[str, Any], status: str, duration_ms: float, result_summary: str):
        # Sanitize sensitive arguments
        sanitized_args = {}
        for k, v in args.items():
            if any(s in k.lower() for s in ["key", "secret", "password", "token"]):
                sanitized_args[k] = "***REDACTED***"
            elif isinstance(v, str) and len(v) > 200:
                sanitized_args[k] = v[:200] + "... [truncated]"
            else:
                sanitized_args[k] = v

        entry = {
            "timestamp": time.time(),
            "time_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "tool": tool,
            "path": path,
            "args": sanitized_args,
            "status": status,
            "duration_ms": round(duration_ms, 2),
            "summary": result_summary
        }
        self.audit_log.append(entry)
        if len(self.audit_log) > 500:
            self.audit_log = self.audit_log[-500:]

    def read_file(self, relative_path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> Dict[str, Any]:
        t0 = time.time()
        try:
            target = self._resolve_safe_path(relative_path)
            if not target.exists() or not target.is_file():
                raise FileNotFoundError(f"File not found: {relative_path}")

            content = target.read_text(encoding="utf-8", errors="replace")
            lines = content.splitlines(keepends=True)
            total_lines = len(lines)

            if start_line is not None or end_line is not None:
                s = max(1, start_line or 1) - 1
                e = min(total_lines, end_line or total_lines)
                sliced_content = "".join(lines[s:e])
            else:
                sliced_content = content

            res = {
                "success": True,
                "path": relative_path,
                "total_lines": total_lines,
                "content": sliced_content,
                "size_bytes": target.stat().st_size
            }
            self._log_audit("read_file", relative_path, {"start_line": start_line, "end_line": end_line}, "success", (time.time() - t0)*1000, f"Read {total_lines} lines")
            return res
        except Exception as e:
            self._log_audit("read_file", relative_path, {"start_line": start_line, "end_line": end_line}, "failed", (time.time() - t0)*1000, str(e))
            return {"success": False, "error": str(e), "path": relative_path}

    def write_file(self, relative_path: str, content: str) -> Dict[str, Any]:
        t0 = time.time()
        try:
            target = self._resolve_safe_path(relative_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            existed = target.exists()
            target.write_text(content, encoding="utf-8")
            res = {
                "success": True,
                "path": relative_path,
                "created": not existed,
                "size_bytes": len(content.encode("utf-8"))
            }
            self._log_audit("write_file", relative_path, {"size": len(content)}, "success", (time.time() - t0)*1000, "Created" if not existed else "Overwritten")
            return res
        except Exception as e:
            self._log_audit("write_file", relative_path, {}, "failed", (time.time() - t0)*1000, str(e))
            return {"success": False, "error": str(e), "path": relative_path}

    def create_file(self, relative_path: str, content: str = "") -> Dict[str, Any]:
        t0 = time.time()
        try:
            target = self._resolve_safe_path(relative_path)
            if target.exists():
                return {"success": False, "error": f"File already exists: {relative_path}", "path": relative_path}
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            res = {"success": True, "path": relative_path, "size_bytes": len(content.encode("utf-8"))}
            self._log_audit("create_file", relative_path, {"size": len(content)}, "success", (time.time() - t0)*1000, "Created new file")
            return res
        except Exception as e:
            self._log_audit("create_file", relative_path, {}, "failed", (time.time() - t0)*1000, str(e))
            return {"success": False, "error": str(e), "path": relative_path}

    def edit_file(self, relative_path: str, target_content: str, replacement_content: str) -> Dict[str, Any]:
        """Precise surgical text replacement with unified diff recording."""
        t0 = time.time()
        try:
            target = self._resolve_safe_path(relative_path)
            if not target.exists() or not target.is_file():
                return {"success": False, "error": f"File does not exist: {relative_path}", "path": relative_path}

            old_text = target.read_text(encoding="utf-8", errors="replace")
            if target_content not in old_text:
                return {"success": False, "error": "Target content not found in file", "path": relative_path}

            count = old_text.count(target_content)
            if count > 1:
                return {"success": False, "error": f"Target content appears {count} times, must be unique", "path": relative_path}

            new_text = old_text.replace(target_content, replacement_content, 1)
            target.write_text(new_text, encoding="utf-8")

            # Generate unified diff
            diff = "".join(difflib.unified_diff(
                old_text.splitlines(keepends=True),
                new_text.splitlines(keepends=True),
                fromfile=f"a/{relative_path}",
                tofile=f"b/{relative_path}"
            ))

            res = {
                "success": True,
                "path": relative_path,
                "diff": diff,
                "size_bytes": len(new_text.encode("utf-8"))
            }
            self._log_audit("edit_file", relative_path, {"diff_length": len(diff)}, "success", (time.time() - t0)*1000, "Edited with diff")
            return res
        except Exception as e:
            self._log_audit("edit_file", relative_path, {}, "failed", (time.time() - t0)*1000, str(e))
            return {"success": False, "error": str(e), "path": relative_path}

    def delete_file(self, relative_path: str) -> Dict[str, Any]:
        t0 = time.time()
        try:
            target = self._resolve_safe_path(relative_path)
            if not target.exists():
                return {"success": False, "error": f"Target does not exist: {relative_path}"}

            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()

            res = {"success": True, "path": relative_path}
            self._log_audit("delete_file", relative_path, {}, "success", (time.time() - t0)*1000, "Deleted")
            return res
        except Exception as e:
            self._log_audit("delete_file", relative_path, {}, "failed", (time.time() - t0)*1000, str(e))
            return {"success": False, "error": str(e), "path": relative_path}

    def list_directory(self, relative_path: str = "", recursive: bool = False, max_depth: int = 3) -> Dict[str, Any]:
        t0 = time.time()
        try:
            target = self._resolve_safe_path(relative_path)
            if not target.exists() or not target.is_dir():
                return {"success": False, "error": f"Directory not found: {relative_path}"}

            entries = []
            if recursive:
                for root, dirs, files in os.walk(target):
                    rel_root = Path(root).relative_to(self.root)
                    depth = len(rel_root.parts)
                    if depth > max_depth:
                        continue
                    for d in sorted(dirs):
                        if not d.startswith("."):
                            entries.append({"name": d, "type": "directory", "path": str((rel_root / d).as_posix())})
                    for f in sorted(files):
                        if not f.startswith("."):
                            p = rel_root / f
                            entries.append({"name": f, "type": "file", "path": str(p.as_posix()), "size": (Path(root)/f).stat().st_size})
            else:
                for item in sorted(target.iterdir()):
                    if item.name.startswith("."):
                        continue
                    rel = item.relative_to(self.root).as_posix()
                    entries.append({
                        "name": item.name,
                        "type": "directory" if item.is_dir() else "file",
                        "path": rel,
                        "size": item.stat().st_size if item.is_file() else 0
                    })

            res = {"success": True, "path": relative_path, "entries": entries, "count": len(entries)}
            self._log_audit("list_directory", relative_path, {"recursive": recursive}, "success", (time.time() - t0)*1000, f"{len(entries)} items")
            return res
        except Exception as e:
            self._log_audit("list_directory", relative_path, {}, "failed", (time.time() - t0)*1000, str(e))
            return {"success": False, "error": str(e)}

    def search_code(self, query: str, relative_path: str = "", case_sensitive: bool = False) -> Dict[str, Any]:
        t0 = time.time()
        try:
            target = self._resolve_safe_path(relative_path)
            matches = []
            flags = 0 if case_sensitive else re.IGNORECASE
            pattern = re.compile(re.escape(query), flags)

            search_root = target if target.is_dir() else target.parent
            for root, _, files in os.walk(search_root):
                if any(ignored in root for ignored in ["node_modules", ".git", "__pycache__", "dist", ".next"]):
                    continue
                for fname in files:
                    fpath = Path(root) / fname
                    # Skip non-text files or huge binaries
                    if fpath.suffix.lower() in [".png", ".jpg", ".jpeg", ".ico", ".pdf", ".zip", ".exe", ".bin"]:
                        continue
                    try:
                        if fpath.stat().st_size > 1_000_000:
                            continue
                        content = fpath.read_text(encoding="utf-8", errors="ignore")
                        for idx, line in enumerate(content.splitlines(), start=1):
                            if pattern.search(line):
                                rel = fpath.relative_to(self.root).as_posix()
                                matches.append({
                                    "file": rel,
                                    "line_number": idx,
                                    "line": line.strip()[:160]
                                })
                                if len(matches) >= 100:
                                    break
                    except Exception:
                        continue
                if len(matches) >= 100:
                    break

            res = {"success": True, "query": query, "matches": matches, "count": len(matches)}
            self._log_audit("search_code", query, {}, "success", (time.time() - t0)*1000, f"{len(matches)} matches")
            return res
        except Exception as e:
            self._log_audit("search_code", query, {}, "failed", (time.time() - t0)*1000, str(e))
            return {"success": False, "error": str(e)}

    def get_project_structure(self, max_depth: int = 4) -> Dict[str, Any]:
        """Returns structured file tree for IDE navigation."""
        def build_node(path: Path, current_depth: int):
            rel = path.relative_to(self.root).as_posix()
            if path.is_file():
                return {
                    "name": path.name,
                    "path": rel if rel != "." else path.name,
                    "type": "file",
                    "size": path.stat().st_size
                }
            
            children = []
            if current_depth < max_depth:
                try:
                    for item in sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name.lower())):
                        if item.name.startswith(".") or item.name in ["node_modules", "__pycache__", "dist", ".next"]:
                            continue
                        children.append(build_node(item, current_depth + 1))
                except PermissionError:
                    pass

            return {
                "name": path.name if path != self.root else "workspace",
                "path": rel if rel != "." else "",
                "type": "directory",
                "children": children
            }

        tree = build_node(self.root, 0)
        return {"success": True, "workspace_id": self.workspace_id, "root_path": str(self.root), "tree": tree}

# Global or multi-tenant registry for workspaces
_workspaces: Dict[str, WorkspaceManager] = {}

def get_workspace(workspace_id: str = "default", base_dir: Optional[str] = None) -> WorkspaceManager:
    key = f"{workspace_id}:{base_dir or ''}"
    if key not in _workspaces:
        _workspaces[key] = WorkspaceManager(workspace_id, base_dir)
    return _workspaces[key]
