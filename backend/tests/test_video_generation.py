"""Tests for the isolated AI Video Generation subsystem."""

import os
import io
import time
import pytest
import struct
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database import init_db, async_session
from app.models.user import User
from app.utils.security import hash_password, create_access_token
from app.services.video.models import model_registry
from app.services.video.validation import video_validator
from app.services.video.storage import video_storage
from app.services.video.enhancer import prompt_enhancer
from app.services.video.schemas import VideoGenerationRequest, VideoMode, VideoJobStatus


def make_minimal_mp4_bytes() -> bytes:
    """Creates a minimal valid MP4 container with ftyp box."""
    # Box size (32 bytes), 'ftyp', major_brand 'isom', minor_version 0x00000200, compatible brands 'isom', 'iso2', 'mp41'
    box_type = b"ftyp"
    major_brand = b"isom"
    minor_version = struct.pack(">I", 512)
    compatible_brands = b"isomiso2mp41"
    ftyp_payload = major_brand + minor_version + compatible_brands
    box_size = struct.pack(">I", 8 + len(ftyp_payload))
    ftyp_box = box_size + box_type + ftyp_payload
    # Add dummy mdat box to make it > 1024 bytes
    mdat_payload = b"\x00" * 1200
    mdat_box = struct.pack(">I", 8 + len(mdat_payload)) + b"mdat" + mdat_payload
    return ftyp_box + mdat_box


@pytest.fixture(autouse=True)
async def setup_test_users():
    await init_db()
    async with async_session() as session:
        u1 = User(
            id="vid-user-alpha",
            email="alpha@video.ai",
            username="alphavid",
            hashed_password=hash_password("password123"),
            is_active=True,
        )
        u2 = User(
            id="vid-user-beta",
            email="beta@video.ai",
            username="betavid",
            hashed_password=hash_password("password123"),
            is_active=True,
        )
        session.add(u1)
        session.add(u2)
        try:
            await session.commit()
        except Exception:
            await session.rollback()


@pytest.mark.asyncio
async def test_video_models_registry_and_dimensions():
    models = model_registry.list_models()
    assert len(models) >= 2
    model_ids = [m.model_id for m in models]
    assert "wan-ai/wan2.2" in model_ids
    assert "nvidia/cosmos3-nano" in model_ids

    # Check dimension calculations
    dim_16_9 = model_registry.calculate_dimensions("720p", "16:9")
    assert dim_16_9 == (1280, 720)
    dim_9_16 = model_registry.calculate_dimensions("720p", "9:16")
    assert dim_9_16 == (720, 1280)
    dim_1_1 = model_registry.calculate_dimensions("480p", "1:1")
    assert dim_1_1 == (480, 480)


def test_video_validator_mp4():
    mp4_bytes = make_minimal_mp4_bytes()
    is_valid, err, meta = video_validator.validate_mp4_bytes(mp4_bytes)
    assert is_valid is True
    assert err is None
    assert meta["format"] == "mp4"
    assert meta["major_brand"] == "isom"

    # Corrupt data
    is_valid, err, _ = video_validator.validate_mp4_bytes(b"corrupt non-video payload 1234567890")
    assert is_valid is False
    assert "missing ISO MP4 'ftyp'" in err


def test_prompt_enhancer():
    raw_prompt = "A red sports car racing down the coastal highway"
    enhanced = prompt_enhancer.enhance(raw_prompt, style="cinematic")
    assert enhanced.original_prompt == raw_prompt
    assert "camera" in enhanced.enhanced_prompt.lower() or "shot" in enhanced.enhanced_prompt.lower()
    assert "lighting" in enhanced.enhanced_prompt.lower() or "light" in enhanced.enhanced_prompt.lower()
    assert enhanced.enhanced_prompt.startswith(raw_prompt)


@pytest.mark.asyncio
async def test_video_api_health_and_models():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Health check
        h_res = await client.get("/api/video/health")
        assert h_res.status_code == 200
        health_data = h_res.json()
        assert "active_models" in health_data

        # Models listing
        m_res = await client.get("/api/video/models")
        assert m_res.status_code == 200
        models_data = m_res.json()
        assert any(m["model_id"] == "wan-ai/wan2.2" for m in models_data)


@pytest.mark.asyncio
async def test_video_reference_upload_and_prompt_enhance():
    token = create_access_token({"sub": "vid-user-alpha"})
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test prompt enhance endpoint
        enh_res = await client.post(
            "/api/video/enhance-prompt",
            json={"prompt": "Drone shot of tropical beach sunset", "style": "cinematic"},
            headers=headers,
        )
        assert enh_res.status_code == 200
        assert "enhanced_prompt" in enh_res.json()

        # Test reference image upload
        dummy_img = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        files = {"file": ("reference.png", dummy_img, "image/png")}
        up_res = await client.post("/api/video/upload-reference", files=files, headers=headers)
        assert up_res.status_code == 200
        ref_data = up_res.json()
        assert "reference_image_id" in ref_data
        ref_id = ref_data["reference_image_id"]

        # Verify reference path stored safely
        ref_path = video_storage.get_reference_image_path("vid-user-alpha", ref_id)
        assert ref_path is not None
        assert os.path.exists(ref_path)


