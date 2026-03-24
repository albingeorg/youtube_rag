"""Application-specific typed HTTP exceptions."""

from fastapi import HTTPException, status


class AppHTTPException(HTTPException):
	"""Base typed HTTP exception for API errors."""

	def __init__(self, status_code: int, detail: str):
		super().__init__(status_code=status_code, detail=detail)


class InvalidYouTubeURLError(AppHTTPException):
	def __init__(self):
		super().__init__(
			status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
			detail="Invalid YouTube URL. Provide a valid youtube.com or youtu.be link.",
		)


class TranscriptUnavailableError(AppHTTPException):
	def __init__(self, video_id: str, reason: str):
		super().__init__(
			status_code=status.HTTP_424_FAILED_DEPENDENCY,
			detail=f"Transcript unavailable for video '{video_id}': {reason}.",
		)


class VideoNotFoundError(AppHTTPException):
	def __init__(self, video_id: str):
		super().__init__(
			status_code=status.HTTP_404_NOT_FOUND,
			detail=f"Video '{video_id}' is not indexed.",
		)


class LLMError(AppHTTPException):
	def __init__(self, message: str):
		super().__init__(
			status_code=status.HTTP_502_BAD_GATEWAY,
			detail=f"LLM request failed: {message}",
		)
