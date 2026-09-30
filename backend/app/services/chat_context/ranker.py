import re
import math
from typing import List, Tuple, Dict, Set, Optional, Any
from collections import Counter
from app.services.chat_context.contracts import DocumentChunk

STOP_WORDS: Set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "can't", "cannot", "could",
    "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down",
    "during", "each", "few", "for", "from", "further", "had", "hadn't", "has",
    "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her",
    "here", "here's", "hers", "herself", "him", "himself", "his", "how", "how's",
    "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it",
    "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my",
    "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or",
    "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same",
    "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so",
    "some", "such", "than", "that", "that's", "the", "their", "theirs", "them",
    "themselves", "then", "there", "there's", "these", "they", "they'd", "they'll",
    "they're", "they've", "this", "those", "through", "to", "too", "under", "until",
    "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
    "weren't", "what", "what's", "when", "when's", "where", "where's", "which",
    "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
    "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours",
    "yourself", "yourselves", "tell", "show", "give", "please", "can"
}


class LexicalChunkRanker:
    """
    High-precision BM25 & structural chunk ranker.
    Boosts chunks matching explicit user mentions:
    - filename mentions (e.g. 'in report.pdf')
    - page numbers (e.g. 'on page 14')
    - slide numbers (e.g. 'slide 3')
    - sheet names (e.g. 'Sheet1', 'Q3 Revenue')
    - function/variable names
    """

    def _tokenize(self, text: str) -> List[str]:
        words = re.findall(r'[a-zA-Z0-9_\-\.]+', text.lower())
        return [w for w in words if len(w) > 1 and w not in STOP_WORDS]

    def _extract_intent_hints(self, query: str) -> Dict[str, Any]:
        q_lower = query.lower()
        hints = {
            "page": None,
            "slide": None,
            "sheet": None,
            "files": []
        }

        # Page match: 'page 4', 'p. 4', 'p4'
        page_match = re.search(r'\b(?:page|p\.)\s*(\d+)\b', q_lower)
        if page_match:
            hints["page"] = int(page_match.group(1))

        # Slide match: 'slide 2', 'slide #2'
        slide_match = re.search(r'\bslide\s*(?:#)?(\d+)\b', q_lower)
        if slide_match:
            hints["slide"] = int(slide_match.group(1))

        # Filename pattern: word.ext
        file_matches = re.findall(r'([a-zA-Z0-9_\-]+\.[a-zA-Z0-9]{2,5})', q_lower)
        if file_matches:
            hints["files"] = file_matches

        return hints

    def score_chunks(self, chunks: List[DocumentChunk], query: str) -> List[Tuple[DocumentChunk, float]]:
        if not chunks:
            return []

        query_terms = self._tokenize(query)
        hints = self._extract_intent_hints(query)
        q_lower = query.lower()

        # Document frequencies for BM25 calculation
        doc_count = len(chunks)
        df: Dict[str, int] = Counter()
        chunk_token_lists = []

        avg_doc_len = 0.0
        for chunk in chunks:
            terms = self._tokenize(chunk.content + " " + chunk.section + " " + chunk.source)
            chunk_token_lists.append(terms)
            unique_terms = set(terms)
            for t in unique_terms:
                df[t] += 1
            avg_doc_len += len(terms)

        avg_doc_len = max(1.0, avg_doc_len / doc_count)

        k1 = 1.5
        b = 0.75

        scored: List[Tuple[DocumentChunk, float]] = []

        for idx, chunk in enumerate(chunks):
            chunk_terms = chunk_token_lists[idx]
            doc_len = len(chunk_terms)
            term_freq = Counter(chunk_terms)

            score = 0.0

            # 1. BM25 calculation
            for q_term in query_terms:
                if q_term in term_freq:
                    f = term_freq[q_term]
                    n = df[q_term]
                    idf = math.log((doc_count - n + 0.5) / (n + 0.5) + 1.0)
                    tf = (f * (k1 + 1)) / (f + k1 * (1 - b + b * (doc_len / avg_doc_len)))
                    score += idf * tf

            # 2. Structural & Intent Boosts
            # Filename boost
            if hints["files"]:
                for fn in hints["files"]:
                    if fn in chunk.source.lower():
                        score += 15.0

            # Page boost
            if hints["page"] is not None and chunk.page == hints["page"]:
                score += 12.0

            # Slide boost
            if hints["slide"] is not None and chunk.slide == hints["slide"]:
                score += 12.0

            # Sheet boost
            if chunk.sheet and chunk.sheet.lower() in q_lower:
                score += 10.0

            # Exact phrase match in content
            clean_query = query.strip().lower()
            if len(clean_query) > 5 and clean_query in chunk.content.lower():
                score += 15.0

            # Section title match
            if chunk.section and any(qt in chunk.section.lower() for qt in query_terms):
                score += 5.0

            scored.append((chunk, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def select_top_chunks(
        self,
        chunks: List[DocumentChunk],
        query: str,
        token_budget: int,
        min_chunks_per_file: int = 1
    ) -> List[DocumentChunk]:
        """
        Greedily selects top relevant chunks that fit within the token budget.
        Ensures representation from all referenced files if possible.
        """
        if not chunks:
            return []

        scored = self.score_chunks(chunks, query)
        selected: List[DocumentChunk] = []
        selected_ids: Set[str] = set()
        accumulated_tokens = 0

        # Group by file_id for fair coverage
        file_represented: Set[str] = set()

        # Pass 1: Ensure at least one top chunk from each file if score > 0
        for chunk, score in scored:
            if chunk.file_id not in file_represented:
                if accumulated_tokens + chunk.token_count <= token_budget:
                    selected.append(chunk)
                    selected_ids.add(chunk.chunk_id)
                    file_represented.add(chunk.file_id)
                    accumulated_tokens += chunk.token_count

        # Pass 2: Greedily add remaining highest-scoring chunks
        for chunk, score in scored:
            if chunk.chunk_id in selected_ids:
                continue
            if accumulated_tokens + chunk.token_count <= token_budget:
                selected.append(chunk)
                selected_ids.add(chunk.chunk_id)
                accumulated_tokens += chunk.token_count
            elif token_budget - accumulated_tokens < 100:
                break

        # Fallback guarantee: if nothing could fit (e.g. single chunk exceeded token budget)
        if not selected and scored:
            top_chunk, _ = scored[0]
            if top_chunk.token_count > token_budget:
                char_limit = max(300, token_budget * 4)
                truncated_content = top_chunk.content[:char_limit] + "\n\n[... content truncated to fit token budget ...]"
                truncated_chunk = DocumentChunk(
                    chunk_id=top_chunk.chunk_id,
                    file_id=top_chunk.file_id,
                    source=top_chunk.source,
                    location=top_chunk.location,
                    page=top_chunk.page,
                    section=top_chunk.section,
                    slide=top_chunk.slide,
                    sheet=top_chunk.sheet,
                    start_line=top_chunk.start_line,
                    end_line=top_chunk.end_line,
                    content=truncated_content,
                    token_count=max(1, len(truncated_content) // 4),
                    metadata=top_chunk.metadata
                )
                selected.append(truncated_chunk)
            else:
                selected.append(top_chunk)

        # Re-sort selected chunks back into logical document order (by source, then page/line)
        selected.sort(key=lambda c: (
            c.source,
            c.page or 0,
            c.slide or 0,
            c.start_line or 0,
            c.chunk_id
        ))

        return selected


chunk_ranker = LexicalChunkRanker()
