"""
app/rag/chunker.py
──────────────────
Splits a transcript into overlapping text chunks with associated timestamps.
Keeping this module separate allows easy swapping of chunking strategies
(e.g. sentence-aware, semantic, fixed-token) without touching other layers.
"""

from dataclasses import dataclass, field


@dataclass
class Chunk:
    """A single transcript chunk with metadata."""

    id: int
    text: str
    start_time: float          # seconds from video start
    end_time: float            # approximate end time
    timestamp_str: str         # human-readable MM:SS

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "timestamp_str": self.timestamp_str,
        }


def _format_timestamp(seconds: float) -> str:
    """Convert float seconds to MM:SS string."""
    total = max(0, int(seconds))
    return f"{total // 60:02d}:{total % 60:02d}"


def chunk_transcript(
    segments: list[dict],
    chunk_size: int = 400,
    overlap: int = 60,
) -> list[Chunk]:
    """
    Merge transcript segments into overlapping word-based chunks.

    Args:
        segments:   Raw transcript segments from YouTubeTranscriptApi.
        chunk_size: Target word count per chunk.
        overlap:    Number of words shared between consecutive chunks.

    Returns:
        Ordered list of Chunk objects.
    """
    if not segments:
        return []

    # ── 1. Flatten to (word, timestamp) pairs ────────────────────
    words: list[str] = []
    word_times: list[float] = []

    for seg in segments:
        seg_words = seg["text"].split()
        seg_start = seg["start"]
        seg_end = seg_start + seg.get("duration", 2.0)

        for i, w in enumerate(seg_words):
            # linearly interpolate timestamps within the segment
            ratio = i / max(len(seg_words) - 1, 1)
            words.append(w)
            word_times.append(seg_start + ratio * (seg_end - seg_start))

    # ── 2. Slide window ──────────────────────────────────────────
    chunks: list[Chunk] = []
    step = max(1, chunk_size - overlap)
    total = len(words)
    chunk_id = 0

    i = 0
    while i < total:
        end = min(i + chunk_size, total)
        chunk_words = words[i:end]
        start_t = word_times[i]
        end_t = word_times[end - 1]

        chunks.append(
            Chunk(
                id=chunk_id,
                text=" ".join(chunk_words),
                start_time=start_t,
                end_time=end_t,
                timestamp_str=_format_timestamp(start_t),
            )
        )
        chunk_id += 1
        i += step

    return chunks