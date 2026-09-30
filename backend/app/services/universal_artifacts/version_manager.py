import re
from typing import Dict, Any, Optional, Tuple
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.file import GeneratedFile


class ArtifactVersionManager:
    """Manages version lineage and conversational file modifications (§19, §20, §56)."""

    @classmethod
    async def get_latest_artifact_for_chat(
        cls,
        conversation_id: str,
        db: AsyncSession,
        fmt: Optional[str] = None
    ) -> Optional[GeneratedFile]:
        stmt = select(GeneratedFile).where(GeneratedFile.conversation_id == str(conversation_id))
        if fmt:
            stmt = stmt.where(GeneratedFile.filename.ilike(f"%.{fmt}"))
        stmt = stmt.order_by(desc(GeneratedFile.created_at))
        result = await db.execute(stmt)
        return result.scalars().first()

    @classmethod
    def compute_next_version(cls, prev_filename: str) -> Tuple[int, str]:
        """Calculates next version number and clean filename."""
        base_name, ext = prev_filename.rsplit('.', 1) if '.' in prev_filename else (prev_filename, '')
        m = re.search(r'_v(\d+)$', base_name)
        if m:
            curr_ver = int(m.group(1))
            next_ver = curr_ver + 1
            clean_base = re.sub(r'_v\d+$', '', base_name)
        else:
            curr_ver = 1
            next_ver = 2
            clean_base = base_name

        new_filename = f"{clean_base}_v{next_ver}.{ext}" if ext else f"{clean_base}_v{next_ver}"
        return next_ver, new_filename
