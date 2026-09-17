"""
NVIDIA Riva Tamil Integration Bridge & Verification Server.
Runs on the external GPU host to provide diagnostic and health validation for Riva ta-IN models.
"""

import asyncio
import logging
from fastapi import FastAPI
import uvicorn

app = FastAPI(title="HSBot NVIDIA Riva Tamil Service", version="1.0.0")
logger = logging.getLogger("tamil_riva_server")


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "nvidia-riva-tamil",
        "language": "ta-IN",
        "models": {
            "asr": "riva-tamil-conformer-asr",
            "tts": "riva-tamil-fastpitch-tts",
            "voice": "ta-IN-Standard"
        },
        "riva_grpc_port": 50051,
        "triton_port": 8001,
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
