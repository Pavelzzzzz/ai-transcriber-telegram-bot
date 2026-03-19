import os
import sys
from unittest.mock import AsyncMock, Mock, patch

import pytest

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
)

from services.transcription_service.processor import TranscriptionProcessor


class TestTranscriptionProcessor:
    @pytest.fixture
    def mock_whisper_transcriber(self):
        with patch("services.transcription_service.processor.WhisperTranscriber") as mock:
            instance = Mock()
            instance.transcribe_audio = AsyncMock(
                return_value={"text": "Transcribed text", "duration": 10.5, "language": "ru"}
            )
            mock.return_value = instance
            yield instance

    @pytest.fixture
    def processor(self):
        return TranscriptionProcessor("base")

    @pytest.mark.asyncio
    async def test_transcribe_audio_success(self, processor, mock_whisper_transcriber):
        result = await processor.transcribe_audio("/path/to/audio.ogg", "ru")

        assert result["text"] == "Transcribed text"
        assert result["duration"] == 10.5
        assert result["language"] == "ru"

    @pytest.mark.asyncio
    async def test_transcribe_audio_file_not_found(self, processor):
        with patch("services.transcription_service.processor.WhisperTranscriber") as mock:
            instance = Mock()
            instance.transcribe_audio = AsyncMock(side_effect=FileNotFoundError("File not found"))
            mock.return_value = instance

            with pytest.raises(FileNotFoundError):
                await processor.transcribe_audio("/nonexistent/audio.ogg")

    @pytest.mark.asyncio
    async def test_transcribe_audio_error(self, processor):
        with patch("services.transcription_service.processor.WhisperTranscriber") as mock:
            instance = Mock()
            instance.transcribe_audio = AsyncMock(side_effect=Exception("Transcription error"))
            mock.return_value = instance

            with pytest.raises(Exception, match="Transcription error"):
                await processor.transcribe_audio("/path/to/audio.ogg")

    @pytest.mark.asyncio
    async def test_transcribe_audio_with_custom_language(self, processor, mock_whisper_transcriber):
        result = await processor.transcribe_audio("/path/to/audio.ogg", "en")

        assert result["language"] == "en"
        mock_whisper_transcriber.transcribe_audio.assert_called_once_with(
            "/path/to/audio.ogg", "en"
        )

    def test_init_with_custom_model(self):
        with patch("services.transcription_service.processor.WhisperTranscriber"):
            processor = TranscriptionProcessor("small")
            assert processor.model_name == "small"
