import time
import json
from typing import AsyncGenerator, Optional
import httpx
from app.services.nvidia.config import NVIDIA_BASE_URL, NVIDIA_MODELS
from app.services.nvidia.key_manager import KeyManager
from app.services.model_providers.base import ModelResponse, StreamChunk

key_manager = KeyManager()


class NvidiaChatProvider:
    def __init__(self):
        self.base_url = NVIDIA_BASE_URL

    def _get_model_id(self, model_key: str) -> str:
        model_conf = NVIDIA_MODELS.get(model_key)
        if model_conf:
            return model_conf["id"]
        return model_key

    def _get_model_config(self, model_key: str) -> dict:
        return NVIDIA_MODELS.get(model_key, {})

    async def generate(
        self,
        messages: list[dict],
        model: str = "llama-3.1-70b",
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        top_p: float = 0.95,
        json_mode: bool = False,
        reasoning: bool = False,
        tools: Optional[list[dict]] = None,
    ) -> ModelResponse:
        start = time.time()
        api_key = key_manager.get_key()
        if not api_key:
            raise ValueError("No available NVIDIA API keys")

        model_id = self._get_model_id(model)
        model_conf = self._get_model_config(model)

        payload = {
            "model": model_id,
            "messages": self._build_messages(messages, system_prompt),
            "temperature": temperature,
            "max_tokens": max_tokens or model_conf.get("max_tokens", 4096),
            "top_p": top_p,
            "stream": False,
        }

        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        if model_conf.get("supports_thinking") and reasoning:
            if "nemotron" in model_id.lower():
                payload["chat_template_kwargs"] = {"enable_thinking": True}
                payload["reasoning_budget"] = 16384
            else:
                payload["chat_template_kwargs"] = {"thinking": True}

        if tools:
            payload["tools"] = tools

        headers = self._build_headers(api_key.key)

        async with httpx.AsyncClient(timeout=300.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                if response.status_code in (429, 503, 529):
                    key_manager.record_failure(api_key, f"server_busy: {response.status_code}")
                    return await self._retry_with_fallback(messages, model, system_prompt, temperature, max_tokens, top_p, json_mode, reasoning, tools)
                if response.status_code == 401:
                    key_manager.record_failure(api_key, "unauthorized: 401")
                    return await self._retry_with_fallback(messages, model, system_prompt, temperature, max_tokens, top_p, json_mode, reasoning, tools)
                if response.status_code == 404:
                    key_manager.record_failure(api_key, "model_not_found: 404")
                    return await self._retry_with_fallback(messages, model, system_prompt, temperature, max_tokens, top_p, json_mode, reasoning, tools)
                if response.status_code >= 500:
                    key_manager.record_failure(api_key, f"server_error: {response.status_code}")
                    return await self._retry_with_fallback(messages, model, system_prompt, temperature, max_tokens, top_p, json_mode, reasoning, tools)

                response.raise_for_status()
                data = response.json()
                latency = (time.time() - start) * 1000

                content = data["choices"][0]["message"]["content"] or ""
                usage = data.get("usage", {})

                key_manager.record_success(api_key, usage.get("total_tokens", 0))

                reasoning_content = None
                if model_conf.get("supports_thinking") and reasoning:
                    reasoning_content = data["choices"][0].get("message", {}).get("reasoning_content")

                return ModelResponse(
                    content=content,
                    model=model,
                    provider="nvidia",
                    reasoning=reasoning_content,
                    input_tokens=usage.get("prompt_tokens", 0),
                    output_tokens=usage.get("completion_tokens", 0),
                    latency_ms=latency,
                )

            except httpx.TimeoutException:
                key_manager.record_failure(api_key, "timeout")
                return await self._retry_with_fallback(messages, model, system_prompt, temperature, max_tokens, top_p, json_mode, reasoning, tools)
            except Exception as e:
                key_manager.record_failure(api_key, str(e))
                raise

    async def generate_stream(
        self,
        messages: list[dict],
        model: str = "llama-3.1-70b",
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        top_p: float = 0.95,
        json_mode: bool = False,
        reasoning: bool = False,
        tools: Optional[list[dict]] = None,
    ) -> AsyncGenerator[StreamChunk, None]:
        api_key = key_manager.get_key()
        if not api_key:
            yield StreamChunk(type="error", content="No available NVIDIA API keys", done=True)
            return

        model_id = self._get_model_id(model)
        model_conf = self._get_model_config(model)

        payload = {
            "model": model_id,
            "messages": self._build_messages(messages, system_prompt),
            "temperature": temperature,
            "max_tokens": max_tokens or model_conf.get("max_tokens", 4096),
            "top_p": top_p,
            "stream": True,
        }

        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        if model_conf.get("supports_thinking") and reasoning:
            if "nemotron" in model_id.lower():
                payload["chat_template_kwargs"] = {"enable_thinking": True}
                payload["reasoning_budget"] = 16384
            else:
                payload["chat_template_kwargs"] = {"thinking": True}

        if tools:
            payload["tools"] = tools

        headers = self._build_headers(api_key.key)
        input_tokens = 0
        output_tokens = 0
        full_content = ""
        full_reasoning = ""

        async with httpx.AsyncClient(timeout=300.0) as client:
            try:
                async with client.stream("POST", f"{self.base_url}/chat/completions", headers=headers, json=payload) as response:
                    if response.status_code in (429, 503, 529):
                        key_manager.record_failure(api_key, f"server_busy: {response.status_code}")
                        yield StreamChunk(type="error", content="Server busy, switching model...", done=False)
                        async for chunk in self._fallback_stream(messages, model, system_prompt, temperature, max_tokens):
                            yield chunk
                        return
                    if response.status_code >= 500:
                        key_manager.record_failure(api_key, f"server_error: {response.status_code}")
                        yield StreamChunk(type="error", content="Server error, switching model...", done=False)
                        async for chunk in self._fallback_stream(messages, model, system_prompt, temperature, max_tokens):
                            yield chunk
                        return

                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        if line.startswith("data: "):
                            raw = line[6:].strip()
                            if raw == "[DONE]":
                                continue
                            try:
                                chunk_data = json.loads(raw)
                                delta = chunk_data.get("choices", [{}])[0].get("delta", {})
                                reason_text = delta.get("reasoning_content")
                                if reason_text:
                                    full_reasoning += reason_text
                                    yield StreamChunk(
                                        type="reasoning",
                                        content=reason_text,
                                        model=model,
                                        provider="nvidia",
                                    )
                                if delta.get("content"):
                                    full_content += delta["content"]
                                    yield StreamChunk(
                                        type="content",
                                        content=delta["content"],
                                        model=model,
                                        provider="nvidia",
                                    )
                                finish_reason = chunk_data.get("choices", [{}])[0].get("finish_reason")
                                if finish_reason == "tool_calls":
                                    pass
                                usage = chunk_data.get("usage", {})
                                if usage:
                                    input_tokens = usage.get("prompt_tokens", 0)
                                    output_tokens = usage.get("completion_tokens", 0)
                            except json.JSONDecodeError:
                                continue

                    key_manager.record_success(api_key)
                    yield StreamChunk(
                        type="done",
                        model=model,
                        provider="nvidia",
                        reasoning=full_reasoning or None,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        done=True,
                    )

            except Exception as e:
                key_manager.record_failure(api_key, str(e))
                yield StreamChunk(type="error", content=str(e), done=True)

    async def _retry_with_fallback(self, messages, model, system_prompt, temperature, max_tokens, top_p, json_mode, reasoning, tools):
        from app.services.nvidia.config import TASK_ROUTES
        model_type = "chat"
        for m_type, m_list in TASK_ROUTES.items():
            if model in m_list.get("fallback", []) or model == m_list.get("default"):
                model_type = m_type
                break

        fallbacks = TASK_ROUTES.get(model_type, {}).get("fallback", [])
        for fb_model in fallbacks:
            if fb_model != model:
                try:
                    return await self.generate(
                        messages, model=fb_model, system_prompt=system_prompt,
                        temperature=temperature, max_tokens=max_tokens,
                        top_p=top_p, json_mode=json_mode, reasoning=reasoning, tools=tools,
                    )
                except Exception:
                    continue
        raise ValueError("All models exhausted")

    async def _fallback_stream(self, messages, model, system_prompt, temperature, max_tokens):
        from app.services.nvidia.config import TASK_ROUTES
        model_type = "chat"
        for m_type, m_list in TASK_ROUTES.items():
            if model in m_list.get("fallback", []) or model == m_list.get("default"):
                model_type = m_type
                break

        fallbacks = TASK_ROUTES.get(model_type, {}).get("fallback", [])
        for fb_model in fallbacks:
            if fb_model != model:
                try:
                    async for chunk in self.generate_stream(
                        messages, model=fb_model, system_prompt=system_prompt,
                        temperature=temperature, max_tokens=max_tokens,
                    ):
                        yield chunk
                    return
                except Exception:
                    continue

    def _build_messages(self, messages: list[dict], system_prompt: Optional[str] = None) -> list[dict]:
        result = []
        if system_prompt:
            result.append({"role": "system", "content": system_prompt})
        result.extend(messages)
        return result

    def _build_headers(self, api_key: str) -> dict:
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
