import io
import json
import uuid
try:
    import pytest
except ImportError:
    class _DummyMark:
        def __getattr__(self, _):
            return lambda fn: fn
    class _DummyPytest:
        mark = _DummyMark()
        def fixture(self, *args, **kwargs):
            return lambda fn: fn
    pytest = _DummyPytest()  # type: ignore

from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.auth import create_access_token
from app.database import init_db, async_session
from app.models.user import User
from app.api.nvidia_api import resolve_message_attachments


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


async def _create_test_user(username_prefix: str = "fileuser") -> tuple[str, str]:
    await init_db()
    uid = str(uuid.uuid4())
    uname = f"{username_prefix}_{uid[:8]}"
    email = f"{uname}@example.com"
    async with async_session() as db:
        user = User(
            id=uid,
            username=uname,
            email=email,
            hashed_password="hashed_test_password",
            display_name=uname,
        )
        db.add(user)
        await db.commit()
    token = create_access_token(uid, uname)
    return uid, token


@pytest.mark.anyio
async def test_upload_text_and_clipboard_files_and_status():
    user_id, token = await _create_test_user("clipuser")
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Upload a code file as clipboard source
        code_bytes = b"def fibonacci(n):\n    return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)\n"
        files = {"file": ("fib.py", io.BytesIO(code_bytes), "text/x-python")}
        res = await client.post(
            "/api/files/upload?analyze=false&source=clipboard",
            files=files,
            headers=headers,
        )
        assert res.status_code == 201, res.text
        data = res.json()
        assert data["filename"] == "fib.py"
        assert data["category"] == "code"
        assert data["status"] == "ready"
        assert data["content_ready"] is True
        assert data["source"] == "clipboard"
        assert "def fibonacci" in data["text_preview"]
        file_id = data["id"]

        # 2. Check status endpoint
        status_res = await client.get(f"/api/files/{file_id}/status", headers=headers)
        assert status_res.status_code == 200
        status_data = status_res.json()
        assert status_data["id"] == file_id
        assert status_data["status"] == "ready"
        assert status_data["content_ready"] is True

        # 3. Download content endpoint
        dl_res = await client.get(f"/api/files/{file_id}/content", headers=headers)
        assert dl_res.status_code == 200
        assert dl_res.content == code_bytes


@pytest.mark.anyio
async def test_upload_pasted_png_image_and_resolve_attachments():
    user_id, token = await _create_test_user("imguser")
    headers = {"Authorization": f"Bearer {token}"}

    # Generate a tiny valid 2x2 PNG in memory
    from PIL import Image
    buf = io.BytesIO()
    img = Image.new("RGB", (4, 4), color=(25, 120, 220))
    img.save(buf, format="PNG")
    png_bytes = buf.getvalue()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = {"file": ("pasted-image-1.png", io.BytesIO(png_bytes), "image/png")}
        res = await client.post(
            "/api/files/upload?analyze=false&source=clipboard",
            files=files,
            headers=headers,
        )
        assert res.status_code == 201, res.text
        info = res.json()
        assert info["category"] == "image"
        assert info["status"] == "ready"
        assert info["content_ready"] is True
        file_id = info["id"]

        # Upload a CSV file as well for multi-file test
        csv_bytes = b"quarter,revenue,growth\nQ1,125000,12%\nQ2,148000,18%\n"
        res_csv = await client.post(
            "/api/files/upload?analyze=false&source=drag_drop",
            files={"file": ("metrics.csv", io.BytesIO(csv_bytes), "text/csv")},
            headers=headers,
        )
        assert res_csv.status_code == 201
        csv_info = res_csv.json()
        csv_id = csv_info["id"]

        # Verify resolve_message_attachments binds BOTH image base64 + CSV text for the user
        async with async_session() as db:
            context_text, img_b64, persisted = await resolve_message_attachments(
                db=db,
                user_id=user_id,
                message="Compare the screenshot and the CSV metrics",
                file_ids=[file_id, csv_id],
                client_attachments=[
                    {"id": file_id, "fileId": file_id, "name": "pasted-image-1.png", "source": "clipboard"},
                    {"id": csv_id, "fileId": csv_id, "name": "metrics.csv", "source": "drag_drop"},
                ],
            )
            assert img_b64 is not None and len(img_b64) > 20
            assert "metrics.csv" in context_text
            assert "148000" in context_text
            assert len(persisted) == 2
            assert persisted[0]["source"] == "clipboard"
            assert persisted[1]["source"] == "drag_drop"


@pytest.mark.anyio
async def test_multi_tenant_file_isolation_and_delete():
    user_a_id, token_a = await _create_test_user("tenanta")
    user_b_id, token_b = await _create_test_user("tenantb")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/files/upload?analyze=false",
            files={"file": ("secret_notes.txt", io.BytesIO(b"Top secret alpha project"), "text/plain")},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert res.status_code == 201
        file_id = res.json()["id"]

        # User B cannot view status, download content, or delete User A's file
        status_b = await client.get(
            f"/api/files/{file_id}/status",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert status_b.status_code == 404

        dl_b = await client.get(
            f"/api/files/{file_id}/content",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert dl_b.status_code == 404

        del_b = await client.delete(
            f"/api/files/{file_id}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert del_b.status_code == 404

        # User B cannot resolve User A's file_id in chat attachment resolver
        async with async_session() as db:
            ctx_b, img_b, persisted_b = await resolve_message_attachments(
                db=db,
                user_id=user_b_id,
                message="Tell me what is in the file",
                file_ids=[file_id],
            )
            assert ctx_b == ""
            assert img_b is None
            assert persisted_b == []

        # User A can delete their own file
        del_a = await client.delete(
            f"/api/files/{file_id}",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert del_a.status_code == 204


@pytest.mark.anyio
async def test_empty_and_unsupported_file_rejection():
    _, token = await _create_test_user("valuser")
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Empty file -> 400
        empty_res = await client.post(
            "/api/files/upload",
            files={"file": ("empty.txt", io.BytesIO(b""), "text/plain")},
            headers=headers,
        )
        assert empty_res.status_code == 400
        assert "empty" in empty_res.json()["detail"].lower()

        # Unsupported binary executable -> 400
        exe_res = await client.post(
            "/api/files/upload",
            files={"file": ("malware.exe", io.BytesIO(b"MZ\x90\x00\x03"), "application/x-msdownload")},
            headers=headers,
        )
        assert exe_res.status_code == 400
        assert "unsupported" in exe_res.json()["detail"].lower()


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_upload_text_and_clipboard_files_and_status())
    asyncio.run(test_upload_pasted_png_image_and_resolve_attachments())
    asyncio.run(test_multi_tenant_file_isolation_and_delete())
    asyncio.run(test_empty_and_unsupported_file_rejection())
    print("ALL 4 BACKEND ATTACHMENT PIPELINE TESTS PASSED")

