"""
app/api/schemas.py
──────────────────
Pydantic request / response models for all API endpoints.
Keeping schemas separate from route logic makes validation
and documentation easy to maintain and extend.
"""

from datetime import datetime
from pydantic import BaseModel, HttpUrl, Field


# ── Request models ────────────────────────────────────────────────


class ProcessVideoRequest(BaseModel):
    url: str = Field(
        ...,
        description="YouTube video URL",
        examples=["https://www.youtube.com/watch?v=dQw4w9WgXcQ"],
    )


class AskQuestionRequest(BaseModel):
    video_id: str = Field(..., description="11-character YouTube video ID")
    question: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="Natural-language question about the video",
    )


# ── Response models ───────────────────────────────────────────────


class ProcessVideoResponse(BaseModel):
    video_id: str
    title: str
    chunk_count: int
    transcript_length: int
    indexed_at: datetime
    cached: bool = False


class AskQuestionResponse(BaseModel):
    video_id: str
    question: str
    answer: str
    sources: list[str] = Field(
        description="Timestamp references of the chunks used for the answer"
    )


class VideoSummary(BaseModel):
    video_id: str
    title: str
    url: str
    chunk_count: int
    transcript_length: int
    indexed_at: datetime


class DeleteResponse(BaseModel):
    message: str
    video_id: str


class HealthResponse(BaseModel):
    status: str
    version: str
    videos_indexed: int


class ChatMessage(BaseModel):
    role: str
    text: str
    sources: list[str] | None = None
    time: str | None = None