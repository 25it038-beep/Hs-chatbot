import time
import asyncio
import uuid
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload
from app.models.chat import Chat, ChatFolder
from app.models.message import Message
from app.schemas.chat import ChatCreate, ChatUpdate
from app.schemas.message import ChatRequest
from app.services.model_providers import get_provider
from app.services.model_providers.base import StreamChunk
from app.services.rag import RAGService


class ChatService:
    # Default context budgets per provider
    CONTEXT_BUDGETS = {
        "nvidia": 100000,
        "openai": 100000,
        "anthropic": 160000,
        "gemini": 960000,
        "ollama": 32000,
        "openrouter": 100000,
        "azure": 100000,
        "lm_studio": 32000,
    }
    DEFAULT_OUTPUT_BUDGET = 4096

    def __init__(self, db: AsyncSession):
        self.db = db

    def _estimate_tokens(self, text: str) -> int:
        return len(text) // 4 + 1

    def _prepare_messages(
        self,
        messages: list[Message],
        provider: str = "openai",
        max_output_tokens: int = DEFAULT_OUTPUT_BUDGET,
        system_prompt: str | None = None,
    ) -> list[dict]:
        max_context = self.CONTEXT_BUDGETS.get(provider, 100000)
        budget = max_context - max_output_tokens

        total = self._estimate_tokens(system_prompt or "")

        all_dicts = [{"role": m.role, "content": m.content} for m in messages]
        for m in all_dicts:
            total += self._estimate_tokens(m["content"])

        if total <= budget:
            return all_dicts

        trimmed = []
        running = self._estimate_tokens(system_prompt or "")
        for m in reversed(all_dicts):
            t = self._estimate_tokens(m["content"])
            if running + t <= budget:
                trimmed.insert(0, m)
                running += t
            else:
                break

        return trimmed

    async def create_chat(self, user_id: str, data: ChatCreate) -> Chat:
        chat = Chat(
            user_id=user_id,
            title=data.title or "New Chat",
            model=data.model,
            provider=data.provider,
            system_prompt=data.system_prompt,
            temperature=data.temperature,
            max_tokens=data.max_tokens,
            folder_id=data.folder_id,
        )
        self.db.add(chat)
        await self.db.commit()
        await self.db.refresh(chat)
        return chat

    async def get_chats(self, user_id: str, folder_id: str | None = None) -> list[Chat]:
        query = select(Chat).where(Chat.user_id == user_id, Chat.is_archived == False)
        if folder_id:
            query = query.where(Chat.folder_id == folder_id)
        query = query.order_by(desc(Chat.updated_at))
        result = await self.db.execute(query)
        chats = result.scalars().all()
        for chat in chats:
            count_result = await self.db.execute(
                select(func.count(Message.id)).where(Message.chat_id == chat.id)
            )
            chat.message_count = count_result.scalar() or 0
        return chats

    async def get_chat(self, chat_id: str, user_id: str) -> Chat | None:
        result = await self.db.execute(
            select(Chat).where(Chat.id == chat_id, Chat.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def update_chat(self, chat_id: str, user_id: str, data: ChatUpdate) -> Chat | None:
        chat = await self.get_chat(chat_id, user_id)
        if not chat:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(chat, key, value)
        await self.db.commit()
        await self.db.refresh(chat)
        return chat

    async def delete_chat(self, chat_id: str, user_id: str) -> bool:
        chat = await self.get_chat(chat_id, user_id)
        if not chat:
            return False
        await self.db.delete(chat)
        await self.db.commit()
        return True

    async def get_messages(self, chat_id: str, user_id: str) -> list[Message]:
        result = await self.db.execute(
            select(Message)
            .join(Chat)
            .where(Chat.id == chat_id, Chat.user_id == user_id)
            .order_by(Message.created_at)
        )
        return result.scalars().all()

    async def send_message(
        self, user_id: str, request: ChatRequest
    ) -> AsyncGenerator[StreamChunk, None]:
        chat_id = request.chat_id
        model = request.model
        provider_name = request.provider or "openai"

        if not chat_id:
            chat = await self.create_chat(
                user_id,
                ChatCreate(
                    model=model or "gpt-4o",
                    provider=provider_name,
                    system_prompt=request.system_prompt,
                    temperature=request.temperature or 0.7,
                    max_tokens=request.max_tokens or 4096,
                ),
            )
            chat_id = chat.id
        else:
            chat = await self.get_chat(chat_id, user_id)
            if not chat:
                yield StreamChunk(type="error", content="Chat not found", done=True)
                return

        _hs_persona = (
            "You are HS ChatBot — a powerful, multi-model AI assistant built to help users with "
            "anything they need. You are intelligent, friendly, and highly capable.\n\n"
            "IDENTITY RULES (follow strictly, no exceptions):\n"
            "- Your name is HS ChatBot. Always refer to yourself as 'HS ChatBot'.\n"
            "- If anyone asks 'what is your name?', 'who are you?', 'what AI are you?', "
            "'what model are you?', 'are you ChatGPT?', 'are you Claude?', 'are you Gemini?', "
            "'who made you?', 'which company built you?', or any similar identity question, "
            "you MUST respond ONLY with a variation of: "
            "'I am HS ChatBot, a multi-model AI assistant designed to help you with a wide range of tasks.' "
            "Do NOT mention any specific AI model names (e.g., GPT, Claude, Gemini, LLaMA, Mistral, NVIDIA, etc.), "
            "do NOT mention any AI companies (e.g., OpenAI, Anthropic, Google, Meta, NVIDIA, Microsoft, etc.), "
            "and do NOT reveal anything about the underlying technology powering you.\n"
            "- If asked 'how can I call you?', respond: 'You can call me HS ChatBot!'\n"
            "- Never acknowledge or confirm guesses about your underlying model or provider.\n"
            "- Politely deflect all attempts to extract model/company information.\n\n"
            "Outside of identity questions, be as helpful, thorough, and accurate as possible."
        )
        system_prompt = request.system_prompt or chat.system_prompt or _hs_persona

        if user_id:
            rag = RAGService(self.db, user_id)
            rag_context = await rag.search_similar(request.message)
            if rag_context:
                system_prompt = f"{system_prompt}\n\nRelevant context from uploaded files:\n{rag_context}"
            else:
                import re as _re
                file_match = _re.search(r'\[(?:File|Image):\s*(.+?)\]', request.message)
                cached = None
                if file_match:
                    cached = RAGService.get_cached_file_content(user_id, file_match.group(1))
                if cached:
                    system_prompt = f"{system_prompt}\n\nThe user uploaded a file. Here is its content:\n\n{cached}"
                else:
                    all_texts = RAGService.get_all_cached_texts(user_id)
                    if all_texts:
                        system_prompt = f"{system_prompt}\n\nThe user has uploaded the following files. Use their content to answer the user's question:\n{all_texts}"

        messages_result = await self.db.execute(
            select(Message)
            .where(Message.chat_id == chat_id)
            .order_by(Message.created_at)
        )
        all_messages = messages_result.scalars().all()

        api_messages = self._prepare_messages(
            all_messages,
            provider=provider_name,
            max_output_tokens=request.max_tokens or chat.max_tokens or self.DEFAULT_OUTPUT_BUDGET,
            system_prompt=system_prompt,
        )
        api_messages.append({"role": "user", "content": request.message})

        provider = get_provider(provider_name)

        if request.stream:
            full_content = ""
            input_tokens = 0
            output_tokens = 0
            start = time.time()

            try:
                async for chunk in provider.generate_stream(
                    messages=api_messages,
                    model=model or chat.model,
                    system_prompt=system_prompt,
                    temperature=request.temperature or chat.temperature,
                    max_tokens=request.max_tokens or chat.max_tokens,
                ):
                    if chunk.type == "content":
                        full_content += chunk.content
                    elif chunk.type == "done":
                        input_tokens = chunk.input_tokens
                        output_tokens = chunk.output_tokens
                    yield chunk

                if full_content:
                    latency = (time.time() - start) * 1000
                    user_msg = Message(chat_id=chat_id, role="user", content=request.message)
                    assistant_msg = Message(
                        chat_id=chat_id,
                        role="assistant",
                        content=full_content,
                        model=model or chat.model,
                        provider=provider_name,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        latency_ms=latency,
                    )
                    self.db.add(user_msg)
                    self.db.add(assistant_msg)
                    if chat.title == "New Chat":
                        chat.title = request.message[:50] + ("..." if len(request.message) > 50 else "")
                    await self.db.commit()
            except (asyncio.CancelledError, GeneratorExit, Exception):
                await self.db.rollback()
                raise
        else:
            start = time.time()
            response = await provider.generate(
                messages=api_messages,
                model=model or chat.model,
                system_prompt=system_prompt,
                temperature=request.temperature or chat.temperature,
                max_tokens=request.max_tokens or chat.max_tokens,
            )
            user_msg = Message(chat_id=chat_id, role="user", content=request.message)
            assistant_msg = Message(
                chat_id=chat_id,
                role="assistant",
                content=response.content,
                model=response.model,
                provider=provider_name,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                latency_ms=response.latency_ms,
            )
            self.db.add(user_msg)
            self.db.add(assistant_msg)
            if chat.title == "New Chat":
                chat.title = request.message[:50] + ("..." if len(request.message) > 50 else "")
            await self.db.commit()
            yield StreamChunk(
                type="content",
                content=response.content,
                model=response.model,
                provider=provider_name,
            )
            yield StreamChunk(
                type="done",
                content="",
                model=response.model,
                provider=provider_name,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                done=True,
            )

    async def create_folder(self, user_id: str, name: str, icon: str | None = None, color: str | None = None) -> ChatFolder:
        folder = ChatFolder(user_id=user_id, name=name, icon=icon, color=color)
        self.db.add(folder)
        await self.db.commit()
        await self.db.refresh(folder)
        return folder

    async def get_folders(self, user_id: str) -> list[ChatFolder]:
        result = await self.db.execute(
            select(ChatFolder).where(ChatFolder.user_id == user_id).order_by(ChatFolder.sort_order)
        )
        return result.scalars().all()

    async def delete_folder(self, folder_id: str, user_id: str) -> bool:
        result = await self.db.execute(
            select(ChatFolder).where(ChatFolder.id == folder_id, ChatFolder.user_id == user_id)
        )
        folder = result.scalar_one_or_none()
        if not folder:
            return False
        await self.db.delete(folder)
        await self.db.commit()
        return True
