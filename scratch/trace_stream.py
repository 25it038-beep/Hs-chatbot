"""
End-to-end stream tracer: runs send_message locally and catches ALL exceptions
including those swallowed by the async generator protocol.
"""
import asyncio
import sys
import traceback

async def test_stream():
    from app.database import init_db, async_session
    await init_db()
    
    async with async_session() as db:
        from app.services.chat import ChatService
        from app.schemas.message import ChatRequest
        
        svc = ChatService(db)
        req = ChatRequest(
            chat_id=None,
            message="Hello, what can you do?",
            provider="sambanova",
            model="DeepSeek-V3-0324",
            stream=True
        )
        
        print("[TRACE] Calling send_message with provider=sambanova, model=DeepSeek-V3-0324")
        chunk_count = 0
        try:
            async for chunk in svc.send_message("default_user_id", req):
                chunk_count += 1
                snippet = (chunk.content or "")[:80]
                print("[CHUNK #" + str(chunk_count) + "] type=" + repr(chunk.type) + " content=" + repr(snippet) + " done=" + str(chunk.done))
                if chunk.done or chunk_count > 20:
                    print("[TRACE] Stream complete after " + str(chunk_count) + " chunks")
                    break
        except Exception as e:
            print("[FATAL] Generator raised exception: " + type(e).__name__ + ": " + str(e))
            traceback.print_exc()
        
        if chunk_count == 0:
            print("[FATAL] Stream produced ZERO chunks - generator exited silently")
        else:
            print("[OK] Stream produced " + str(chunk_count) + " chunks")

if __name__ == "__main__":
    asyncio.run(test_stream())
