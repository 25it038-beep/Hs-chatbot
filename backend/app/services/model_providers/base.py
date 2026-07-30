from typing import AsyncGenerator, Optional, Protocol
from pydantic import BaseModel


class ModelResponse(BaseModel):
    content: str
    model: str
    provider: str
    reasoning: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0


class StreamChunk(BaseModel):
    type: str
    content: str = ""
    reasoning: str | None = None
    model: str = ""
    provider: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    done: bool = False


class ModelProvider(Protocol):
    def __init__(self, provider_name: str):
        ...

    async def generate(
        self,
        messages: list[dict],
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[dict] | None = None,
    ) -> ModelResponse:
        ...

    async def generate_stream(
        self,
        messages: list[dict],
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[dict] | None = None,
    ) -> AsyncGenerator[StreamChunk, None]:
        ...
        yield StreamChunk(type="done", done=True)
