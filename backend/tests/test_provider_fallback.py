import json
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import async_session, init_db
from app.models.user import User
from app.utils.security import hash_password, create_access_token
from app.services.model_providers.base import StreamChunk


@pytest.mark.asyncio
async def test_sambanova_missing_key_fallback_to_nvidia():
    await init_db()

    # Ensure test user exists
    async with async_session() as session:
        user = User(
            id="test-fallback-user",
            email="fallback@hsbot.ai",
            username="fallbackuser",
            hashed_password=hash_password("password123"),
            is_active=True,
        )
        session.add(user)
        try:
            await session.commit()
        except Exception:
            await session.rollback()

    token = create_access_token({"sub": "test-fallback-user"})
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create a chat with provider sambanova
        chat_resp = await client.post(
            "/api/chats",
            json={"title": "Test Chat", "model": "DeepSeek-V3.2", "provider": "sambanova"},
            headers=headers,
        )
        assert chat_resp.status_code == 200
        chat_id = chat_resp.json()["id"]

        # Mock NVIDIA provider so we do not make a live external API call during unit test
        async def fake_stream(*args, **kwargs):
            yield StreamChunk(type="content", content="Hello from NVIDIA fallback!", model="llama-3.2-11b", provider="nvidia")
            yield StreamChunk(type="done", model="llama-3.2-11b", provider="nvidia", done=True)

        mock_nvidia_provider = MagicMock()
        mock_nvidia_provider.generate_stream = fake_stream

        # Ensure sambanova_api_key is None to simulate Render / unconfigured env
        with patch("app.config.settings.sambanova_api_key", None), \
             patch("app.config.settings.nvidia_api_keys", "nvapi-test-key"), \
             patch("app.services.chat.get_provider") as mock_get_provider:
            
            def side_effect(provider_name):
                if provider_name == "sambanova":
                    raise ValueError("Missing API key for provider 'sambanova'. Set SAMBANOVA_API_KEY in the environment.")
                return mock_nvidia_provider

            mock_get_provider.side_effect = side_effect

            payload = {
                "message": "Hello, how are you?",
                "chat_id": chat_id,
                "provider": "sambanova",
                "stream": True,
            }
            res = await client.post("/api/chats/messages", json=payload, headers=headers)
            assert res.status_code == 200

            chunks = []
            for line in res.text.split("\n"):
                if line.startswith("data: "):
                    raw = line[6:].strip()
                    if raw and raw != "[DONE]":
                        try:
                            chunks.append(json.loads(raw))
                        except Exception:
                            pass

            # Verify no error chunk about missing SAMBANOVA_API_KEY
            error_chunks = [c for c in chunks if c.get("type") == "error"]
            assert len(error_chunks) == 0, f"Unexpected error chunk: {error_chunks}"

            # Verify response was received from fallback
            content_chunks = [c for c in chunks if c.get("type") == "content"]
            full_text = "".join(c.get("content", "") for c in content_chunks)
            assert "Hello from NVIDIA fallback!" in full_text
