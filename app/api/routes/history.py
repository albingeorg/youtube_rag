from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any

from app.api.dependencies import get_vector_store
from app.rag import history as history_service
from app.api.schemas import ChatMessage

router = APIRouter()

@router.get("/{video_id}", response_model=List[ChatMessage])
def get_video_history(video_id: str):
    """
    Retrieves the chat history for a specific video.
    """
    try:
        return history_service.get_history(video_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{video_id}")
def add_message(video_id: str, message: ChatMessage):
    """
    Adds a message to the chat history of a specific video.
    """
    try:
        history_service.add_message_to_history(
            video_id, message.role, message.text, message.sources, message.time
        )
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{video_id}")
def clear_video_history(video_id: str):
    """
    Clears the chat history for a specific video.
    """
    try:
        history_service.clear_history(video_id)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
