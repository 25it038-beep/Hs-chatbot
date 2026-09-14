import os
import uuid
from app.config import settings

def get_chat_workspace_dir(user_id: str, chat_id: str) -> str:
    base = os.path.join(settings.upload_dir, "workspaces", user_id, chat_id)
    os.makedirs(base, exist_ok=True)
    return base

def save_file(user_id: str, chat_id: str, filename: str, content_bytes: bytes) -> str:
    workspace = get_chat_workspace_dir(user_id, chat_id)
    file_id = str(uuid.uuid4())
    ext = os.path.splitext(filename)[1]
    safe_name = f"{file_id}{ext}"
    path = os.path.join(workspace, safe_name)
    with open(path, 'wb') as f:
        f.write(content_bytes)
    return path
