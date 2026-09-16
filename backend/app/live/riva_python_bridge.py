"""
Pure Python async gRPC bridge for NVIDIA Riva ASR + TTS via NVCF.
Replaces the Node.js persistent_riva_worker.js entirely.
No Node.js required — uses grpcio + grpcio-tools directly.
"""

import asyncio
import logging
import os
import sys
from typing import AsyncGenerator, Optional

logger = logging.getLogger("hsbot.live.riva_python_bridge")

NVCF_HOST = "grpc.nvcf.nvidia.com:443"
NVCF_FUNCTION_TTS = os.environ.get("NVCF_FUNCTION_TTS", "ddacc747-1269-4fab-bfd9-8f593dead106")
NVCF_FUNCTION_ASR = os.environ.get("NVCF_FUNCTION_ASR", "d3fe9151-442b-4204-a70d-5fcc597fd610")

# Resolve API key from environment
def _get_api_key() -> str:
    raw = os.environ.get("NVIDIA_API_KEYS", "") or os.environ.get("NVIDIA_API_KEY", "")
    if raw:
        return raw.split(",")[0].strip()
    # Hardcoded fallback key (same as in persistent_riva_worker.js)
    return "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"

# Proto stub location — generated at Docker build time or found via PYTHONPATH
PROTO_GENERATED_DIR = os.path.join(os.path.dirname(__file__), "grpc_stubs")

_grpc_ready = False
_grpc = None
_tts_pb2 = None
_tts_pb2_grpc = None
_asr_pb2 = None
_asr_pb2_grpc = None
_audio_pb2 = None


def _load_grpc_stubs():
    global _grpc_ready, _grpc, _tts_pb2, _tts_pb2_grpc, _asr_pb2, _asr_pb2_grpc, _audio_pb2
    if _grpc_ready:
        return True
    try:
        import grpc
        import grpc.aio
        _grpc = grpc

        if PROTO_GENERATED_DIR not in sys.path:
            sys.path.insert(0, PROTO_GENERATED_DIR)

        from riva.proto import riva_tts_pb2, riva_tts_pb2_grpc as tts_grpc
        from riva.proto import riva_asr_pb2, riva_asr_pb2_grpc as asr_grpc
        from riva.proto import riva_audio_pb2

        _tts_pb2 = riva_tts_pb2
        _tts_pb2_grpc = tts_grpc
        _asr_pb2 = riva_asr_pb2
        _asr_pb2_grpc = asr_grpc
        _audio_pb2 = riva_audio_pb2

        _grpc_ready = True
        logger.info("[RivaPython] gRPC stubs loaded successfully")
        return True
    except Exception as e:
        logger.error(f"[RivaPython] Failed to load gRPC stubs: {e}")
        return False


def _make_channel():
    """Creates an authenticated secure gRPC channel to NVCF."""
    creds = _grpc.ssl_channel_credentials()
    return _grpc.aio.secure_channel(
        NVCF_HOST,
        creds,
        options=[
            ("grpc.max_send_message_length", 64 * 1024 * 1024),
            ("grpc.max_receive_message_length", 64 * 1024 * 1024),
            ("grpc.keepalive_time_ms", 30000),
            ("grpc.keepalive_timeout_ms", 10000),
        ],
    )


async def transcribe(pcm_bytes: bytes, sample_rate: int = 16000, timeout: float = 10.0) -> str:
    """
    Transcribes raw 16-bit mono PCM using NVIDIA Parakeet ASR via NVCF gRPC.
    """
    if not pcm_bytes:
        return ""
    if not _load_grpc_stubs():
        raise RuntimeError("Riva gRPC stubs not available")

    api_key = _get_api_key()
    metadata = [
        ("function-id", NVCF_FUNCTION_ASR),
        ("authorization", f"Bearer {api_key}"),
    ]

    config = _asr_pb2.RecognitionConfig(
        encoding=_audio_pb2.LINEAR_PCM,
        sample_rate_hertz=sample_rate,
        language_code="en-US",
        max_alternatives=1,
        enable_automatic_punctuation=True,
    )
    request = _asr_pb2.RecognizeRequest(config=config, audio=pcm_bytes)

    try:
        async with _make_channel() as channel:
            stub = _asr_pb2_grpc.RivaSpeechRecognitionStub(channel)
            response = await asyncio.wait_for(
                stub.Recognize(request, metadata=metadata),
                timeout=timeout,
            )
            if response.results and response.results[0].alternatives:
                return response.results[0].alternatives[0].transcript.strip()
    except asyncio.TimeoutError:
        logger.warning(f"[RivaPython ASR] Timed out after {timeout}s")
    except Exception as e:
        logger.error(f"[RivaPython ASR] Error: {e}")
    return ""


async def stream_synthesize(
    text: str,
    voice: str = "Chatterbox-Multilingual",
    sample_rate: int = 24000,
    timeout: float = 15.0,
) -> AsyncGenerator[bytes, None]:
    """
    Streams raw PCM audio from NVIDIA Chatterbox TTS via NVCF gRPC.
    """
    if not text.strip():
        return
    if not _load_grpc_stubs():
        raise RuntimeError("Riva gRPC stubs not available")

    api_key = _get_api_key()
    metadata = [
        ("function-id", NVCF_FUNCTION_TTS),
        ("authorization", f"Bearer {api_key}"),
    ]

    async def _request_generator():
        yield _tts_pb2.SynthesizeSpeechRequest(
            text=text.strip(),
            language_code="en-US",
            encoding=_audio_pb2.LINEAR_PCM,
            sample_rate_hz=sample_rate,
            voice_name=voice,
        )

    try:
        async with _make_channel() as channel:
            stub = _tts_pb2_grpc.RivaSpeechSynthesisStub(channel)
            async for response in stub.SynthesizeOnline(
                _request_generator(), metadata=metadata
            ):
                if response.audio:
                    yield response.audio
    except asyncio.TimeoutError:
        logger.warning(f"[RivaPython TTS] Timed out after {timeout}s")
    except Exception as e:
        logger.error(f"[RivaPython TTS] Error: {e}")
