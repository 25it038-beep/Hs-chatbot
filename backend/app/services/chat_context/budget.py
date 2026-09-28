import re
from typing import Dict, Any, Optional
from app.services.chat_context.contracts import ContextBudget

# Known model context windows
MODEL_CONTEXT_LIMITS: Dict[str, int] = {
    # SambaNova / DeepSeek
    "DeepSeek-V3.2": 65536,
    "DeepSeek-V3.1": 65536,
    "Meta-Llama-3.3-70B-Instruct": 131072,
    "gemma-4-31B-it": 131072,
    "gpt-oss-120b": 131072,

    # NVIDIA NIM
    "nvidia/nemotron-3-ultra-550b-a55b": 131072,
    "moonshotai/kimi-k3": 262144,
    "meta/llama-3.1-70b-instruct": 131072,
    "meta/llama-3.3-70b-instruct": 131072,
    "meta/llama-3.2-11b-vision-instruct": 131072,
    "mistralai/mistral-large-2-instruct": 131072,
    "mistralai/codestral-22b-instruct-v0.1": 32768,
    "z-ai/glm-5.2": 131072,

    # Standard short models
    "llama-3.1-70b": 131072,
    "llama-3.3-70b": 131072,
    "codestral": 32768,
    "mistral-large": 131072,
    "glm-5.2": 131072,
}

DEFAULT_CONTEXT_LIMIT = 32768
DEFAULT_OUTPUT_BUDGET = 4096
DEFAULT_SAFETY_MARGIN = 0.15  # 15% safety headroom


def estimate_tokens(text: str) -> int:
    """
    Estimates token count for arbitrary text.
    Uses tiktoken if installed and available, otherwise high-precision heuristic.
    """
    if not text:
        return 0
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text, disallowed_special=()))
    except Exception:
        # Heuristic: 1 token ~= 4 characters or ~0.75 words
        words = len(text.split())
        chars = len(text)
        return max(1, int((words * 1.3 + chars / 4.0) / 2.0))


def compute_context_budget(
    model_id: str,
    output_budget: int = DEFAULT_OUTPUT_BUDGET,
    safety_margin: float = DEFAULT_SAFETY_MARGIN
) -> ContextBudget:
    """
    Computes token budget boundaries based on model capacity and safety margins.
    """
    max_context = MODEL_CONTEXT_LIMITS.get(model_id, DEFAULT_CONTEXT_LIMIT)
    # Check partial match if full model string wasn't in dict
    if model_id not in MODEL_CONTEXT_LIMITS:
        for k, v in MODEL_CONTEXT_LIMITS.items():
            if k.lower() in model_id.lower() or model_id.lower() in k.lower():
                max_context = v
                break

    safe_max = int(max_context * (1.0 - safety_margin))
    usable_budget = max(2048, safe_max - output_budget)

    return ContextBudget(
        model_id=model_id,
        max_context=max_context,
        safety_margin=safety_margin,
        usable_budget=usable_budget,
        output_budget=output_budget,
        remaining_tokens=usable_budget
    )
