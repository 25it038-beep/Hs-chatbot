import json
import time
import asyncio
import httpx
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.middleware.auth import get_current_user, get_optional_user
from app.models.user import User
from app.models.message import Message
from app.services.chat import ChatService
from app.services.rag import RAGService
from app.services.nvidia import (
    NvidiaChatProvider, NvidiaVisionProvider, NvidiaImageProvider,
    NvidiaEmbeddingsProvider, NvidiaSpeechProvider, ai_router,
)
from app.services.nvidia.key_manager import key_manager
from app.services.nvidia.config import NVIDIA_MODELS, NVIDIA_BASE_URL

router = APIRouter(prefix="/api/nvidia", tags=["nvidia"])

chat_provider = NvidiaChatProvider()
vision_provider = NvidiaVisionProvider()
image_provider = NvidiaImageProvider()
embed_provider = NvidiaEmbeddingsProvider()
speech_provider = NvidiaSpeechProvider()


class ChatRequest(BaseModel):
    message: str
    model: Optional[str] = None
    system_prompt: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 0.95
    stream: bool = True
    json_mode: bool = False
    reasoning: bool = False
    auto_route: bool = True
    chat_id: Optional[str] = None
    files: Optional[list[str]] = None


class EmbedRequest(BaseModel):
    texts: list[str]
    model: str = "nv-embed-v1"
    input_type: str = "query"


@router.post("/chat")
async def nvidia_chat(
    request: ChatRequest,
    user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    if request.auto_route:
        task, auto_model = ai_router.get_model_for_message(request.message)
        if task == "image_generation":
            model = auto_model or "flux-1-dev"
        else:
            model = auto_model
    else:
        model = request.model or "deepseek-v4-flash"
        task = "chat"

    system_prompt = request.system_prompt or "You are a helpful AI assistant. You ONLY respond in English. No matter what language the user writes in, you ALWAYS answer in English. Never use any other language in your responses."

    # ── Image generation path ──
    if task == "image_generation":
        enhanced = f"professional high quality photograph, well-lit, bright, vivid colors, detailed, realistic: {request.message}"
        if request.stream:
            async def generate_image():
                yield f"data: {json.dumps({'type': 'meta', 'model': model, 'task': task, 'chat_id': request.chat_id or ''})}\n\n"
                yield f"data: {json.dumps({'type': 'generating', 'content': 'Generating image...'})}\n\n"
                try:
                    img_resp = await image_provider.generate(prompt=enhanced, model=model)
                    yield f"data: {json.dumps({'type': 'image', 'content': img_resp.image_b64, 'seed': img_resp.seed})}\n\n"
                    yield f"data: {json.dumps({'type': 'content', 'content': ''})}\n\n"
                except Exception as e:
                    yield f"data: {json.dumps({'type': 'error', 'content': f'Image generation failed: {str(e)}'})}\n\n"
                    yield f"data: {json.dumps({'type': 'content', 'content': f'I could not generate the image. {str(e)}'})}\n\n"
                yield "data: [DONE]\n\n"
            return StreamingResponse(generate_image(), media_type="text/event-stream", headers={
                "Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no",
            })
        else:
            try:
                img_resp = await image_provider.generate(prompt=enhanced, model=model)
                return {
                    "content": f'<img src="data:image/png;base64,{img_resp.image_b64}" alt="Generated image" style="max-width:100%;border-radius:8px;" />',
                    "image": img_resp.image_b64,
                    "model": model,
                    "provider": "nvidia",
                    "seed": img_resp.seed,
                }
            except Exception as e:
                return {"content": f"Image generation failed: {str(e)}", "model": model, "provider": "nvidia"}

    # ── Conversation memory path (authenticated + chat_id) ──
    if user and request.chat_id:
        svc = ChatService(db)
        chat = await svc.get_chat(request.chat_id, user.id)
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")

        system_prompt = request.system_prompt or chat.system_prompt or "You are a helpful AI assistant. You ONLY respond in English. No matter what language the user writes in, you ALWAYS answer in English. Never use any other language in your responses."

        if user:
            rag = RAGService(db, user.id)
            rag_context = await rag.search_similar(request.message)
            if rag_context:
                system_prompt = f"{system_prompt}\n\nRelevant context from uploaded files:\n{rag_context}"
            else:
                import re as _re
                file_match = _re.search(r'\[(?:File|Image):\s*(.+?)\]', request.message)
                cached = None
                if file_match:
                    cached = RAGService.get_cached_file_content(user.id, file_match.group(1))
                if cached:
                    system_prompt = f"{system_prompt}\n\nThe user uploaded a file. Here is its content:\n\n{cached}"
                else:
                    all_texts = RAGService.get_all_cached_texts(user.id)
                    if all_texts:
                        system_prompt = f"{system_prompt}\n\nThe user has uploaded the following files. Use their content to answer the user's question:\n{all_texts}"

        result = await db.execute(
            select(Message).where(Message.chat_id == request.chat_id).order_by(Message.created_at)
        )
        all_messages = result.scalars().all()

        api_messages = svc._prepare_messages(
            all_messages,
            provider="nvidia",
            max_output_tokens=request.max_tokens or chat.max_tokens or 4096,
            system_prompt=system_prompt,
        )
        api_messages.append({"role": "user", "content": request.message})

        if request.stream:
            async def generate_with_memory():
                yield f"data: {json.dumps({'type': 'meta', 'model': model, 'task': task, 'chat_id': request.chat_id})}\n\n"
                full_content = ""
                input_tokens = 0
                output_tokens = 0
                start = time.time()

                try:
                    async for chunk in chat_provider.generate_stream(
                        messages=api_messages,
                        model=model,
                        system_prompt=system_prompt,
                        temperature=request.temperature,
                        max_tokens=request.max_tokens,
                        top_p=request.top_p,
                        json_mode=request.json_mode,
                        reasoning=request.reasoning,
                    ):
                        if chunk.type == "content":
                            full_content += chunk.content
                        elif chunk.type == "done":
                            input_tokens = chunk.input_tokens
                            output_tokens = chunk.output_tokens
                        yield f"data: {json.dumps(chunk.model_dump())}\n\n"

                    if full_content:
                        latency = (time.time() - start) * 1000
                        user_msg = Message(chat_id=request.chat_id, role="user", content=request.message)
                        assistant_msg = Message(
                            chat_id=request.chat_id,
                            role="assistant",
                            content=full_content,
                            model=model,
                            provider="nvidia",
                            input_tokens=input_tokens,
                            output_tokens=output_tokens,
                            latency_ms=latency,
                        )
                        db.add(user_msg)
                        db.add(assistant_msg)
                        if chat.title == "New Chat":
                            chat.title = request.message[:50] + ("..." if len(request.message) > 50 else "")
                        await db.commit()
                except (asyncio.CancelledError, GeneratorExit, Exception):
                    await db.rollback()
                    raise

                yield "data: [DONE]\n\n"

            return StreamingResponse(generate_with_memory(), media_type="text/event-stream", headers={
                "Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no",
            })
        else:
            start = time.time()
            response = await chat_provider.generate(
                messages=api_messages,
                model=model,
                system_prompt=system_prompt,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                top_p=request.top_p,
                json_mode=request.json_mode,
                reasoning=request.reasoning,
            )
            user_msg = Message(chat_id=request.chat_id, role="user", content=request.message)
            assistant_msg = Message(
                chat_id=request.chat_id,
                role="assistant",
                content=response.content,
                model=model,
                provider="nvidia",
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                latency_ms=response.latency_ms,
            )
            db.add(user_msg)
            db.add(assistant_msg)
            if chat.title == "New Chat":
                chat.title = request.message[:50] + ("..." if len(request.message) > 50 else "")
            await db.commit()
            return response

    # ── Stateless path (anonymous or no chat_id) ──
    messages = [{"role": "user", "content": request.message}]

    if request.stream:
        async def generate():
            yield f"data: {json.dumps({'type': 'meta', 'model': model, 'task': task})}\n\n"
            async for chunk in chat_provider.generate_stream(
                messages=messages,
                model=model,
                system_prompt=system_prompt,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                top_p=request.top_p,
                json_mode=request.json_mode,
                reasoning=request.reasoning,
            ):
                yield f"data: {json.dumps(chunk.model_dump())}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(generate(), media_type="text/event-stream", headers={
            "Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no",
        })
    else:
        response = await chat_provider.generate(
            messages=messages,
            model=model,
            system_prompt=system_prompt,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            top_p=request.top_p,
            json_mode=request.json_mode,
            reasoning=request.reasoning,
        )
        return response


