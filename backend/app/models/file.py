import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class GeneratedFile(Base):
    __tablename__ = "generated_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    conversation_id: Mapped[str] = mapped_column(String(36), ForeignKey("chats.id", ondelete="CASCADE"), nullable=True)
    message_id: Mapped[str] = mapped_column(String(36), nullable=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(50), default="ready")
    processing_stage: Mapped[str] = mapped_column(String(50), nullable=True, default="READY")
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    extracted_text_path: Mapped[str] = mapped_column(String(500), nullable=True)
    chunks_path: Mapped[str] = mapped_column(String(500), nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=True)
    preview_data: Mapped[str] = mapped_column(Text, nullable=True)
    design_spec: Mapped[str] = mapped_column(Text, nullable=True)
    content_data: Mapped[str] = mapped_column(Text, nullable=True)
    verification_result: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=True)

    user = relationship("User", foreign_keys=[user_id])
    chat = relationship("Chat", foreign_keys=[conversation_id])
