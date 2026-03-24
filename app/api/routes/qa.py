"""
app/api/routes/qa.py
─────────────────────
Routes for the question-answering RAG pipeline.
"""

from fastapi import APIRouter, Depends

from app.api.dependencies import get_video_service, get_llm_service
from app.api.schemas import AskQuestionRequest, AskQuestionResponse
from app.services.video import VideoService
from app.services.llm import LLMService

router = APIRouter(prefix="/qa", tags=["Q&A"])


@router.post(
    "/ask",
    response_model=AskQuestionResponse,
    summary="Ask a question about an indexed video",
)
async def ask_question(
    body: AskQuestionRequest,
    video_svc: VideoService = Depends(get_video_service),
    llm_svc: LLMService = Depends(get_llm_service),
):
    """
    RAG pipeline:
      1. Retrieve top-k relevant chunks from the video transcript
      2. Send chunks + question to Groq LLM
      3. Return the answer with source timestamps
    """
    chunks, sources, title = video_svc.retrieve_and_answer_context(
        video_id=body.video_id,
        question=body.question,
    )

    answer = llm_svc.answer(
        question=body.question,
        chunks=chunks,
        video_title=title,
    )

    return AskQuestionResponse(
        video_id=body.video_id,
        question=body.question,
        answer=answer,
        sources=sources,
    )