@router.post("/vision")
async def nvidia_vision(
    file: UploadFile = File(...),
    prompt: str = Form("Describe this image in detail."),
    model: str = Form("nemotron-vl"),
):
    content = await file.read()
    mime_type = file.content_type or "image/png"
    model_id = NVIDIA_MODELS.get(model, {}).get("id", model)
    response = await vision_provider.analyze(
        image_data=content, prompt=prompt, mime_type=mime_type, model=model_id,
    )
    return response


@router.post("/image/generate")
async def nvidia_image_generate(
    prompt: str = Form(...),
    model: str = Form("flux-1-dev"),
    steps: int = Form(20),
    seed: int = Form(0),
):
    try:
        response = await image_provider.generate(
            prompt=prompt, model=model, steps=steps, seed=seed,
        )
        return response
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Image generation timed out")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")


@router.post("/image/edit")
async def nvidia_image_edit(
    file: UploadFile = File(...),
    prompt: str = Form(...),
):
    content = await file.read()
    response = await image_provider.edit(prompt=prompt, image_data=content)
    return response


@router.post("/embeddings")
async def nvidia_embeddings(request: EmbedRequest):
    model_id = NVIDIA_MODELS.get(request.model, {}).get("id", request.model)
    embeddings = await embed_provider.create(
        texts=request.texts, model=model_id, input_type=request.input_type,
    )
    dims = len(embeddings[0]) if embeddings else 0
    return {"embeddings": embeddings, "model": request.model, "dimensions": dims}


@router.post("/speech/transcribe")
async def nvidia_transcribe(
    file: UploadFile = File(...),
    language: str = Form("en"),
):
    content = await file.read()
    try:
        text = await speech_provider.transcribe(audio_data=content, language=language)
        return {"text": text}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/usage")
async def nvidia_usage():
    return key_manager.get_usage_stats()


@router.get("/route")
async def nvidia_route(message: str = Query(...), preferred_model: Optional[str] = Query(None)):
    task, model = ai_router.get_model_for_message(message, preferred_model)
    return {"task": task, "model": model, "available_fallbacks": ai_router.get_fallback_models(task)}
