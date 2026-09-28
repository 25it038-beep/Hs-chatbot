import re
import logging
from typing import List, Dict, Any, Optional
from app.services.chat_context.contracts import ConversationContextSummary
from app.services.chat_context.budget import estimate_tokens

logger = logging.getLogger("hsbot.chat_context.conversation")


class ConversationContextStore:
    """
    Manages long-running conversation history and intelligent compaction.
    Keeps recent conversational turns verbatim while compressing older history
    into a structured memory summary when token limits are approached.
    """

    def _extract_summary(self, older_messages: List[Dict[str, str]]) -> ConversationContextSummary:
        """
        Extracts structured bullet points from older messages to form memory summary.
        """
        requirements = []
        decisions = []
        topics = []

        req_pattern = re.compile(r'\b(?:need|want|must|require|please make sure|should|prefer)\b\s+([^.\n]+)', re.I)
        dec_pattern = re.compile(r'\b(?:agreed|decided|chose|using|we will|i will)\b\s+([^.\n]+)', re.I)

        for m in older_messages:
            content = m.get("content", "")
            role = m.get("role", "")

            # Look for explicit requirements in user messages
            if role == "user":
                for match in req_pattern.finditer(content):
                    clause = match.group(1).strip()
                    if 10 < len(clause) < 120 and clause not in requirements:
                        requirements.append(clause)
            elif role == "assistant":
                for match in dec_pattern.finditer(content):
                    clause = match.group(1).strip()
                    if 10 < len(clause) < 120 and clause not in decisions:
                        decisions.append(clause)

        # Infer topic from first user message
        active_topic = "General Discussion"
        for m in older_messages:
            if m.get("role") == "user":
                lines = [ln.strip() for ln in m.get("content", "").splitlines() if ln.strip()]
                if lines:
                    first_line = lines[0]
                    active_topic = first_line[:80]
                    break

        summary_lines = [f"- Topic: {active_topic}"]
        if requirements:
            summary_lines.append(f"- User Requirements: {'; '.join(requirements[:4])}")
        if decisions:
            summary_lines.append(f"- Established Decisions: {'; '.join(decisions[:4])}")
        summary_lines.append(f"- Earlier Turns: {len(older_messages)} previous messages summarized for context.")

        summary_text = "[CONVERSATION MEMORY SUMMARY]\n" + "\n".join(summary_lines)

        return ConversationContextSummary(
            active_topic=active_topic,
            user_requirements=requirements[:6],
            decisions=decisions[:6],
            summary_text=summary_text
        )

    def compact_history(
        self,
        messages: List[Dict[str, str]],
        history_budget: int,
        preserve_recent_turns: int = 4
    ) -> List[Dict[str, str]]:
        """
        Returns a history sequence guaranteed to fit within `history_budget`.
        """
        if not messages:
            return []

        total_tokens = sum(estimate_tokens(m.get("content", "")) for m in messages)
        if total_tokens <= history_budget:
            return messages

        # Budget exceeded: separate recent messages from older ones
        # preserve_recent_turns counts individual messages (user + assistant pairs)
        recent_count = min(len(messages), max(2, preserve_recent_turns * 2))
        recent_messages = messages[-recent_count:]
        older_messages = messages[:-recent_count]

        if not older_messages:
            # All messages are recent, trim from the earliest until it fits
            trimmed = list(recent_messages)
            while trimmed and sum(estimate_tokens(m.get("content", "")) for m in trimmed) > history_budget:
                trimmed.pop(0)
            return trimmed

        # Build compact summary of older messages
        summary = self._extract_summary(older_messages)
        summary_msg = {
            "role": "system",
            "content": (
                f"{summary.summary_text}\n"
                f"[End of earlier conversation summary. The following are the most recent messages.]"
            )
        }

        # Check if summary + recent_messages fits
        combined = [summary_msg] + recent_messages
        while len(combined) > 2 and sum(estimate_tokens(m.get("content", "")) for m in combined) > history_budget:
            # Remove earliest message from recent (after summary)
            combined.pop(1)

        return combined


conversation_context_store = ConversationContextStore()
