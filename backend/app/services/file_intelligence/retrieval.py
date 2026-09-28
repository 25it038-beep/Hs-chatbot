"""
HSBot General Chat — File Retrieval Engine (FileRetrievalEngineV2)
Handles explicit file references, conversation memory file resolution, structure-aware retrieval,
exact occurrence search, hierarchical large-document selection, and multi-file cross-retrieval.
"""
import re
import math
from collections import Counter
from typing import Optional, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message
from app.services.file_intelligence.models import (
    ProcessedFileRepresentation,
    FileChunk,
    FileProcessingState,
)
from app.services.file_intelligence.storage import FileStorageManagerV2


STOPWORDS = {
    "the", "and", "for", "that", "this", "with", "from", "what", "where", "when",
    "which", "who", "whom", "whose", "why", "how", "are", "was", "were", "been",
    "being", "have", "has", "had", "does", "did", "will", "would", "should", "could",
    "can", "may", "might", "must", "shall", "about", "into", "through", "during",
    "before", "after", "above", "below", "between", "under", "again", "further",
    "then", "once", "here", "there", "all", "any", "both", "each", "few", "more",
    "most", "other", "some", "such", "only", "own", "same", "than", "too", "very",
    "file", "files", "document", "documents", "uploaded", "earlier", "use", "please",
    "tell", "show", "give", "find", "explain", "analyze", "summarize", "compare",
}


def tokenize(text: str) -> list[str]:
    return [
        tok
        for tok in re.findall(r"[a-zA-Z0-9_]{2,}", (text or "").lower())
        if tok not in STOPWORDS
    ]


