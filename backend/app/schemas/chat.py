from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ChatFolderCreate(BaseModel):
    name: str
    icon: Optional[str] = None
    color: Optional[str] = None


class ChatFolderResponse(BaseModel):
    id: str
    name: str
    icon: Optional[str] = None
    color: Optional[str] = None
    sort_order: int
    created_at: datetime

    class Config:
        from_attributes = True


class ChatCreate(BaseModel):
    title: Optional[str] = None
    model: str = "llama-3.1-70b"
    provider: str = "nvidia"
    system_prompt: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096
    folder_id: Optional[str] = None


class ChatUpdate(BaseModel):
    title: Optional[str] = None
    model: Optional[str] = None
    provider: Optional[str] = None
    system_prompt: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    folder_id: Optional[str] = None
    is_pinned: Optional[bool] = None


class ChatResponse(BaseModel):
    id: str
    title: Optional[str] = None
    model: str
    provider: str
    system_prompt: Optional[str] = None
    temperature: float
    max_tokens: int
    is_pinned: bool
    is_archived: bool
    token_count: int
    folder_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    class Config:
        from_attributes = True
