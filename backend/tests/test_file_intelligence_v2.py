import os
import json
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import engine, Base, async_session, init_db
from app.models.user import User
from app.models.file import GeneratedFile
from app.models.chat import Chat
from app.models.message import Message
from app.utils.security import hash_password, create_access_token
from app.services.chat_context import (
    file_retrieval_engine,
    general_chat_file_context_engine,
    FileProcessingState,
)


@pytest.fixture(autouse=True)
async def setup_test_db():
    await init_db()
    async with async_session() as session:
        user = User(
            id="test-file-user-1",
            email="fileuser@hsbot.ai",
            username="fileuser",
            hashed_password=hash_password("password123"),
            is_active=True,
        )
        session.add(user)
        try:
            await session.commit()
        except Exception:
            await session.rollback()
    yield


@pytest.mark.asyncio
async def test_file_upload_with_chat_id_and_chunking():
    token = create_access_token({"sub": "test-file-user-1"})
    headers = {"Authorization": f"Bearer {token}"}

    sample_content = (
        "# System Architecture Specification\n\n"
        "## Overview\n"
        "The HSBot platform is built using a modern decoupled architecture.\n"
        "The frontend is Vite with React 19 and Tailwind CSS 4.\n\n"
        "## Core Engine\n"
        "The backend is powered by FastAPI and SQLAlchemy 2.0.\n"
        "Fast retrieval uses BM25 keyword matching and chunk citation tracking.\n"
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create a chat first
        chat_resp = await client.post(
            "/api/chats",
            json={"title": "Doc Chat", "model": "llama-3.2-11b", "provider": "nvidia"},
            headers=headers
        )
        assert chat_resp.status_code == 200
        chat_id = chat_resp.json()["id"]

        # Upload file with chat_id
        files = {
            "file": ("architecture.md", sample_content.encode("utf-8"), "text/markdown")
        }
        data = {
            "chat_id": chat_id,
        }
        res = await client.post("/api/files/upload", files=files, data=data, headers=headers)
        assert res.status_code == 200
        file_info = res.json()
        assert file_info["filename"] == "architecture.md"
        assert file_info["size"] == len(sample_content.encode("utf-8"))
        assert file_info["chunk_count"] >= 1
        assert file_info["status"] == "READY"
        file_id = file_info["id"]

        # Verify DB record
        async with async_session() as session:
            db_file = await session.get(GeneratedFile, file_id)
            assert db_file is not None
            assert db_file.conversation_id == chat_id
            assert db_file.content_hash is not None
            assert db_file.processing_stage == "READY"
            assert db_file.chunks_path is not None
            assert os.path.exists(db_file.chunks_path)
            assert os.path.exists(db_file.extracted_text_path)

            with open(db_file.chunks_path, "r", encoding="utf-8") as f:
                saved_data = json.load(f)
                chunks = saved_data.get("chunks", []) if isinstance(saved_data, dict) else saved_data
                assert len(chunks) >= 1
                assert any("Architecture" in c.get("content", "") or "Core Engine" in c.get("content", "") for c in chunks)


@pytest.mark.asyncio
async def test_file_upload_duplicate_hash_reuse():
    token = create_access_token({"sub": "test-file-user-1"})
    headers = {"Authorization": f"Bearer {token}"}

    sample_content = "def calculate_hash_test():\n    return 42 * 100\n"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # First upload
        files1 = {"file": ("calc.py", sample_content.encode("utf-8"), "text/x-python")}
        res1 = await client.post("/api/files/upload", files=files1, headers=headers)
        assert res1.status_code == 200
        data1 = res1.json()

        # Second upload with identical content
        files2 = {"file": ("calc.py", sample_content.encode("utf-8"), "text/x-python")}
        res2 = await client.post("/api/files/upload", files=files2, headers=headers)
        assert res2.status_code == 200
        data2 = res2.json()

        # Both should be READY and have the same chunk count
        assert data1["status"] == "READY"
        assert data2["status"] == "READY"
        assert data2["chunk_count"] == data1["chunk_count"]


@pytest.mark.asyncio
async def test_file_status_endpoint():
    token = create_access_token({"sub": "test-file-user-1"})
    headers = {"Authorization": f"Bearer {token}"}

    sample_text = "Key financial metrics: Revenue grew by 25% YoY to $50M."
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = {"file": ("report.txt", sample_text.encode("utf-8"), "text/plain")}
        res = await client.post("/api/files/upload", files=files, headers=headers)
        assert res.status_code == 200
        file_id = res.json()["id"]

        status_res = await client.get(f"/api/files/{file_id}/status", headers=headers)
        assert status_res.status_code == 200
        s_data = status_res.json()
        assert s_data["file_id"] == file_id
        assert s_data["status"] == "READY"
        assert s_data["processing_stage"] == "READY"
        assert "capabilities" in s_data
        assert s_data["capabilities"]["can_extract_text"] is True


@pytest.mark.asyncio
async def test_chat_files_endpoint():
    token = create_access_token({"sub": "test-file-user-1"})
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create chat
        chat_resp = await client.post(
            "/api/chats",
            json={"title": "Multi File Chat", "model": "llama-3.2-11b", "provider": "nvidia"},
            headers=headers
        )
        chat_id = chat_resp.json()["id"]

        # Upload file linked to chat
        files = {"file": ("notes.md", b"# Meeting Notes\nNext sync on Friday.", "text/markdown")}
        upload_res = await client.post(
            "/api/files/upload",
            files=files,
            data={"chat_id": chat_id},
            headers=headers
        )
        assert upload_res.status_code == 200

        # Retrieve chat files
        get_files_res = await client.get(f"/api/chats/{chat_id}/files", headers=headers)
        assert get_files_res.status_code == 200
        files_list = get_files_res.json()
        assert len(files_list) >= 1
        assert any(f["filename"] == "notes.md" for f in files_list)
        assert all(f["status"] == "READY" for f in files_list)


@pytest.mark.asyncio
async def test_file_retrieval_engine_persistence_and_citations():
    token = create_access_token({"sub": "test-file-user-1"})
    headers = {"Authorization": f"Bearer {token}"}

    sample_doc = (
        "# Product Specification\n\n"
        "## Authentication Requirements\n"
        "All requests must pass Clerk RS256 JWKS validation.\n"
        "Tokens must contain sub claim representing unique user ID.\n\n"
        "## Performance Metrics\n"
        "First token latency must be below 400ms.\n"
        "Context engine token budgeting must maintain a 15% safety headroom.\n"
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create chat
        chat_resp = await client.post(
            "/api/chats",
            json={"title": "Spec Analysis", "model": "llama-3.2-11b", "provider": "nvidia"},
            headers=headers
        )
        chat_id = chat_resp.json()["id"]

        # 2. Upload file linked to chat
        files = {"file": ("product_spec.md", sample_doc.encode("utf-8"), "text/markdown")}
        up_res = await client.post(
            "/api/files/upload",
            files=files,
            data={"chat_id": chat_id},
            headers=headers
        )
        file_id = up_res.json()["id"]

        # 3. Test resolve_active_files without explicit file_ids (simulating Turn 2 follow-up!)
        active_files = await file_retrieval_engine.resolve_active_files(
            user_id="test-file-user-1",
            chat_id=chat_id,
            file_ids=None,
            attachments=None,
            message="What are the authentication requirements?"
        )
        assert len(active_files) >= 1
        assert any(f["id"] == file_id for f in active_files)

        # 4. Test retrieve_relevant_context with BM25 keyword matching
        retrieval = await file_retrieval_engine.retrieve_relevant_context(
            user_id="test-file-user-1",
            chat_id=chat_id,
            query="authentication requirements Clerk RS256",
            active_files=active_files,
            token_budget=2000
        )
        assert "Clerk RS256" in retrieval["context_text"]
        assert len(retrieval["citations"]) >= 1
        assert any("product_spec.md" in c for c in retrieval["citations"])


@pytest.mark.asyncio
async def test_general_chat_file_context_engine_e2e():
    sample_code = (
        "# Database Repository\n\n"
        "class UserRepository:\n"
        "    def get_by_id(self, user_id: str):\n"
        "        return self.session.query(User).filter_by(id=user_id).first()\n"
    )

    # Test prepare_context
    final_messages, meta = await general_chat_file_context_engine.prepare_context(
        user_id="test-file-user-1",
        chat_id="temp-chat-99",
        attached_files=[{
            "id": "file_repo_1",
            "filename": "repo.py",
            "text": sample_code,
            "status": "READY",
        }],
        model_id="llama-3.2-11b",
        user_message="How does get_by_id filter the user?",
        conversation_history=[],
        system_prompt="You are a helpful assistant.",
    )

    assert len(final_messages) >= 2
    assert final_messages[0]["role"] == "system"
    user_msg_content = final_messages[-1]["content"]
    assert "How does get_by_id filter the user?" in user_msg_content
    assert "UserRepository" in user_msg_content
    assert "repo.py" in str(meta.get("citations", []))
