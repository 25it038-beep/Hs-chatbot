import os
import zipfile
from typing import Dict, Any, List, Tuple


def generate_universal_zip(files_map: Dict[str, str], output_path: str):
    """Creates a real, validated ZIP archive from generated file contents (§12, §13)."""
    with zipfile.ZipFile(output_path, 'w', compression=zipfile.ZIP_DEFLATED) as zipf:
        for rel_path, content in files_map.items():
            clean_rel = rel_path.lstrip("/\\")
            zipf.writestr(clean_rel, content)