@pytest.mark.asyncio
async def test_video_generation_lifecycle_and_streaming():
    token = create_access_token({"sub": "vid-user-alpha"})
    headers = {"Authorization": f"Bearer {token}"}

    valid_mp4 = make_minimal_mp4_bytes()

    # Mock provider generate_video so test doesn't call live NVIDIA credit endpoints
    with patch("app.services.video.providers.wan.NvidiaWanVideoProvider.generate_video", new_callable=AsyncMock) as mock_wan_gen:
        mock_wan_gen.return_value = valid_mp4

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Enqueue generation job
            gen_payload = {
                "prompt": "Futuristic neon city under rain at night",
                "model": "wan-ai/wan2.2",
                "mode": "text_to_video",
                "aspect_ratio": "16:9",
                "duration_seconds": 5,
                "resolution": "720p",
                "fps": 24,
            }
            res = await client.post("/api/video/generate", json=gen_payload, headers=headers)
            assert res.status_code == 200
            job_data = res.json()
            job_id = job_data["id"]
            assert job_data["status"] in ["queued", "submitting", "generating"]

            # 2. Poll until completed (with brief sleep to let worker finish)
            completed_job = None
            for _ in range(20):
                import asyncio
                await asyncio.sleep(0.1)
                poll_res = await client.get(f"/api/video/jobs/{job_id}", headers=headers)
                assert poll_res.status_code == 200
                st = poll_res.json()["status"]
                if st == "completed":
                    completed_job = poll_res.json()
                    break

            assert completed_job is not None
            assert completed_job["status"] == "completed"
            assert completed_job["file_size"] == len(valid_mp4)
            assert completed_job["stream_url"] is not None

            # 3. Test HTTP 206 Range Streaming
            stream_headers = {**headers, "Range": "bytes=0-499"}
            stream_res = await client.get(f"/api/video/{job_id}/stream", headers=stream_headers)
            assert stream_res.status_code == 206
            assert stream_res.headers["Content-Range"].startswith("bytes 0-499/")
            assert len(stream_res.content) == 500
            assert stream_res.content == valid_mp4[:500]

            # Full download test
            dl_res = await client.get(f"/api/video/{job_id}/download", headers=headers)
            assert dl_res.status_code == 200
            assert dl_res.content == valid_mp4
            assert "attachment" in dl_res.headers.get("content-disposition", "")


@pytest.mark.asyncio
async def test_tenant_isolation_and_security():
    token_alpha = create_access_token({"sub": "vid-user-alpha"})
    token_beta = create_access_token({"sub": "vid-user-beta"})

    headers_alpha = {"Authorization": f"Bearer {token_alpha}"}
    headers_beta = {"Authorization": f"Bearer {token_beta}"}

    # Save video directly for User Alpha
    valid_mp4 = make_minimal_mp4_bytes()
    alpha_job_id = "test_alpha_video_secure"
    video_storage.save_video(
        user_id="vid-user-alpha",
        job_id=alpha_job_id,
        video_bytes=valid_mp4,
        metadata={"job_id": alpha_job_id, "prompt": "Alpha secret video"},
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # User Alpha can stream their video
        res_alpha = await client.get(f"/api/video/{alpha_job_id}/stream", headers=headers_alpha)
        assert res_alpha.status_code in (200, 206)

        # User Beta CANNOT stream User Alpha's video (404 isolation)
        res_beta = await client.get(f"/api/video/{alpha_job_id}/stream", headers=headers_beta)
        assert res_beta.status_code == 404

        # User Beta CANNOT download User Alpha's video
        dl_beta = await client.get(f"/api/video/{alpha_job_id}/download", headers=headers_beta)
        assert dl_beta.status_code == 404

        # Unauthenticated user cannot stream without token
        unauth = await client.get(f"/api/video/{alpha_job_id}/stream")
        assert unauth.status_code == 401


@pytest.mark.asyncio
async def test_video_job_cancellation():
    token = create_access_token({"sub": "vid-user-alpha"})
    headers = {"Authorization": f"Bearer {token}"}

    # Provider that hangs waiting for cancellation
    async def hanging_generate(*args, **kwargs):
        import asyncio
        await asyncio.sleep(10.0)
        return make_minimal_mp4_bytes()

    with patch("app.services.video.providers.wan.NvidiaWanVideoProvider.generate_video", side_effect=hanging_generate):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            gen_res = await client.post(
                "/api/video/generate",
                json={"prompt": "Slow generation prompt", "model": "wan-ai/wan2.2"},
                headers=headers,
            )
            assert gen_res.status_code == 200
            job_id = gen_res.json()["id"]

            # Cancel job
            cancel_res = await client.post(f"/api/video/jobs/{job_id}/cancel", headers=headers)
            assert cancel_res.status_code == 200
            assert cancel_res.json()["status"] == "cancelled"

            # Check status reflects cancelled
            stat_res = await client.get(f"/api/video/jobs/{job_id}", headers=headers)
            assert stat_res.status_code == 200
            assert stat_res.json()["status"] == "cancelled"
