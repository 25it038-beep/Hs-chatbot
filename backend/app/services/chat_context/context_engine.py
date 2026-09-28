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

logger = logging.getLogger("hsbot.chat_context.engine")


class GeneralChatContextEngineV2:
    """
    Production-grade context management, universal file extraction,
    and token-budgeted prompt assembler for General Chat.
    """

    async def prepare_context(
        self,
        model_id: str,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        attached_files: Optional[List[Dict[str, Any]]] = None,
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

        attached_files = attached_files or []
        analysis_results: List[FileAnalysisResult] = []
        all_chunks: List[DocumentChunk] = []
        file_citations: List[str] = []

        # 1. Process all attached files
        if attached_files:
            obs.phase = ChatRequestPhase.READING_FILES
            obs.file_count = len(attached_files)
            for f_info in attached_files:
                f_path = f_info.get("file_path") or f_info.get("path") or ""
                f_name = f_info.get("filename") or f_info.get("name") or os.path.basename(f_path)
                f_id = str(f_info.get("file_id") or f_info.get("id") or f_name)
                m_type = f_info.get("mime_type") or f_info.get("type")

                if f_path and os.path.exists(f_path):
                    res = await file_adapter_registry.process_file(
                        file_path=f_path,
                        filename=f_name,
                        file_id=f_id,
                        mime_type=m_type
                    )
                    analysis_results.append(res)
                    all_chunks.extend(res.chunks)
                    file_citations.extend(res.citations)
                    obs.input_sources.append(f_name)

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

        # Budget allocation:
        # Total usable budget minus system prompt and user query
        available_pool = max(1000, budget.usable_budget - sys_tokens - user_msg_tokens)

        # Allocate up to 65% of available pool to documents if files are attached
        max_file_tokens = int(available_pool * 0.65) if all_chunks else 0
        selected_chunks: List[DocumentChunk] = []
        file_context_str = ""

        if all_chunks:
            total_chunk_tokens = sum(c.token_count for c in all_chunks)
            if total_chunk_tokens <= max_file_tokens:
                selected_chunks = all_chunks
            else:
                selected_chunks = chunk_ranker.select_top_chunks(
                    chunks=all_chunks,
                    query=user_message,
                    token_budget=max_file_tokens
                )

            obs.retrieved_chunks_count = len(selected_chunks)

            # Build file summaries header
            file_summaries_header = "### Attached Documents Summary:\n"
            for a_res in analysis_results:
                file_summaries_header += f"- **{a_res.filename}**: {a_res.summary}\n"

            # Build extracted chunks body
            chunks_body = "\n\n".join(c.content for c in selected_chunks)
            file_context_str = (
                f"\n\n==================== ATTACHED FILE CONTEXT ====================\n"
                f"{file_summaries_header}\n"
                f"### Relevant Extracted Content:\n"
                f"{chunks_body}\n"
                f"================================================================"
            )

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
            "file_analysis": [r.to_dict() for r in analysis_results],
            "citations": list(dict.fromkeys(file_citations)),
            "chunks_included": len(selected_chunks)
        }

        return final_messages, meta


general_chat_context_engine = GeneralChatContextEngineV2()
