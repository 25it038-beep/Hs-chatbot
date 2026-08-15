import asyncio
import sys
from app.database import init_db, get_db
from app.services.chat import ChatService
from app.schemas.message import ChatRequest

async def test_direct():
    await init_db()
    # we need a db session
    from app.database import async_session
    async with async_session() as db:
        svc = ChatService(db)
        
        req = ChatRequest(
            chat_id="70ba9109-3786-4e39-b598-1e050dc2c417", # or any valid chat id
            message="Open youtube",
            provider="sambanova",
            model="DeepSeek-V3.2",
            stream=True
        )
        
        print("Running send_message directly...")
        try:
            async for chunk in svc.send_message("default_user_id", req):
                print(f"Chunk: {chunk.model_dump()}")
        except Exception as e:
            import traceback
            print(f"CRASHED: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_direct())
