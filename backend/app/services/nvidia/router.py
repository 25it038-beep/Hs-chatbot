import re
from typing import Optional
from app.services.nvidia.config import TASK_PATTERNS, CHAT_TASK_KEYWORDS, TASK_ROUTES


class AIRouter:
    def detect_task(self, message: str) -> str:
        text = message.lower()

        # Check for image generation tasks with typo tolerance (genrate, cretae, iamge, etc.)
        image_patterns = [
            r"/(image|img|draw)\b",
            r"\b(gen+er?at[eio]*|cr[ea]*t[eao]*|make|draw|render|illustrate|paint|sketch)\b.*\b(i[am]*g[e]*|pic[ture]*|photo|art[work]*|drawing|painting)\b",
            r"\b(draw|illustrate|paint|sketch)\b\s+(a\s+|an\s+|the\s+|me\s+)?",
            r"text.?to.?image",
        ]
        if any(re.search(pat, text) for pat in image_patterns):
            return "image_generation"

        # Check for image search tasks
        for kw in TASK_PATTERNS["web_images"]:
            if kw in text:
                return "web_images"

        # Check for vision tasks
        if any(kw in text for kw in TASK_PATTERNS["vision"]):
            return "vision"

        # Check for coding tasks
        for kw in TASK_PATTERNS["coding"]:
            if " " in kw:
                if kw in text:
                    return "coding"
            else:
                if re.search(rf"\b{re.escape(kw)}\b", text):
                    return "coding"

        # Check for reasoning tasks
        for kw in TASK_PATTERNS["reasoning"]:
            if kw in text:
                return "reasoning"

        # Check for explicit chat
        for kw in CHAT_TASK_KEYWORDS["chat"]:
            if kw in text:
                return "chat"

        # Default: if message starts with code-like patterns
        if re.match(r"^(def |class |function |const |import |from |#|\/\/|<!--)", text):
            return "coding"

        return "chat"

    def get_best_model(self, task: str, preferred_model: Optional[str] = None) -> str:
        if preferred_model:
            return preferred_model

        route = TASK_ROUTES.get(task, TASK_ROUTES["chat"])
        return route["default"]

    def get_fallback_models(self, task: str) -> list[str]:
        route = TASK_ROUTES.get(task, TASK_ROUTES["chat"])
        return route.get("fallback", [])

    def get_model_for_message(self, message: str, preferred_model: Optional[str] = None) -> tuple[str, str]:
        task = self.detect_task(message)
        model = self.get_best_model(task, preferred_model)
        return task, model


ai_router = AIRouter()
