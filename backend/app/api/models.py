from fastapi import APIRouter
from pydantic import BaseModel
from app.services.nvidia.config import NVIDIA_MODELS

router = APIRouter(prefix="/api/models", tags=["models"])


class ModelInfo(BaseModel):
    id: str
    name: str
    provider: str
    capabilities: list[str]


def _build_models():
    models = []
    # NVIDIA NIM models exclusively
    for key, conf in NVIDIA_MODELS.items():
        models.append({
            "id": key,
            "name": conf["name"],
            "provider": "nvidia",
            "capabilities": conf.get("capabilities", ["chat"]),
        })
    return models


AVAILABLE_MODELS = _build_models()

PROVIDERS: list[dict] = [
    {"id": "nvidia", "name": "NVIDIA NIM", "icon": "cpu", "requires_key": True, "models": len(AVAILABLE_MODELS)},
]


@router.get("", response_model=list[ModelInfo])
async def list_models():
    return [ModelInfo(**m) for m in AVAILABLE_MODELS]


@router.get("/providers")
async def list_providers():
    return PROVIDERS


@router.get("/nvidia")
async def list_nvidia_models():
    return [
        {"key": k, **v}
        for k, v in NVIDIA_MODELS.items()
    ]
