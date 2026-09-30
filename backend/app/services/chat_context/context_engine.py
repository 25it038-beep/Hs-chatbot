import os
import time
import logging
from typing import List, Dict, Any, Optional, Tuple
from app.services.chat_context.contracts import (
    ContextBudget,
    DocumentChunk,
    FileAnalysisResult,
    RequestObservability,
    ChatRequestPhase
)
from app.services.chat_context.budget import (
    compute_context_budget,
    estimate_tokens,
    DEFAULT_SAFETY_MARGIN,
    DEFAULT_OUTPUT_BUDGET
)
from app.services.chat_context.file_adapters.registry import file_adapter_registry
from app.services.chat_context.ranker import chunk_ranker
from app.services.chat_context.conversation_store import conversation_context_store
from app.services.chat_context.retrieval_engine import file_retrieval_engine

logger = logging.getLogger("hsbot.chat_context.engine")


class GeneralChatFileContextEngineV2:
    """
    Production-grade context management, universal file extraction,
    and token-budgeted prompt assembler for General Chat.
    Resolves files across request attachments, conversation history, and explicit user mentions.
    """

    async def prepare_context(
        self,
        model_id: str,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        user_id: Optional[str] = None,
        chat_id: Optional[str] = None,
        attached_files: Optional[List[Dict[str, Any]]] = None,
        file_ids: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
        """
        Processes attached files, ranks chunks, budgets tokens with safety headroom,
        compacts history, and constructs the final prompt messages.
        """
        start_time = time.time()
        req_id = request_id or f"req_{int(start_time * 1000)}"

        obs = RequestObservability(
            request_id=req_id,
            model=model_id,
            started_at=start_time,
            phase=ChatRequestPhase.PREPARING_CONTEXT,
            input_sources=["user_message"]
        )

        budget = compute_context_budget(
            model_id=model_id,
            output_budget=DEFAULT_OUTPUT_BUDGET,
            safety_margin=DEFAULT_SAFETY_MARGIN
        )

        # 1. Resolve active files across current request, conversation history, and prompt mentions
        resolved_files: List[Dict[str, Any]] = []
        if user_id:
            resolved_files = await file_retrieval_engine.resolve_active_files(
                user_id=user_id,
                chat_id=chat_id,
                file_ids=file_ids,
                attachments=attached_files,
                message=user_message
            )
        elif attached_files:
            resolved_files = attached_files

        obs.file_count = len(resolved_files)
        for rf in resolved_files:
            obs.input_sources.append(rf.get("filename", "file"))

        # 2. Token budgeting: System Prompt
        sys_content = system_prompt or (
            "You are HSBot, an advanced, helpful, and truthful AI assistant. "
            "When answering questions based on attached documents, cite specific sections, "
            "pages, or line numbers accurately. If information is not in the documents, state so clearly."
        )
        sys_tokens = estimate_tokens(sys_content)
        budget.system_tokens = sys_tokens

        # 3. Token budgeting: User query & attached file context
        user_msg_tokens = estimate_tokens(user_message)
        budget.user_tokens = user_msg_tokens

        # Budget allocation: usable budget minus system and user message
        available_pool = max(1000, budget.usable_budget - sys_tokens - user_msg_tokens)
        max_file_tokens = int(available_pool * 0.65) if resolved_files else 0

        file_context_str = ""
        citations: List[str] = []
        retrieved_chunks_count = 0
        analysis_results: List[Dict[str, Any]] = []

        if resolved_files:
            obs.phase = ChatRequestPhase.READING_FILES
            retrieval_result = await file_retrieval_engine.retrieve_relevant_context(
                user_id=user_id or "default_user_id",
                chat_id=chat_id,
                query=user_message,
                active_files=resolved_files,
                token_budget=max_file_tokens
            )
            file_context_str = retrieval_result.get("context_text", "")
            citations = retrieval_result.get("citations", [])
            retrieved_chunks = retrieval_result.get("chunks", [])
            retrieved_chunks_count = len(retrieved_chunks)
            obs.retrieved_chunks_count = retrieved_chunks_count

        file_tokens = estimate_tokens(file_context_str)
        budget.file_tokens = file_tokens

        # 4. Token budgeting: Conversation History
        history_budget = max(500, budget.usable_budget - sys_tokens - user_msg_tokens - file_tokens)
        compacted_history = conversation_context_store.compact_history(
            messages=conversation_history,
            history_budget=history_budget
        )
        history_tokens = sum(estimate_tokens(m.get("content", "")) for m in compacted_history)
        budget.history_tokens = history_tokens

        budget.remaining_tokens = max(
            0,
            budget.usable_budget - (sys_tokens + user_msg_tokens + file_tokens + history_tokens)
        )

        # 5. Assemble final message list
        final_messages: List[Dict[str, str]] = []

        # System message
        final_messages.append({"role": "system", "content": sys_content})

        # History messages
        final_messages.extend(compacted_history)

        # Final user message with attached file context
        final_user_content = user_message
        if file_context_str:
            final_user_content = f"{user_message}{file_context_str}"

        final_messages.append({"role": "user", "content": final_user_content})

        obs.context_size = sum(estimate_tokens(m["content"]) for m in final_messages)
        obs.phase = ChatRequestPhase.CALLING_MODEL

        meta = {
            "budget": budget.to_dict(),
            "observability": obs.to_dict(),
            "active_files": resolved_files,
            "citations": citations,
            "chunks_included": retrieved_chunks_count
        }

        return final_messages, meta


GeneralChatContextEngineV2 = GeneralChatFileContextEngineV2
general_chat_context_engine = GeneralChatFileContextEngineV2()
general_chat_file_context_engine = general_chat_context_engine
