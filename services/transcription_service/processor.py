import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.audio_preprocessor import AudioPreprocessingError, cleanup_audio, preprocess_audio
from utils.whisper_transcriber import WhisperTranscriber

logger = logging.getLogger(__name__)


class TranscriptionProcessor:
    def __init__(self, model_name: str = "small"):
        self.model_name = model_name
        self.transcriber = WhisperTranscriber(model_name)

    async def transcribe_audio(
        self, file_path: str, language: str = "ru", noise_reduction: bool = True
    ) -> dict:
        processed_path = None
        try:
            logger.info(f"Transcribing audio file: {file_path}, noise_reduction={noise_reduction}")

            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

            file_to_transcribe = file_path

            if noise_reduction:
                try:
                    processed_path = preprocess_audio(file_path, denoise=True)
                    file_to_transcribe = processed_path
                    logger.info(f"Audio preprocessed: {processed_path}")
                except AudioPreprocessingError as e:
                    logger.warning(f"Audio preprocessing failed, using original: {e}")
                    file_to_transcribe = file_path

            result = await self.transcriber.transcribe_audio(file_to_transcribe, language)

            return {
                "text": result.get("text", ""),
                "duration": result.get("duration", 0),
                "language": language,
                "file_path": file_path,
                "noise_reduction": noise_reduction,
            }
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise
        finally:
            if processed_path:
                cleanup_audio(processed_path)
