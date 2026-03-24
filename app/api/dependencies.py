"""FastAPI dependency providers for shared app services."""

from fastapi import Request

from app.rag.store import VideoStore
from app.services.llm import LLMService
from app.services.video import VideoService


def get_store(request: Request) -> VideoStore:
	return request.app.state.store


def get_llm_service(request: Request) -> LLMService:
	return request.app.state.llm_service


def get_video_service(request: Request) -> VideoService:
	return request.app.state.video_service
