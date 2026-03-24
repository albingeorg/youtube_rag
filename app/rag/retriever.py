"""
app/rag/retriever.py
────────────────────
Responsible for finding the most relevant chunks for a given query.

Current implementation: TF-IDF-inspired keyword scoring (no external vector DB).
The interface is designed so a vector-based retriever (e.g. ChromaDB + embeddings)
can be dropped in as a replacement without touching any other module.
"""

import math
import re
from collections import Counter

from app.rag.chunker import Chunk
from app.core.logging import get_logger

logger = get_logger(__name__)

# Common English stop words to exclude from scoring
_STOP_WORDS: frozenset[str] = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "has", "have", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "this", "that", "these", "those", "it", "its",
    "i", "you", "he", "she", "we", "they", "what", "which", "who", "how",
})


def _tokenize(text: str) -> list[str]:
    """Lowercase, strip punctuation, remove stop words."""
    tokens = re.findall(r"[a-z]+", text.lower())
    return [t for t in tokens if t not in _STOP_WORDS and len(t) > 1]


def _build_idf(chunks: list[Chunk]) -> dict[str, float]:
    """
    Compute inverse document frequency for each term across all chunks.
    IDF = log(N / (1 + df)) where df = number of chunks containing the term.
    """
    N = len(chunks)
    df: Counter = Counter()
    for chunk in chunks:
        unique_terms = set(_tokenize(chunk.text))
        df.update(unique_terms)
    return {term: math.log(N / (1 + count)) for term, count in df.items()}


class KeywordRetriever:
    """
    TF-IDF keyword retriever over a fixed list of chunks.
    Instantiate once per video, then call `.retrieve()` on each query.
    """

    def __init__(self, chunks: list[Chunk]):
        self._chunks = chunks
        self._idf = _build_idf(chunks)
        # Pre-tokenise chunks for speed
        self._chunk_tokens: list[list[str]] = [_tokenize(c.text) for c in chunks]

    def retrieve(self, query: str, top_k: int = 5) -> list[Chunk]:
        """
        Return the top_k most relevant chunks for the query.
        Scoring: TF-IDF with exact-phrase bonus.
        Falls back to first chunk if nothing scores > 0.
        """
        if not self._chunks:
            return []

        query_tokens = _tokenize(query)
        if not query_tokens:
            return self._chunks[:top_k]

        query_lower = query.lower()
        scores: list[float] = []

        for idx, tokens in enumerate(self._chunk_tokens):
            tf: Counter = Counter(tokens)
            doc_len = max(len(tokens), 1)

            # TF-IDF score
            score = sum(
                (tf[t] / doc_len) * self._idf.get(t, 0.0)
                for t in query_tokens
            )

            # Exact-phrase bonus
            if query_lower in self._chunks[idx].text.lower():
                score += 1.5

            # Recency boost — earlier chunks get slight preference when tied
            recency_penalty = idx * 0.0001
            score -= recency_penalty

            scores.append(score)

        # Rank and pick top_k
        ranked = sorted(
            range(len(scores)), key=lambda i: scores[i], reverse=True
        )
        top_indices = [i for i in ranked[:top_k] if scores[i] > 0]

        if not top_indices:
            logger.debug("No positive-score chunks, returning first chunk")
            return self._chunks[:1]

        # Return in video order (ascending timestamp) for better context
        top_indices.sort(key=lambda i: self._chunks[i].start_time)
        return [self._chunks[i] for i in top_indices]