class FileRetrievalEngineV2:
    """Retrieves relevant, source-cited chunks across 1 or N conversation files."""

    @staticmethod
    def extract_filename_mentions(message: str) -> tuple[str, list[str]]:
        """
        Extract explicit [File: ...], [Image: ...], [Files: ...] tags as well as inline
        filename mentions (e.g., 'report.pdf', 'data.xlsx') from the user prompt.
        Returns (cleaned_query, mentioned_filenames).
        """
        if not message:
            return "", []

        mentions: list[str] = []

        # 1. Bracket tags: [File: a.pdf], [Image: b.png], [Files: a.pdf, b.xlsx]
        for m in re.finditer(r"\[(?:File|Image|Files):\s*([^\]]+)\]", message, re.IGNORECASE):
            raw_inside = m.group(1)
            for part in raw_inside.split(","):
                p = part.strip()
                if p and p not in mentions:
                    mentions.append(p)

        cleaned = re.sub(r"\[(?:File|Image|Files):\s*[^\]]+\]\s*", "", message, flags=re.IGNORECASE).strip()

        # 2. Inline filenames with known extensions in the prompt text
        inline_re = re.compile(
            r"\b([A-Za-z0-9_\-\s]{1,80}\.(?:pdf|docx|doc|xlsx|xls|csv|tsv|pptx|ppt|txt|md|json|jsonl|xml|yaml|yml|py|js|ts|tsx|jsx|java|go|rs|c|cpp|cs|rb|php|sql|sh|html|css|png|jpg|jpeg|webp|gif|bmp|zip|tar|gz|tgz|mp3|wav|mp4|[a-z0-9]{2,5}))\b",
            re.IGNORECASE,
        )
        for m in inline_re.finditer(cleaned):
            candidate = m.group(1).strip()
            # Only take the last word if space was matched greedily
            if " " in candidate and not any( candidate.lower().startswith(p) for p in ("my ", "the ") ):
                candidate = candidate.split()[-1]
            elif " " in candidate:
                candidate = candidate.split()[-1]
            if candidate and candidate not in mentions:
                mentions.append(candidate)

        return cleaned or message, mentions

    @classmethod
    async def resolve_active_files(
        cls,
        db: AsyncSession,
        user_id: str,
        message: str,
        explicit_file_ids: Optional[list[str]] = None,
        conversation_id: Optional[str] = None,
        message_id: Optional[str] = None,
    ) -> tuple[list[ProcessedFileRepresentation], set[str], str]:
        """
        Resolve all files relevant to the current turn:
        1. Explicit fileIds attached to the request (links them to conversation_id).
        2. Explicit filenames named in the prompt -> marked in required_file_ids.
        3. Conversation-linked files from earlier messages in the same chat (so follow-ups & refresh work!).
        Returns (resolved_representations, required_file_ids, cleaned_prompt).
        """
        cleaned_prompt, mentioned_names = cls.extract_filename_mentions(message)
        resolved: list[ProcessedFileRepresentation] = []
        seen_ids: set[str] = set()
        required_ids: set[str] = set()

        # 1. Explicit file IDs passed in request.files
        if explicit_file_ids:
            valid_ids = [fid for fid in explicit_file_ids if fid and not str(fid).startswith("local-")]
            if conversation_id and valid_ids:
                reps = await FileStorageManagerV2.link_files_to_conversation(
                    db=db,
                    user_id=user_id,
                    file_ids=valid_ids,
                    conversation_id=conversation_id,
                    message_id=message_id,
                )
                for r in reps:
                    if r.fileId not in seen_ids:
                        seen_ids.add(r.fileId)
                        required_ids.add(r.fileId)
                        resolved.append(r)
            else:
                for fid in valid_ids:
                    r = await FileStorageManagerV2.load_representation(db, user_id, fid)
                    if r and r.fileId not in seen_ids:
                        seen_ids.add(r.fileId)
                        required_ids.add(r.fileId)
                        resolved.append(r)

        # 2. Conversation files persisted in GeneratedFile(conversation_id=chat_id)
        if conversation_id:
            conv_reps = await FileStorageManagerV2.get_conversation_files(db, user_id, conversation_id)
            for r in conv_reps:
                if r.fileId not in seen_ids:
                    seen_ids.add(r.fileId)
                    resolved.append(r)

            # Also check Message.extra_data["attachments"] in this conversation (survives any legacy links)
            try:
                stmt = (
                    select(Message)
                    .where(Message.chat_id == str(conversation_id))
                    .order_by(Message.created_at.desc())
                    .limit(30)
                )
                m_res = await db.execute(stmt)
                msgs = m_res.scalars().all()
                for m in msgs:
                    if isinstance(m.extra_data, dict):
                        atts = m.extra_data.get("attachments") or m.extra_data.get("user_attachments") or []
                        for att in atts:
                            if isinstance(att, dict):
                                aid = att.get("fileId") or att.get("id")
                                if aid and aid not in seen_ids and not str(aid).startswith("local-"):
                                    rep = await FileStorageManagerV2.load_representation(db, user_id, str(aid))
                                    if rep:
                                        seen_ids.add(rep.fileId)
                                        resolved.append(rep)
            except Exception:
                pass

        # 3. Match any explicit filename mentions in the prompt
        if mentioned_names:
            for r in resolved:
                if any(
                    m.lower() == r.filename.lower() or m.lower() in r.filename.lower()
                    for m in mentioned_names
                ):
                    required_ids.add(r.fileId)

            # If a mentioned filename wasn't in resolved yet, look it up in user's recent uploads
            unmatched_mentions = [
                m for m in mentioned_names
                if not any(m.lower() == r.filename.lower() or m.lower() in r.filename.lower() for r in resolved)
            ]
            if unmatched_mentions:
                found_by_name = await FileStorageManagerV2.find_user_files_by_name_or_recent(
                    db=db,
                    user_id=user_id,
                    filename_hints=unmatched_mentions,
                    conversation_id=conversation_id,
                )
                for r in found_by_name:
                    if r.fileId not in seen_ids:
                        seen_ids.add(r.fileId)
                        required_ids.add(r.fileId)
                        resolved.append(r)
                        if conversation_id:
                            await FileStorageManagerV2.link_files_to_conversation(
                                db, user_id, [r.fileId], conversation_id, message_id
                            )

        # 4. If user says "use the file I uploaded earlier" / "use that file again" and resolved is still empty,
        # check the user's most recently uploaded file ONLY if they explicitly refer to an uploaded file
        if not resolved and re.search(
            r"\b(?:uploaded\s+earlier|that\s+file|the\s+file|previous\s+file|attached\s+file|the\s+document|the\s+pdf|the\s+spreadsheet)\b",
            message.lower(),
        ):
            recent_reps = await FileStorageManagerV2.find_user_files_by_name_or_recent(
                db=db,
                user_id=user_id,
                filename_hints=None,
                conversation_id=conversation_id,
                limit=3,
            )
            for r in recent_reps:
                if r.fileId not in seen_ids:
                    seen_ids.add(r.fileId)
                    resolved.append(r)

        return resolved, required_ids, cleaned_prompt

    @staticmethod
    def search_within_file(
        rep: ProcessedFileRepresentation,
        query: str,
        top_k: int = 12,
    ) -> list[dict[str, Any]]:
        """
        Search within an uploaded file for specific terms, functions, sections, pages, or slides.
        Supports exact occurrence search ("Find every occurrence of 'revenue'") and ranked chunk search.
        """
        if not rep.chunks:
            return []

        q_clean = (query or "").strip()
        q_lower = q_clean.lower()

        # Check if user quoted a specific search phrase (e.g., 'revenue' or "login")
        quoted = re.findall(r"['\"]([^'\"]{2,80})['\"]", q_clean)
        q_tokens = tokenize(q_clean)
        for q_phrase in quoted:
            for t in q_phrase.lower().split():
                if t not in q_tokens:
                    q_tokens.append(t)

        # Page number filter (e.g. "page 24" or "pages 18-23")
        requested_pages: set[int] = set()
        for pm in re.finditer(r"\bpages?\s+(\d+)(?:\s*[-–to]+\s*(\d+))?\b", q_lower):
            p1 = int(pm.group(1))
            p2 = int(pm.group(2)) if pm.group(2) else p1
            for p_num in range(min(p1, p2), max(p1, p2) + 1):
                requested_pages.add(p_num)

        # Slide number filter (e.g. "slide 3")
        requested_slides: set[int] = set()
        for sm in re.finditer(r"\bslides?\s+(\d+)(?:\s*[-–to]+\s*(\d+))?\b", q_lower):
            s1 = int(sm.group(1))
            s2 = int(sm.group(2)) if sm.group(2) else s1
            for s_num in range(min(s1, s2), max(s1, s2) + 1):
                requested_slides.add(s_num)

        # Line range filter (e.g. "lines 45-82")
        requested_lines: Optional[tuple[int, int]] = None
        lm = re.search(r"\blines?\s+(\d+)(?:\s*[-–to]+\s*(\d+))?\b", q_lower)
        if lm:
            l1 = int(lm.group(1))
            l2 = int(lm.group(2)) if lm.group(2) else l1
            requested_lines = (min(l1, l2), max(l1, l2))

        # Compute IDF across chunks
        N = len(rep.chunks)
        df: Counter[str] = Counter()
        chunk_tokens_list: list[Counter[str]] = []
        for ch in rep.chunks:
            c_toks = Counter(tokenize(ch.text))
            chunk_tokens_list.append(c_toks)
            for tok in c_toks:
                df[tok] += 1

        scored: list[tuple[float, int, FileChunk]] = []
        is_summary_or_conclusion = bool(
            re.search(
                r"\b(summar(?:y|ize)|conclu(?:de|sion|sions)|overview|key\s+points|main\s+points|risks|findings|takeaways|entire|whole)\b",
                q_lower,
            )
        )
        is_auth_or_bug_query = bool(
            re.search(r"\b(auth|authentication|login|token|password|jwt|bug|error|fail|broken|issue|security)\b", q_lower)
        )

        for idx, ch in enumerate(rep.chunks):
            score = 0.0
            c_text_lower = ch.text.lower()
            meta = ch.metadata

            # 1. Exact page / slide / line match gets massive priority
            if requested_pages and meta.page in requested_pages:
                score += 100.0
            if requested_slides and meta.slide in requested_slides:
                score += 100.0
            if requested_lines and meta.lineStart is not None and meta.lineEnd is not None:
                if meta.lineStart <= requested_lines[1] and meta.lineEnd >= requested_lines[0]:
                    score += 100.0

            # 2. Quoted phrase exact match
            for phrase in quoted:
                occ = c_text_lower.count(phrase.lower())
                if occ > 0:
                    score += 35.0 * occ

            # 3. BM25-style lexical score over query tokens
            c_toks = chunk_tokens_list[idx]
            for tok in q_tokens:
                tf = c_toks.get(tok, 0)
                if tf > 0:
                    idf = math.log(1.0 + (N - df[tok] + 0.5) / (df[tok] + 0.5))
                    score += idf * ((tf * 2.2) / (tf + 1.2))
                elif tok in c_text_lower:
                    score += 1.5

                # Boost if token matches section / sheet / innerPath / symbol
                if meta.section and tok in meta.section.lower():
                    score += 6.0
                if meta.sheet and tok in meta.sheet.lower():
                    score += 8.0
                if meta.innerPath and tok in meta.innerPath.lower():
                    score += 8.0

            # 4. Code / ZIP authentication or bug-hunting boost (Section 16 & 57)
            if is_auth_or_bug_query and (meta.innerPath or meta.sourceType == "code"):
                path_or_sec = f"{meta.innerPath or ''} {meta.section or ''}".lower()
                if any(k in path_or_sec for k in ("auth", "login", "security", "user", "token", "session", "route", "api", "config", "test")):
                    score += 15.0

            # 5. Hierarchical document reasoning boost for summary/conclusion queries (Section 33)
            if is_summary_or_conclusion:
                if idx == 0 or idx == 1:
                    score += 8.0  # Introduction / Executive Summary
                if idx >= max(0, N - 2):
                    score += 10.0  # Conclusion / Final pages
                if meta.section and any(
                    k in meta.section.lower()
                    for k in ("summary", "conclusion", "risk", "finding", "overview", "introduction", "recommendation", "result")
                ):
                    score += 14.0
                if any(
                    k in c_text_lower
                    for k in ("in conclusion", "we conclude", "conclusion", "key risks", "biggest risks", "summary", "findings")
                ):
                    score += 10.0

            # Small positional tie-breaker so earlier chunks come first when scores are equal
            score += max(0.0, 0.5 - (idx * 0.001))
            scored.append((score, idx, ch))

        scored.sort(key=lambda x: (-x[0], x[1]))
        selected = scored[:top_k]
        # Re-sort selected chunks in natural document order for coherent reading
        selected.sort(key=lambda x: x[1])

        return [
            {
                "chunkId": ch.chunkId,
                "score": round(sc, 3),
                "text": ch.text,
                "tokenEstimate": ch.tokenEstimate,
                "citation": ch.metadata.format_citation(),
                "metadata": ch.metadata.to_compact_dict(),
            }
            for sc, _, ch in selected
        ]

    @staticmethod
    def find_exact_occurrences(rep: ProcessedFileRepresentation, query: str) -> Optional[str]:
        """
        When user asks 'Find every occurrence of X' or 'Where is X mentioned',
        scans the entire file and returns exact locations (page/slide/sheet/line) and snippets.
        """
        q_lower = (query or "").lower()
        m = re.search(
            r"(?:every\s+occurrence\s+of|all\s+occurrences\s+of|find\s+all\s+(?:python\s+)?functions?\s+named|search\s+for|mentions?\s+of)\s+['\"]?([A-Za-z0-9_\-\s]{2,50})['\"]?",
            query or "",
            re.IGNORECASE,
        )
        target_term = None
        if m:
            target_term = m.group(1).strip().strip("'\"?.!")
        else:
            quoted = re.findall(r"['\"]([^'\"]{2,50})['\"]", query or "")
            if quoted and any(w in q_lower for w in ("find", "occurrence", "where", "search", "count", "how many times")):
                target_term = quoted[0].strip()

        if not target_term or len(target_term) < 2:
            return None

        term_lower = target_term.lower()
        hits: list[str] = []
        total_count = 0

        for ch in rep.chunks:
            c_lower = ch.text.lower()
            cnt = c_lower.count(term_lower)
            if cnt > 0:
                total_count += cnt
                cit = ch.metadata.format_citation()
                # Extract matching lines
                matching_lines = [
                    line.strip()
                    for line in ch.text.splitlines()
                    if term_lower in line.lower()
                ]
                preview_line = " | ".join(matching_lines[:3])[:300]
                hits.append(f"  • {cit} ({cnt}x): {preview_line}")

        if not hits:
            return f"=== EXACT FILE SEARCH RESULT ({rep.filename}) ===\nTerm '{target_term}': 0 occurrences found."

        return (
            f"=== EXACT FILE SEARCH RESULT ({rep.filename}) ===\n"
            f"Term '{target_term}': {total_count} total occurrence(s) across {len(hits)} section(s):\n"
            + "\n".join(hits[:30])
        )
