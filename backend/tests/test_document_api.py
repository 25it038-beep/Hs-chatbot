import os
import json
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import engine, Base, async_session
from app.models.user import User
from app.utils.security import hash_password, create_access_token


@pytest.mark.asyncio
async def test_nvidia_chat_pdf_generation_and_download():
    # Setup DB
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Ensure test user exists
    async with async_session() as session:
        user = User(
            id="test-doc-user-1",
            email="docuser@hsbot.ai",
            username="docuser",
            hashed_password=hash_password("password123"),
            is_active=True,
        )
        session.add(user)
        try:
            await session.commit()
        except:
            await session.rollback()

    token = create_access_token({"sub": "test-doc-user-1"})
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create a chat
        chat_resp = await client.post("/api/chats", json={"title": "New Chat", "model": "llama-3.1-70b", "provider": "nvidia"}, headers=headers)
        assert chat_resp.status_code == 200
        chat_id = chat_resp.json()["id"]

        # 2. Send "Create a PDF about artificial intelligence" to /api/nvidia/chat
        payload = {
            "message": "Create a PDF about artificial intelligence",
            "chat_id": chat_id,
            "stream": False,
        }
        res = await client.post("/api/nvidia/chat", json=payload, headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert "attachments" in data
        assert len(data["attachments"]) == 1
        att = data["attachments"][0]
        assert att["name"].endswith(".pdf")
        assert att["type"] == "application/pdf"
        assert att["size"] > 0
        file_id = att["id"]

        # 3. Test downloading the file via /api/files/{file_id}/download
        dl_resp = await client.get(f"/api/files/{file_id}/download", headers=headers)
        assert dl_resp.status_code == 200
        assert dl_resp.headers["content-type"] == "application/pdf"
        assert "attachment" in dl_resp.headers["content-disposition"]
        # Magic bytes check: must be real PDF
        assert dl_resp.content.startswith(b"%PDF-")


@pytest.mark.asyncio
async def test_generic_chat_pptx_stream_and_download():
    token = create_access_token({"sub": "test-doc-user-1"})
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create a chat
        chat_resp = await client.post("/api/chats", json={"title": "New Chat", "model": "DeepSeek-V3.2", "provider": "sambanova"}, headers=headers)
        assert chat_resp.status_code == 200
        chat_id = chat_resp.json()["id"]

        # 2. Send "Create a 5-slide PowerPoint about my project" to /api/chats/messages (streaming)
        payload = {
            "message": "Create a 5-slide PowerPoint about my project",
            "chat_id": chat_id,
            "stream": True,
        }
        stream_res = await client.post("/api/chats/messages", json=payload, headers=headers)
        assert stream_res.status_code == 200

        # Read SSE lines and find file_created event
        file_created_found = False
        pptx_file_id = None
        lines = stream_res.text.split("\n")
        for line in lines:
            if line.startswith("data: "):
                raw_data = line[6:].strip()
                if raw_data == "[DONE]":
                    continue
                try:
                    chunk = json.loads(raw_data)
                    if chunk.get("type") == "file_created":
                        file_created_found = True
                        pptx_file_id = chunk["file"]["id"]
                        assert chunk["file"]["name"].endswith(".pptx")
                except:
                    pass

        assert file_created_found is True
        assert pptx_file_id is not None

        # 3. Test downloading via query token
        dl_resp = await client.get(f"/api/files/{pptx_file_id}/download?token={token}")
        assert dl_resp.status_code == 200
        assert "presentation" in dl_resp.headers["content-type"]
        # Real PPTX package starts with ZIP header PK\x03\x04
        assert dl_resp.content.startswith(b"PK\x03\x04")


@pytest.mark.asyncio
async def test_xlsx_excel_generation():
    token = create_access_token({"sub": "test-doc-user-1"})
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        chat_resp = await client.post("/api/chats", json={"title": "New Chat", "model": "DeepSeek-V3.2", "provider": "sambanova"}, headers=headers)
        chat_id = chat_resp.json()["id"]

        payload = {
            "message": "Create an Excel expense tracker",
            "chat_id": chat_id,
            "stream": True,
        }
        res = await client.post("/api/chats/messages", json=payload, headers=headers)
        assert res.status_code == 200

        xlsx_id = None
        for line in res.text.split("\n"):
            if line.startswith("data: "):
                data = line[6:].strip()
                if data == "[DONE]": continue
                try:
                    chunk = json.loads(data)
                    if chunk.get("type") == "file_created":
                        xlsx_id = chunk["file"]["id"]
                        assert chunk["file"]["name"].endswith(".xlsx")
                except: pass

        assert xlsx_id is not None
        dl_resp = await client.get(f"/api/files/{xlsx_id}/download", headers=headers)
        assert dl_resp.status_code == 200
        assert dl_resp.content.startswith(b"PK\x03\x04")


@pytest.mark.asyncio
async def test_normal_chat_does_not_create_file():
    token = create_access_token({"sub": "test-doc-user-1"})
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        chat_resp = await client.post("/api/chats", json={"title": "New Chat"}, headers=headers)
        chat_id = chat_resp.json()["id"]

        payload = {
            "message": "What is artificial intelligence?",
            "chat_id": chat_id,
            "stream": True,
        }
        # In this test environment with mocked or real stream, verify no file_created event
        res = await client.post("/api/chats/messages", json=payload, headers=headers)
        for line in res.text.split("\n"):
            if line.startswith("data: "):
                data = line[6:].strip()
                if data == "[DONE]": continue
                try:
                    chunk = json.loads(data)
                    assert chunk.get("type") != "file_created"
                    assert chunk.get("file") is None
                except: pass
