"""
app/services/llm.py
────────────────────
Thin wrapper around the Groq SDK.
All LLM concerns (prompt building, model calls, retries) live here.
"""

from groq import Groq, APIStatusError, APIConnectionError

from app.core.config import get_settings
from app.core.exceptions import LLMError
from app.core.logging import get_logger
from app.rag.chunker import Chunk

logger = get_logger(__name__)

_SYSTEM_TEMPLATE = """\
You are VideoMind, an expert AI assistant that answers questions based on YouTube video transcripts.

Video Title: {title}

Instructions:
- Answer using ONLY the provided transcript context below
- If the answer is not in the context, say: "This specific information isn't covered in the video"
- Reference timestamps naturally when helpful (e.g., "Around 2:30, the speaker explains...")
- Be clear, concise, and conversational
- Use markdown formatting (bold, lists, headers) when it improves readability
- Do not fabricate information not present in the transcript
"""

_USER_TEMPLATE = """\
Transcript Context (from video "{title}"):
────────────────────────────────────────
{context}
────────────────────────────────────────

Question: {question}

Answer:"""


def _build_context(chunks: list[Chunk]) -> str:
    """Format retrieved chunks into a numbered context block."""
    lines = []
    for i, chunk in enumerate(chunks, 1):
        lines.append(f"[{i}] [{chunk.timestamp_str}] {chunk.text}")
    return "\n\n".join(lines)


class LLMService:
    """
    Wraps Groq completions API.
    Instantiated once at app startup and shared via dependency injection.
    """

    def __init__(self):
        settings = get_settings()
        self._client = Groq(api_key=settings.groq_api_key)
        self._model = settings.groq_model
        logger.info(f"LLMService initialised — model: {self._model}")

    def answer(
        self,
        question: str,
        chunks: list[Chunk],
        video_title: str,
        max_tokens: int = 1024,
        temperature: float = 0.3,
    ) -> str:
        """
        Given a question and retrieved chunks, return the LLM's answer.
        Raises LLMError on API failures.
        """
        context = _build_context(chunks)
        system_msg = _SYSTEM_TEMPLATE.format(title=video_title)
        user_msg = _USER_TEMPLATE.format(
            title=video_title,
            context=context,
            question=question,
        )

        logger.debug(
            f"LLM call — model={self._model}, "
            f"chunks={len(chunks)}, context_len={len(context)}"
        )

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user",   "content": user_msg},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            answer = response.choices[0].message.content
            logger.debug(f"LLM response: {len(answer)} chars")
            return answer

        except APIStatusError as e:
            logger.error(f"Groq API status error: {e.status_code} — {e.message}")
            raise LLMError(f"Groq returned status {e.status_code}: {e.message}")
        except APIConnectionError as e:
            logger.error(f"Groq connection error: {e}")
            raise LLMError("Could not connect to Groq API. Check your network.")
        except Exception as e:
            logger.error(f"Unexpected LLM error: {e}")
            raise LLMError(str(e))