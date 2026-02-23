"""
AssemblyAI STT provider — uses the official Python SDK.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

import assemblyai as aai

from app.config import settings
from app.dto.stt import STTRequestDTO, STTResultDTO
from app.services.stt.base import BaseSTTProvider

logger = logging.getLogger(__name__)


class AssemblyAIProvider(BaseSTTProvider):
    def __init__(self, api_key: str = ""):
        self._api_key = api_key or settings.ASSEMBLYAI_API_KEY

    async def transcribe(self, request: STTRequestDTO) -> STTResultDTO:
        """
        Transcribe audio bytes using AssemblyAI.
        Uses the synchronous SDK wrapped for async (AssemblyAI SDK is sync).
        """
        import asyncio
        import assemblyai as aai

        logger.info("AssemblyAI: transcribing request %s", request.request_id)

        # AssemblyAI uses global settings, so we must set it before the call
        original_key = aai.settings.api_key
        aai.settings.api_key = self._api_key

        try:
            result = await asyncio.to_thread(self._sync_transcribe, request)
            return result
        finally:
            aai.settings.api_key = original_key
        except Exception as e:
            logger.exception("AssemblyAI transcription failed")
            return STTResultDTO(
                request_id=request.request_id,
                provider="assemblyai",
                status="error",
                error_code="transcription_failed",
                error_message=str(e),
            )

    def _sync_transcribe(self, request: STTRequestDTO) -> STTResultDTO:
        config = aai.TranscriptionConfig(
            language_code=request.language if request.language != "auto" else None,
            language_detection=request.language == "auto",
        )

        transcriber = aai.Transcriber(config=config)

        # Write bytes to a temp file (SDK needs a file path or URL)
        if request.audio_bytes:
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
                f.write(request.audio_bytes)
                tmp_path = f.name

            transcript = transcriber.transcribe(tmp_path)
            Path(tmp_path).unlink(missing_ok=True)
        elif request.audio_url:
            transcript = transcriber.transcribe(request.audio_url)
        else:
            return STTResultDTO(
                request_id=request.request_id,
                provider="assemblyai",
                status="error",
                error_code="no_input",
                error_message="No audio_bytes or audio_url provided",
            )

        if transcript.status == aai.TranscriptStatus.error:
            return STTResultDTO(
                request_id=request.request_id,
                provider="assemblyai",
                provider_job_id=transcript.id,
                status="error",
                error_code="assemblyai_error",
                error_message=transcript.error or "Unknown error",
            )

        return STTResultDTO(
            request_id=request.request_id,
            provider="assemblyai",
            transcript_text=transcript.text or "",
            duration_seconds=transcript.audio_duration,
            provider_job_id=transcript.id,
            status="ok",
        )
