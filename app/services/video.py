"""
app/services/video.py
──────────────────────
Orchestrates the full RAG pipeline for a single video:
  fetch transcript → chunk → build retriever → store

This is the only place that composes the rag.* modules together.
"""

from app.core.config import get_settings
from app.core.logging import get_logger
from app.rag.transcript import extract_video_id, fetch_transcript, fetch_video_title
from app.rag.chunker import chunk_transcript
from app.rag.retriever import KeywordRetriever
from app.rag.store import VideoStore, VideoEntry

logger = get_logger(__name__)


class VideoService:
    """
    High-level service consumed by API route handlers.
    Injected with a shared VideoStore and LLMService.
    """

    def __init__(self, store: VideoStore):
        self._store = store
        self._settings = get_settings()

    def process(self, url: str) -> VideoEntry:
        """
        Process a YouTube URL end-to-end:
          1. Extract video ID
          2. Return cached entry if already indexed
          3. Fetch transcript
          4. Chunk transcript
          5. Build retriever
          6. Persist to store

        Returns the VideoEntry (new or cached).
        """
        video_id = extract_video_id(url)

        # ── Cache hit ─────────────────────────────────────────────
        if self._store.exists(video_id):
            logger.info(f"Cache hit for video '{video_id}'")
            return self._store.get(video_id)

        # ── Fetch ─────────────────────────────────────────────────
        logger.info(f"Processing new video '{video_id}'")
        title = fetch_video_title(video_id)
        segments = fetch_transcript(video_id)

        # ── Chunk ─────────────────────────────────────────────────
        chunks = chunk_transcript(
            segments,
            chunk_size=self._settings.chunk_size,
            overlap=self._settings.chunk_overlap,
        )
        logger.info(f"Created {len(chunks)} chunks for '{video_id}'")

        # ── Index ─────────────────────────────────────────────────
        retriever = KeywordRetriever(chunks)

        transcript_length = sum(len(s["text"]) for s in segments)

        entry = VideoEntry(
            video_id=video_id,
            title=title,
            url=url,
            chunks=chunks,
            retriever=retriever,
            transcript_length=transcript_length,
        )
        self._store.add(entry)
        return entry

    def retrieve_and_answer_context(
        self, video_id: str, question: str
    ) -> tuple[list, list[str]]:
        """
        Retrieve relevant chunks for a question from an indexed video.

        Returns:
            (chunks, source_timestamps)
        Raises VideoNotFoundError if the video isn't in the store.
        """
        from app.core.exceptions import VideoNotFoundError

        entry = self._store.get(video_id)
        if not entry:
            raise VideoNotFoundError(video_id)

        chunks = entry.retriever.retrieve(
            question, top_k=self._settings.top_k_chunks
        )
        sources = [f"[{c.timestamp_str}]" for c in chunks]
        return chunks, sources, entry.title