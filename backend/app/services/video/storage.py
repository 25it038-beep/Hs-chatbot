"""Tenant-isolated video storage manager with path traversal protection."""

import os
import json
import uuid
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
from app.config import settings


class VideoStorageManager:
    """Manages storage of generated videos and reference media with strict per-user isolation."""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = os.path.abspath(base_dir or settings.upload_dir)

    def _get_user_video_dir(self, user_id: str) -> str:
        safe_user_id = str(user_id or "default_user").replace("..", "").replace("/", "").replace("\\", "")
        path = os.path.join(self.base_dir, "users", safe_user_id, "videos")
        os.makedirs(path, exist_ok=True)
        return path

    def _get_user_ref_dir(self, user_id: str) -> str:
        safe_user_id = str(user_id or "default_user").replace("..", "").replace("/", "").replace("\\", "")
        path = os.path.join(self.base_dir, "users", safe_user_id, "references")
        os.makedirs(path, exist_ok=True)
        return path

    def _validate_path_safety(self, file_path: str) -> bool:
        resolved = Path(file_path).resolve()
        base_resolved = Path(self.base_dir).resolve()
        try:
            resolved.relative_to(base_resolved)
            return True
        except ValueError:
            return False

    def save_video(self, user_id: str, job_id: str, video_bytes: bytes, metadata: Dict[str, Any]) -> Tuple[str, str]:
        """
        Saves video binary and JSON metadata under user's directory.
        Returns: (absolute_file_path, relative_download_url)
        """
        user_dir = self._get_user_video_dir(user_id)
        video_filename = f"{job_id}.mp4"
        meta_filename = f"{job_id}.json"

        file_path = os.path.join(user_dir, video_filename)
        meta_path = os.path.join(user_dir, meta_filename)

        if not self._validate_path_safety(file_path):
            raise PermissionError("Path traversal violation prevented")

        with open(file_path, "wb") as f:
            f.write(video_bytes)

        metadata["file_path"] = file_path
        metadata["file_size"] = len(video_bytes)
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        return file_path, f"/api/video/{job_id}/stream"

    def get_video_path(self, user_id: str, job_id: str) -> Optional[str]:
        user_dir = self._get_user_video_dir(user_id)
        safe_job_id = str(job_id).replace("..", "").replace("/", "").replace("\\", "")
        file_path = os.path.join(user_dir, f"{safe_job_id}.mp4")

        if not self._validate_path_safety(file_path):
            return None

        if os.path.exists(file_path):
            return file_path
        return None

    def get_video_metadata(self, user_id: str, job_id: str) -> Optional[Dict[str, Any]]:
        user_dir = self._get_user_video_dir(user_id)
        safe_job_id = str(job_id).replace("..", "").replace("/", "").replace("\\", "")
        meta_path = os.path.join(user_dir, f"{safe_job_id}.json")

        if not self._validate_path_safety(meta_path) or not os.path.exists(meta_path):
            return None

        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def delete_video(self, user_id: str, job_id: str) -> bool:
        user_dir = self._get_user_video_dir(user_id)
        safe_job_id = str(job_id).replace("..", "").replace("/", "").replace("\\", "")
        file_path = os.path.join(user_dir, f"{safe_job_id}.mp4")
        meta_path = os.path.join(user_dir, f"{safe_job_id}.json")

        deleted = False
        if self._validate_path_safety(file_path) and os.path.exists(file_path):
            try:
                os.remove(file_path)
                deleted = True
            except OSError:
                pass

        if self._validate_path_safety(meta_path) and os.path.exists(meta_path):
            try:
                os.remove(meta_path)
            except OSError:
                pass

        return deleted

    def save_reference_image(self, user_id: str, image_bytes: bytes, original_filename: str) -> Tuple[str, str]:
        """Saves reference image for image-to-video workflow. Returns (ref_id, absolute_path)."""
        ref_id = f"ref_{uuid.uuid4().hex[:12]}"
        ext = os.path.splitext(original_filename)[1].lower() or ".jpg"
        if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
            ext = ".png"

        user_ref_dir = self._get_user_ref_dir(user_id)
        file_path = os.path.join(user_ref_dir, f"{ref_id}{ext}")

        if not self._validate_path_safety(file_path):
            raise PermissionError("Path traversal violation prevented")

        with open(file_path, "wb") as f:
            f.write(image_bytes)

        return ref_id, file_path

    def get_reference_image_path(self, user_id: str, ref_id: str) -> Optional[str]:
        user_ref_dir = self._get_user_ref_dir(user_id)
        safe_ref_id = str(ref_id).replace("..", "").replace("/", "").replace("\\", "")

        for ext in [".jpg", ".jpeg", ".png", ".webp"]:
            candidate = os.path.join(user_ref_dir, f"{safe_ref_id}{ext}")
            if self._validate_path_safety(candidate) and os.path.exists(candidate):
                return candidate
        return None


video_storage = VideoStorageManager()
