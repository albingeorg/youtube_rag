from typing import List, Dict, Any
from app.rag.store import vector_store

def add_message_to_history(video_id: str, role: str, text: str, sources: List[str] = None, time: str = None):
    """Adds a message to the chat history for a specific video."""
    history = vector_store.get_chat_history(video_id)
    message = {"role": role, "text": text, "time": time}
    if sources:
        message["sources"] = sources
    history.append(message)
    vector_store.set_chat_history(video_id, history)

def get_history(video_id: str) -> List[Dict[str, Any]]:
    """Retrieves the chat history for a specific video."""
    return vector_store.get_chat_history(video_id)

def clear_history(video_id: str):
    """Clears the chat history for a specific video."""
    vector_store.delete_chat_history(video_id)
