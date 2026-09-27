import io
import uuid
import tempfile
import pytest
from pathlib import Path
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.utils.security import create_access_token
from app.services.workspace.workspace import get_workspace, WorkspaceSecurityError
from app.services.artifacts.registry import artifact_registry
from app.services.artifacts.models import ArtifactMetadata, ArtifactCategory
from app.config import settings

@pytest.mark.asyncio
async def test_unauthenticated_requests_rejected():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Chats listing
        resp = await client.get("/api/chats")
        assert resp.status_code == 401
        assert "Authentication required" in resp.json().get("detail", "")

        # Agent state
        resp = await client.get("/api/agent/state")
        assert resp.status_code == 401

        # File upload
        files = {"file": ("test.txt", io.BytesIO(b"content"), "text/plain")}
        resp = await client.post("/api/files/upload", files=files)
        assert resp.status_code == 401

@pytest.mark.asyncio
async def test_guest_tokens_rejected():
    transport = ASGITransport(app=app)
    for dummy_token in ["hsbot_guest_token", "hsbot_default_access_token", "guest", "null"]:
        headers = {"Authorization": f"Bearer {dummy_token}"}
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/chats", headers=headers)
            assert resp.status_code == 401
            assert "Invalid" in resp.json().get("detail", "") or "unauthorized" in resp.json().get("detail", "")

@pytest.mark.asyncio
async def test_user_chat_and_folder_isolation():
    transport = ASGITransport(app=app)
    user_a_token = create_access_token({"sub": f"user_a_{uuid.uuid4().hex[:6]}"})
    user_b_token = create_access_token({"sub": f"user_b_{uuid.uuid4().hex[:6]}"})
    headers_a = {"Authorization": f"Bearer {user_a_token}"}
    headers_b = {"Authorization": f"Bearer {user_b_token}"}

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # User A creates a chat
        create_resp = await client.post(
            "/api/chats",
            json={"title": "User A Private Chat", "model": "llama-3.2-11b"},
            headers=headers_a
        )
        assert create_resp.status_code == 200
        chat_a_id = create_resp.json()["id"]

        # User A creates a folder
        f_resp = await client.post(
            "/api/chats/folders",
            json={"name": "User A Folder"},
            headers=headers_a
        )
        assert f_resp.status_code == 200
        folder_a_id = f_resp.json()["id"]

        # User B lists chats -> chat_a_id must NOT be visible
        list_b = await client.get("/api/chats", headers=headers_b)
        assert list_b.status_code == 200
        b_chat_ids = [c["id"] for c in list_b.json()]
        assert chat_a_id not in b_chat_ids

        # User B lists folders -> folder_a_id must NOT be visible
        folders_b = await client.get("/api/chats/folders", headers=headers_b)
        assert folders_b.status_code == 200
        b_folder_ids = [f["id"] for f in folders_b.json()]
        assert folder_a_id not in b_folder_ids

        # User B attempts to access User A\'s chat directly (IDOR check)
        get_b_attempt = await client.get(f"/api/chats/{chat_a_id}", headers=headers_b)
        assert get_b_attempt.status_code == 404

        # User B attempts to update User A\'s chat
        update_b_attempt = await client.put(f"/api/chats/{chat_a_id}", json={"title": "Hacked Title"}, headers=headers_b)
        assert update_b_attempt.status_code == 404

        # User B attempts to delete User A\'s chat
        del_b_attempt = await client.delete(f"/api/chats/{chat_a_id}", headers=headers_b)
        assert del_b_attempt.status_code == 404

        # User B attempts to delete User A\'s folder
        del_f_attempt = await client.delete(f"/api/chats/folders/{folder_a_id}", headers=headers_b)
        assert del_f_attempt.status_code == 404

