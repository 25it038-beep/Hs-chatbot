import ast
import os
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

class RepositoryIndex:
    """
    Lightweight Repository Intelligence & Symbol Index.
    Extracts symbols (functions, classes, endpoints, components, imports)
    to enable precise retrieval without dumping the whole codebase to the model.
    """
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir.resolve()
        self.files: List[str] = []
        self.symbols: Dict[str, List[Dict[str, Any]]] = {} # symbol_name -> occurrences
        self.routes: List[Dict[str, Any]] = []
        self.imports: Dict[str, List[str]] = {} # file -> list of imports
        self.last_indexed = 0.0

    def index_workspace(self, force: bool = False):
        if not force and (time.time() - self.last_indexed < 30.0):
            return  # Cache index for 30s

        self.files.clear()
        self.symbols.clear()
        self.routes.clear()
        self.imports.clear()

        for root, dirs, filenames in os.walk(self.root_dir):
            dirs[:] = [d for d in dirs if d not in ["node_modules", ".git", "__pycache__", "dist", ".next", ".cache"]]
            rel_root = Path(root).relative_to(self.root_dir)

            for fname in filenames:
                fpath = Path(root) / fname
                rel_path = (rel_root / fname).as_posix()
                self.files.append(rel_path)

                ext = fpath.suffix.lower()
                if ext == ".py":
                    self._index_python_file(fpath, rel_path)
                elif ext in [".ts", ".tsx", ".js", ".jsx"]:
                    self._index_js_file(fpath, rel_path)

        self.last_indexed = time.time()

    def _index_python_file(self, fpath: Path, rel_path: str):
        try:
            content = fpath.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(content, filename=rel_path)

            file_imports = []
            for node in ast.walk(tree):
                # Functions
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Check for FastAPI route decorators
                    is_route = False
                    method = "GET"
                    path = ""
                    for dec in node.decorator_list:
                        dec_str = ast.unparse(dec) if hasattr(ast, "unparse") else ""
                        if any(m in dec_str.lower() for m in [".get(", ".post(", ".put(", ".delete(", ".patch("]):
                            is_route = True
                            m_match = re.search(r"\.(get|post|put|delete|patch)\((['\"][^'\"]+['\"])", dec_str, re.I)
                            if m_match:
                                method = m_match.group(1).upper()
                                path = m_match.group(2).strip("'\"")

                    if is_route:
                        self.routes.append({
                            "method": method,
                            "path": path,
                            "handler": node.name,
                            "file": rel_path,
                            "line": node.lineno
                        })

                    sym = {
                        "name": node.name,
                        "type": "function",
                        "file": rel_path,
                        "line": node.lineno
                    }
                    self.symbols.setdefault(node.name.lower(), []).append(sym)

                # Classes
                elif isinstance(node, ast.ClassDef):
                    sym = {
                        "name": node.name,
                        "type": "class",
                        "file": rel_path,
                        "line": node.lineno
                    }
                    self.symbols.setdefault(node.name.lower(), []).append(sym)

                # Imports
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        file_imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        file_imports.append(node.module)

            self.imports[rel_path] = list(set(file_imports))
        except Exception:
            pass

    def _index_js_file(self, fpath: Path, rel_path: str):
        try:
            content = fpath.read_text(encoding="utf-8", errors="ignore")
            lines = content.splitlines()

            # Regex for JS/TS functions, classes, components
            fn_pat = re.compile(r"(?:export\s+)?(?:async\s+)?function\s+([A-Za-z0-9_]+)")
            const_fn_pat = re.compile(r"(?:export\s+)?const\s+([A-Za-z0-9_]+)\s*=\s*(?:async\s*)?\(")
            class_pat = re.compile(r"(?:export\s+)?class\s+([A-Za-z0-9_]+)")
            import_pat = re.compile(r"import\s+.*?from\s+['\"]([^'\"]+)['\"]")

            file_imports = []
            for idx, line in enumerate(lines, start=1):
                # Check functions
                m_fn = fn_pat.search(line) or const_fn_pat.search(line)
                if m_fn:
                    name = m_fn.group(1)
                    sym_type = "component" if name[0].isupper() else "function"
                    self.symbols.setdefault(name.lower(), []).append({
                        "name": name,
                        "type": sym_type,
                        "file": rel_path,
                        "line": idx
                    })

                # Check classes
                m_cls = class_pat.search(line)
                if m_cls:
                    name = m_cls.group(1)
                    self.symbols.setdefault(name.lower(), []).append({
                        "name": name,
                        "type": "class",
                        "file": rel_path,
                        "line": idx
                    })

                # Check imports
                m_imp = import_pat.search(line)
                if m_imp:
                    file_imports.append(m_imp.group(1))

            self.imports[rel_path] = list(set(file_imports))
        except Exception:
            pass

    def search_symbols(self, query: str) -> List[Dict[str, Any]]:
        self.index_workspace()
        q = query.lower().strip()
        results = []
        for name, occurrences in self.symbols.items():
            if q in name:
                results.extend(occurrences)
        return results[:30]

    def find_routes(self, path_or_method: str = "") -> List[Dict[str, Any]]:
        self.index_workspace()
        q = path_or_method.lower().strip()
        if not q:
            return self.routes
        return [r for r in self.routes if q in r["path"].lower() or q in r["method"].lower()]

    def search_files(self, pattern_str: str) -> List[str]:
        self.index_workspace()
        pat = re.compile(pattern_str, re.IGNORECASE)
        return [f for f in self.files if pat.search(f)]

    def summarize_context(self) -> Dict[str, Any]:
        self.index_workspace()
        return {
            "total_files": len(self.files),
            "total_symbols": sum(len(v) for v in self.symbols.values()),
            "total_routes": len(self.routes),
            "key_files": [f for f in self.files if any(k in f for k in ["main.py", "App.tsx", "package.json", "requirements.txt", "README.md"])][:10]
        }
