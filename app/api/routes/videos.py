"""
app/api/routes/videos.py
─────────────────────────
Routes for video processing and management.
"""

from fastapi import APIRouter, Depends

from app.api.dependencies import get_video_service, get_store
from app.api.schemas import (
    ProcessVideoRequest,
    ProcessVideoResponse,
    VideoSummary,
    DeleteResponse,
)
from app.core.exceptions import VideoNotFoundError
from app.rag.store import VideoStore
from app.services.video import VideoService

router = APIRouter(prefix="/videos", tags=["Videos"])


@router.post(
    "/process",
    response_model=ProcessVideoResponse,
    summary="Process & index a YouTube video",
)
async def process_video(
    body: ProcessVideoRequest,
    svc: VideoService = Depends(get_video_service),
    store: VideoStore = Depends(get_store),
):
    """
    Fetch transcript, chunk, index, and store a YouTube video.
    Returns immediately if the video has already been processed (cache hit).
    """
    was_cached = store.exists_by_url_or_id(body.url)
    entry = svc.process(url=body.url)

    return ProcessVideoResponse(
        video_id=entry.video_id,
        title=entry.title,
        chunk_count=entry.chunk_count,
        transcript_length=entry.transcript_length,
        indexed_at=entry.indexed_at,
        cached=was_cached,
    )


@router.get(
    "/",
    response_model=list[VideoSummary],
    summary="List all indexed videos",
)
async def list_videos(store: VideoStore = Depends(get_store)):
    """Return all currently indexed videos."""
    return store.list_all()


@router.delete(
    "/{video_id}",
    response_model=DeleteResponse,
    summary="Remove an indexed video",
)
async def delete_video(
    video_id: str,
    store: VideoStore = Depends(get_store),
):
    """Delete a video from the index by its ID."""
    if not store.delete(video_id):
        raise VideoNotFoundError(video_id)
    return DeleteResponse(message="Video removed successfully.", video_id=video_id)