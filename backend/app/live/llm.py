"""
NVIDIA LLM Client for HSBot Live Voice
Streams conversational responses from NVIDIA NIM OpenAI-compatible API
using a persistent warm HTTP client for minimum Time-To-First-Token.
"""

import asyncio
import json
import logging
from typing import AsyncGenerator, List, Dict, Optional
import httpx
from app.config import settings

logger = logging.getLogger("hsbot.live.llm")

NVIDIA_CHAT_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
# Fast, expressive live model
LIVE_MODEL = "meta/llama-3.2-11b-vision-instruct"

SYSTEM_PROMPT = (
    "You are HSBot, an intelligent and friendly AI assistant speaking in real-time live voice. "
    "Be brief, conversational, and direct. Respond in 1 or 2 natural spoken sentences. "
    "Never use markdown, lists, symbols, or code blocks."
)


class NvidiaLiveLLM:
    def __init__(self):
        keys = settings.nvidia_api_keys.split(",") if settings.nvidia_api_keys else []
        self.api_key = keys[0].strip() if keys else "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"
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(20.0, connect=5.0),
                limits=httpx.Limits(max_keepalive_connections=5, keepalive_expiry=60.0),
            )
        return self._client

    async def stream_reply(
        self,
        user_message: str,
        history: List[Dict[str, str]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Streams text tokens from NVIDIA NIM LLM.
        """
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        if history:
            for item in history[-4:]:
                messages.append(item)

        messages.append({"role": "user", "content": user_message})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }

        payload = {
            "model": LIVE_MODEL,
            "messages": messages,
            "temperature": 0.5,
            "max_tokens": 85,
            "stream": True,
        }

        client = self._get_client()
        try:
            async with client.stream("POST", NVIDIA_CHAT_URL, json=payload, headers=headers) as response:
                if response.status_code != 200:
                    err_body = await response.aread()
                    logger.error(f"NVIDIA LLM error {response.status_code}: {err_body.decode('utf-8', 'replace')}")
                    yield "I am having trouble connecting to NVIDIA services right now."
                    return

                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue

                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break

                    try:
                        data = json.loads(data_str)
                        choices = data.get("choices", [])
                        if choices:
                            delta = choices[0].get("delta", {})
                            chunk = delta.get("content", "")
                            if chunk:
                                yield chunk
                    except Exception:
                        continue

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Exception during NVIDIA LLM stream: {e}")
            yield "Sorry, a temporary network error occurred."

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# Singleton instance
live_llm = NvidiaLiveLLM()
