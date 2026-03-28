"""
app/rag/store.py
────────────────
In-memory store that holds indexed video data.

Each entry contains:
  - metadata (title, url, stats)
  - chunks (list[Chunk])
  - retriever (KeywordRetriever instance)

Designed with a clean interface so swapping to a persistent store
(Redis, SQLite, Postgres) requires only changing this file.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from app.rag.chunker import Chunk
from app.rag.retriever import KeywordRetriever
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class VideoEntry:
    """All data associated with a processed video."""

    video_id: str
    title: str
    url: str
    chunks: list[Chunk]
    retriever: KeywordRetriever
    transcript_length: int
    indexed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def chunk_count(self) -> int:
        return len(self.chunks)

    def to_summary(self) -> dict:
        """Lightweight dict for API list responses."""
        return {
            "video_id": self.video_id,
            "title": self.title,
            "url": self.url,
            "chunk_count": self.chunk_count,
            "transcript_length": self.transcript_length,
            "indexed_at": self.indexed_at.isoformat(),
        }


class VideoStore:
    """
    Thread-safe in-memory video index.
    Single instance shared across the FastAPI app (app-level state).
    """

    def __init__(self):
        self._store: dict[str, VideoEntry] = {}
        self._chat_history: dict[str, list[dict]] = {}

    def exists(self, video_id: str) -> bool:
        return video_id in self._store

    def exists_by_url_or_id(self, url_or_id: str) -> bool:
        """Check existence by video ID or by URL (checks all stored URLs)."""
        if url_or_id in self._store:
            return True
        return any(e.url == url_or_id for e in self._store.values())

    def get(self, video_id: str) -> Optional[VideoEntry]:
        return self._store.get(video_id)

    def add(self, entry: VideoEntry) -> None:
        self._store[entry.video_id] = entry
        logger.info(
            f"Stored video '{entry.video_id}' — "
            f"{entry.chunk_count} chunks, {entry.transcript_length} chars"
        )

    def delete(self, video_id: str) -> bool:
        if video_id in self._store:
            del self._store[video_id]
            self.delete_chat_history(video_id)
            logger.info(f"Deleted video '{video_id}' from store")
            return True
        return False

    def list_all(self) -> list[dict]:
        return [entry.to_summary() for entry in self._store.values()]

    def count(self) -> int:
        return len(self._store)

    def get_chat_history(self, video_id: str) -> list[dict]:
        """Retrieves chat history for a video, returns empty list if none."""
        return self._chat_history.get(video_id, [])

    def set_chat_history(self, video_id: str, history: list[dict]):
        """Saves or overwrites the chat history for a video."""
        self._chat_history[video_id] = history
        logger.info(
            f"Saved chat history for video '{video_id}' ({len(history)} messages)"
        )

    def delete_chat_history(self, video_id: str):
        """Deletes chat history for a video if it exists."""
        if video_id in self._chat_history:
            del self._chat_history[video_id]
            logger.info(f"Deleted chat history for video '{video_id}'")


# Create a single global instance of the store
# This will be shared across all API requests
vector_store = VideoStore()