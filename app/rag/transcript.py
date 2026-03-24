"""
app/rag/transcript.py
─────────────────────
Fetches and normalises YouTube transcripts.
Responsible for a single concern: getting raw text + timestamps from a video.
"""

import re
import urllib.request
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional

from groq import Groq
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from yt_dlp import YoutubeDL

from app.core.config import get_settings
from app.core.exceptions import InvalidYouTubeURLError, TranscriptUnavailableError
from app.core.logging import get_logger

logger = get_logger(__name__)

# Regex patterns for extracting YouTube video IDs
_YT_PATTERNS: list[str] = [
    r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})",
    r"youtube\.com/shorts/([a-zA-Z0-9_-]{11})",
    r"youtube\.com/live/([a-zA-Z0-9_-]{11})",
]


def extract_video_id(url: str) -> str:
    """
    Parse a YouTube URL and return the 11-character video ID.
    Raises InvalidYouTubeURLError if no ID can be found.
    """
    for pattern in _YT_PATTERNS:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise InvalidYouTubeURLError()


def fetch_transcript(video_id: str) -> list[dict]:
    """
    Fetch the transcript for a YouTube video.

    Returns a list of segment dicts:
        [{"text": str, "start": float, "duration": float}, ...]

    Raises TranscriptUnavailableError on failure.
    """
    settings = get_settings()

    try:
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)

        # Prefer English captions first: generated, then manual.
        try:
            transcript = transcript_list.find_generated_transcript(["en"])
        except NoTranscriptFound:
            try:
                transcript = transcript_list.find_manually_created_transcript(["en"])
            except NoTranscriptFound:
                # Fallback to any available transcript language.
                available = list(transcript_list)
                if not available:
                    raise TranscriptUnavailableError(video_id, "no transcript found")
                transcript = available[0]

        selected_lang = transcript.language_code

        # Optional translation step for non-English transcripts.
        if (
            settings.transcript_auto_translate_to_en
            and selected_lang != "en"
            and getattr(transcript, "is_translatable", False)
        ):
            try:
                transcript = transcript.translate("en")
            except Exception as e:
                logger.warning(
                    f"Could not auto-translate transcript for {video_id} from "
                    f"{selected_lang} to en: {e}"
                )

        fetched = transcript.fetch()
        segments = [
            {"text": s.text, "start": s.start, "duration": s.duration}
            for s in fetched
        ]
        logger.info(
            f"Fetched transcript for {video_id}: {len(segments)} segments "
            f"(selected_lang={selected_lang}, final_lang={transcript.language_code})"
        )
        return segments
    except Exception as e:
        logger.warning(f"Transcript API failed for {video_id}: {e}")

        if settings.transcript_whisper_fallback_enabled:
            try:
                return _transcribe_video_with_whisper(video_id)
            except Exception as whisper_error:
                raise TranscriptUnavailableError(
                    video_id,
                    f"{e}. Whisper fallback failed: {whisper_error}",
                )

        raise TranscriptUnavailableError(video_id, str(e))


def _transcribe_video_with_whisper(video_id: str) -> list[dict]:
    """Download video audio and transcribe with Groq Whisper as a fallback."""
    settings = get_settings()
    client = Groq(api_key=settings.groq_api_key)
    video_url = f"https://www.youtube.com/watch?v={video_id}"

    with TemporaryDirectory(prefix="videomind-whisper-") as temp_dir:
        output_template = str(Path(temp_dir) / "audio.%(ext)s")
        ydl_opts = {
            "format": "bestaudio[ext=m4a]/bestaudio/best",
            "outtmpl": output_template,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            downloaded_file = Path(ydl.prepare_filename(info))

        logger.info(
            f"Running Whisper fallback for {video_id} using model "
            f"{settings.transcript_whisper_model}"
        )

        with downloaded_file.open("rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model=settings.transcript_whisper_model,
                file=(downloaded_file.name, audio_file.read()),
                response_format="verbose_json",
            )

    raw_segments = getattr(transcript, "segments", None)
    if raw_segments is None and isinstance(transcript, dict):
        raw_segments = transcript.get("segments")

    if raw_segments:
        segments = []
        for seg in raw_segments:
            text = getattr(seg, "text", None)
            if text is None and isinstance(seg, dict):
                text = seg.get("text", "")

            start = getattr(seg, "start", None)
            if start is None and isinstance(seg, dict):
                start = seg.get("start", 0.0)

            end = getattr(seg, "end", None)
            if end is None and isinstance(seg, dict):
                end = seg.get("end", start)

            start = float(start or 0.0)
            end = float(end or start)
            duration = max(0.0, end - start)

            if text:
                segments.append({"text": str(text), "start": start, "duration": duration})

        if segments:
            logger.info(f"Whisper fallback succeeded for {video_id}: {len(segments)} segments")
            return segments

    text = getattr(transcript, "text", None)
    if text is None and isinstance(transcript, dict):
        text = transcript.get("text")

    if not text:
        raise RuntimeError("Whisper returned no transcript text")

    # Fallback shape compatible with chunker when detailed segments are unavailable.
    return [{"text": str(text), "start": 0.0, "duration": 0.0}]


def fetch_video_title(video_id: str) -> str:
    """
    Attempt to resolve the video title via YouTube oEmbed (no API key needed).
    Falls back gracefully to a generic title.
    """
    try:
        oembed_url = (
            f"https://www.youtube.com/oembed"
            f"?url=https://www.youtube.com/watch?v={video_id}&format=json"
        )
        with urllib.request.urlopen(oembed_url, timeout=6) as resp:
            data = json.loads(resp.read())
            return data.get("title", f"Video ({video_id})")
    except Exception:
        logger.warning(f"Could not resolve title for {video_id}, using fallback")
        return f"YouTube Video ({video_id})"