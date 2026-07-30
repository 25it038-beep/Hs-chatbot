import json
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.schemas.chat import ChatCreate, ChatResponse, ChatUpdate, ChatFolderCreate, ChatFolderResponse
from app.schemas.message import ChatRequest, MessageResponse
from app.services.chat import ChatService

router = APIRouter(prefix="/api/chats", tags=["chats"])


@router.post("", response_model=ChatResponse)
async def create_chat(data: ChatCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    try:
        svc = ChatService(db)
        chat = await svc.create_chat(current_user.id, data)
        return ChatResponse.model_validate(chat)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Create chat error: {type(e).__name__}: {str(e)}")


@router.get("", response_model=list[ChatResponse])
async def list_chats(folder_id: str | None = Query(None), current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    try:
        svc = ChatService(db)
        chats = await svc.get_chats(current_user.id, folder_id)
        return [ChatResponse.model_validate(c) for c in chats]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"List chats error: {type(e).__name__}: {str(e)}")


@router.get("/{chat_id}", response_model=ChatResponse)
async def get_chat(chat_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    svc = ChatService(db)
    chat = await svc.get_chat(chat_id, current_user.id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return ChatResponse.model_validate(chat)


@router.put("/{chat_id}", response_model=ChatResponse)
async def update_chat(chat_id: str, data: ChatUpdate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    svc = ChatService(db)
    chat = await svc.update_chat(chat_id, current_user.id, data)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return ChatResponse.model_validate(chat)


@router.delete("/{chat_id}")
async def delete_chat(chat_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    svc = ChatService(db)
    if not await svc.delete_chat(chat_id, current_user.id):
        raise HTTPException(status_code=404, detail="Chat not found")
    return {"message": "Chat deleted"}


@router.get("/{chat_id}/messages", response_model=list[MessageResponse])
async def get_messages(chat_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    svc = ChatService(db)
    messages = await svc.get_messages(chat_id, current_user.id)
    return [MessageResponse.model_validate(m) for m in messages]


@router.post("/messages")
async def send_message(request: ChatRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    svc = ChatService(db)

    async def generate():
        async for chunk in svc.send_message(current_user.id, request):
            yield f"data: {json.dumps(chunk.model_dump())}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    })


@router.post("/folders", response_model=ChatFolderResponse)
async def create_folder(data: ChatFolderCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    svc = ChatService(db)
    folder = await svc.create_folder(current_user.id, data.name, data.icon, data.color)
    return ChatFolderResponse.model_validate(folder)


@router.get("/folders", response_model=list[ChatFolderResponse])
async def list_folders(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    svc = ChatService(db)
    folders = await svc.get_folders(current_user.id)
    return [ChatFolderResponse.model_validate(f) for f in folders]


@router.delete("/folders/{folder_id}")
async def delete_folder(folder_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    svc = ChatService(db)
    if not await svc.delete_folder(folder_id, current_user.id):
        raise HTTPException(status_code=404, detail="Folder not found")
    return {"message": "Folder deleted"}
