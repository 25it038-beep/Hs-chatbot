import os
import json
import time
import shutil
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

from app.services.artifacts.models import ArtifactMetadata, ArtifactVersionRecord, ArtifactCategory

logger = logging.getLogger("hsbot.artifacts.registry")

class PersistentArtifactRegistry:
    def __init__(self, storage_dir: Optional[str] = None):
        self.storage_dir = Path(storage_dir or "./data/artifacts")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.registry_file = self.storage_dir / "registry.json"
        self._artifacts: Dict[str, ArtifactMetadata] = {}
        self._load()

    def _load(self):
        if self.registry_file.exists():
            try:
                data = json.loads(self.registry_file.read_text(encoding="utf-8"))
                for art_id, item in data.items():
                    versions = [
                        ArtifactVersionRecord(
                            version=v["version"],
                            created_at=v["created_at"],
                            storage_path=v["storage_path"],
                            file_size=v["file_size"],
                            change_description=v.get("change_description", ""),
                            checksum=v.get("checksum"),
                            verification_status=v.get("verification_status", "verified")
                        )
                        for v in item.get("versions", [])
                    ]
                    meta = ArtifactMetadata(
                        artifact_id=item["artifact_id"],
                        name=item["name"],
                        filename=item["filename"],
                        extension=item["extension"],
                        mime_type=item["mime_type"],
                        artifact_type=item["artifact_type"],
                        category=ArtifactCategory(item.get("category", "other")),
                        storage_path=item["storage_path"],
                        size=item["size"],
                        created_at=item["created_at"],
                        updated_at=item["updated_at"],
                        version=item.get("version", 1),
                        parent_version=item.get("parent_version"),
                        source_task_id=item.get("source_task_id"),
                        source_message_id=item.get("source_message_id"),
                        chat_id=item.get("chat_id"),
                        user_id=item.get("user_id"),
                        generation_method=item.get("generation_method", "adapter"),
                        validation_status=item.get("validation_status", "passed"),
                        visual_validation_status=item.get("visual_validation_status", "passed"),
                        security_status=item.get("security_status", "passed"),
                        delivery_status=item.get("delivery_status", "ready"),
                        preview_data=item.get("preview_data"),
                        content_summary=item.get("content_summary"),
                        versions=versions
                    )
                    self._artifacts[art_id] = meta
            except Exception as e:
                logger.error("Failed to load artifact registry from disk: %s", e)

    def _save(self):
        try:
            data = {art_id: art.to_dict() for art_id, art in self._artifacts.items()}
            self.registry_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error("Failed to persist artifact registry to disk: %s", e)

    def register_artifact(self, meta: ArtifactMetadata) -> ArtifactMetadata:
        # Snapshot initial version if empty
        if not meta.versions:
            meta.versions.append(
                ArtifactVersionRecord(
                    version=meta.version,
                    created_at=meta.created_at,
                    storage_path=meta.storage_path,
                    file_size=meta.size,
                    change_description="Initial generation",
                    verification_status=meta.validation_status
                )
            )
        self._artifacts[meta.artifact_id] = meta
        self._save()
        return meta

    def get(self, artifact_id: str) -> Optional[ArtifactMetadata]:
        return self._artifacts.get(artifact_id)

    def list_artifacts(
        self,
        category: Optional[ArtifactCategory] = None,
        chat_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[ArtifactMetadata]:
        results = list(self._artifacts.values())
        if category:
            results = [a for a in results if a.category == category]
        if chat_id:
            results = [a for a in results if a.chat_id == chat_id]
        if user_id:
            results = [a for a in results if a.user_id == user_id]
        results.sort(key=lambda x: x.updated_at, reverse=True)
        return results

    def search(self, query: str) -> List[ArtifactMetadata]:
        """Artifact Memory search (Section 24)."""
        q = query.lower().strip()
        matches = []
        for art in self._artifacts.values():
            if (
                q in art.name.lower()
                or q in art.filename.lower()
                or q in art.extension.lower()
                or (art.content_summary and q in art.content_summary.lower())
            ):
                matches.append(art)
        return matches

    def create_new_version(
        self,
        artifact_id: str,
        new_file_path: Path,
        change_description: str,
        preview_data: Optional[Dict[str, Any]] = None
    ) -> Optional[ArtifactMetadata]:
        art = self.get(artifact_id)
        if not art:
            return None

        # Archive current or copy to versioned location
        next_ver = art.version + 1
        ver_dir = self.storage_dir / "versions" / art.artifact_id
        ver_dir.mkdir(parents=True, exist_ok=True)
        versioned_storage = ver_dir / f"v{next_ver}_{art.filename}"

        shutil.copy2(new_file_path, versioned_storage)

        ver_record = ArtifactVersionRecord(
            version=next_ver,
            created_at=time.time(),
            storage_path=str(versioned_storage),
            file_size=versioned_storage.stat().st_size,
            change_description=change_description,
            verification_status="verified"
        )

        art.parent_version = art.version
        art.version = next_ver
        art.storage_path = str(versioned_storage)
        art.size = versioned_storage.stat().st_size
        art.updated_at = time.time()
        art.versions.append(ver_record)
        if preview_data:
            art.preview_data = preview_data

        self._save()
        return art

    def restore_version(self, artifact_id: str, target_version: int) -> Optional[ArtifactMetadata]:
        art = self.get(artifact_id)
        if not art:
            return None
        target_rec = next((v for v in art.versions if v.version == target_version), None)
        if not target_rec or not Path(target_rec.storage_path).exists():
            return None

        # Create a new version restoring the older content
        return self.create_new_version(
            artifact_id=artifact_id,
            new_file_path=Path(target_rec.storage_path),
            change_description=f"Restored from version v{target_version}"
        )

artifact_registry = PersistentArtifactRegistry()