@pytest.mark.asyncio
async def test_user_file_upload_and_download_isolation():
    transport = ASGITransport(app=app)
    user_a_id = f"user_a_{uuid.uuid4().hex[:6]}"
    user_b_id = f"user_b_{uuid.uuid4().hex[:6]}"
    token_a = create_access_token({"sub": user_a_id})
    token_b = create_access_token({"sub": user_b_id})
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # User A uploads a private file
        file_content = b"Confidential Company Financial Data 2026"
        files = {"file": ("financials.txt", io.BytesIO(file_content), "text/plain")}
        upload_res = await client.post("/api/files/upload", files=files, data={"analyze": "false"}, headers=headers_a)
        assert upload_res.status_code == 200
        file_id = upload_res.json()["id"]

        # Verify file is stored in user_a\'s isolated directory
        expected_path = Path(settings.upload_dir) / "users" / user_a_id / "uploads"
        assert expected_path.exists()
        matching_files = list(expected_path.glob(f"{file_id}*"))
        assert len(matching_files) == 1

        # User A can download the file
        dl_a = await client.get(f"/api/files/{file_id}/download", headers=headers_a)
        assert dl_a.status_code == 200
        assert dl_a.content == file_content

        # User B cannot download User A\'s file (IDOR prevented)
        dl_b = await client.get(f"/api/files/{file_id}/download", headers=headers_b)
        assert dl_b.status_code == 404

        # User B cannot preview User A\'s file
        prev_b = await client.get(f"/api/files/{file_id}/preview", headers=headers_b)
        assert prev_b.status_code == 404

        # Anonymous cannot download User A\'s file
        dl_anon = await client.get(f"/api/files/{file_id}/download")
        assert dl_anon.status_code == 401

@pytest.mark.asyncio
async def test_workspace_isolation_between_users():
    user_a_id = f"user_a_{uuid.uuid4().hex[:6]}"
    user_b_id = f"user_b_{uuid.uuid4().hex[:6]}"

    ws_a = get_workspace(workspace_id="project-alpha", user_id=user_a_id)
    ws_b = get_workspace(workspace_id="project-alpha", user_id=user_b_id)

    # Roots must be completely distinct
    assert str(ws_a.root) != str(ws_b.root)
    assert user_a_id in str(ws_a.root)
    assert user_b_id in str(ws_b.root)

    # User A writes a file
    ws_a.write_file("secrets.py", "API_SECRET = 'abc123secret'")

    # User B should NOT have secrets.py in their workspace
    b_read = ws_b.read_file("secrets.py")
    assert b_read["success"] is False
    assert "not found" in b_read["error"].lower()

@pytest.mark.asyncio
async def test_artifact_isolation_between_users():
    transport = ASGITransport(app=app)
    user_a_id = f"user_a_{uuid.uuid4().hex[:6]}"
    user_b_id = f"user_b_{uuid.uuid4().hex[:6]}"
    token_a = create_access_token({"sub": user_a_id})
    token_b = create_access_token({"sub": user_b_id})
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Register an artifact owned by user A
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tf:
        tf.write(b"User A artifact content")
        tf_path = tf.name

    art_meta = artifact_registry.register_artifact(
        name="PrivateDoc",
        filename="privatedoc.txt",
        file_path=tf_path,
        user_id=user_a_id,
        category=ArtifactCategory.DOCUMENT
    )

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # User A lists artifacts -> sees the artifact
        list_a = await client.get("/api/agent/artifacts", headers=headers_a)
        assert list_a.status_code == 200
        a_ids = [a["artifact_id"] for a in list_a.json()["artifacts"]]
        assert art_meta.artifact_id in a_ids

        # User B lists artifacts -> does NOT see User A\'s artifact
        list_b = await client.get("/api/agent/artifacts", headers=headers_b)
        assert list_b.status_code == 200
        b_ids = [a["artifact_id"] for a in list_b.json()["artifacts"]]
        assert art_meta.artifact_id not in b_ids

        # User B attempts to download User A\'s artifact -> 404
        dl_b = await client.get(f"/api/agent/artifacts/{art_meta.artifact_id}/download", headers=headers_b)
        assert dl_b.status_code == 404

        # User B attempts to preview User A\'s artifact -> 404
        prev_b = await client.get(f"/api/agent/artifacts/{art_meta.artifact_id}/preview", headers=headers_b)
        assert prev_b.status_code == 404

        # User B attempts to edit User A\'s artifact -> 404
        edit_b = await client.post(
            f"/api/agent/artifacts/{art_meta.artifact_id}/edit",
            json={"instruction": "tamper"},
            headers=headers_b
        )
        assert edit_b.status_code == 404

@pytest.mark.asyncio
async def test_path_traversal_blocked_in_workspace():
    user_id = f"user_{uuid.uuid4().hex[:6]}"
    ws = get_workspace(workspace_id="test", user_id=user_id)

    with pytest.raises(WorkspaceSecurityError):
        ws.read_file("../../outside.txt")

    with pytest.raises(WorkspaceSecurityError):
        ws.write_file("../../../evil.py", "malicious_code")
