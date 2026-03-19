import logging
import os

from utils.whisper_transcriber import WhisperTranscriber

logger = logging.getLogger(__name__)


class TranscriptionProcessor:
    def __init__(self, model_name: str = "base"):
        self.model_name = model_name
        self.transcriber = WhisperTranscriber(model_name)

    async def transcribe_audio(self, file_path: str, language: str = "ru") -> dict:
        try:
            logger.info(f"Transcribing audio file: {file_path}")

            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

            result = await self.transcriber.transcribe_audio(file_path, language)

            return {
                "text": result.get("text", ""),
                "duration": result.get("duration", 0),
                "language": language,
                "file_path": file_path,
            }
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise
