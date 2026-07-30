from app.services.nvidia.chat import NvidiaChatProvider
from app.services.nvidia.vision import NvidiaVisionProvider
from app.services.nvidia.image import NvidiaImageProvider
from app.services.nvidia.embeddings import NvidiaEmbeddingsProvider
from app.services.nvidia.speech import NvidiaSpeechProvider
from app.services.nvidia.router import ai_router, AIRouter
from app.services.nvidia.key_manager import KeyManager
from app.services.nvidia.config import NVIDIA_MODELS, TASK_ROUTES

__all__ = [
    "NvidiaChatProvider",
    "NvidiaVisionProvider",
    "NvidiaImageProvider",
    "NvidiaEmbeddingsProvider",
    "NvidiaSpeechProvider",
    "ai_router",
    "AIRouter",
    "KeyManager",
    "NVIDIA_MODELS",
    "TASK_ROUTES",
]
