from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime


class MessageCreate(BaseModel):
    role: str
    content: str
    model: Optional[str] = None
    provider: Optional[str] = None
    parent_id: Optional[str] = None


class MessageResponse(BaseModel):
    id: str
    chat_id: str
    role: str
    content: str
    model: Optional[str] = None
    provider: Optional[str] = None
    reasoning: Optional[str] = None
    extra_data: Optional[Any] = None
    token_count: int
    input_tokens: int
    output_tokens: int
    latency_ms: Optional[float] = None
    parent_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    message: str
    chat_id: Optional[str] = None
    model: Optional[str] = None
    provider: Optional[str] = None
    system_prompt: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    stream: bool = True
    files: Optional[list[str]] = None
    tools: Optional[list[dict]] = None


class ChatResponse(BaseModel):
    id: str
    chat_id: str
    role: str
    content: str
    model: Optional[str] = None
    provider: Optional[str] = None
    reasoning: Optional[str] = None
    token_count: int
    input_tokens: int
    output_tokens: int
    latency_ms: Optional[float] = None
    created_at: datetime
