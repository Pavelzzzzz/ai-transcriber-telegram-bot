import asyncio
import os
import sys
from unittest.mock import AsyncMock, Mock, patch

import pytest

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
)

from services.common.schemas import ResultMessage, TaskMessage, TaskStatus, TaskType


class TestTranscriptionServiceIntegration:
    """Integration tests for transcription service"""

    @pytest.mark.integration
    def test_transcribe_task_message_creation(self):
        """Test creating transcription task message"""
        task = TaskMessage(
            task_id="transcribe-test-123",
            task_type=TaskType.TRANSCRIBE,
            user_id=12345,
            chat_id=67890,
            file_path="/test/audio.ogg",
            metadata={"language": "ru"},
        )

        assert task.task_type == TaskType.TRANSCRIBE
        assert task.file_path == "/test/audio.ogg"
        assert task.metadata["language"] == "ru"

    @pytest.mark.integration
    def test_transcribe_result_message_creation(self):
        """Test creating transcription result message"""
        result = ResultMessage(
            task_id="transcribe-test-123",
            status=TaskStatus.SUCCESS,
            result_type="transcription",
            result_data={"text": "Transcribed audio text", "language": "ru", "duration": 10.5},
        )

        assert result.status == TaskStatus.SUCCESS
        assert result.result_data["text"] == "Transcribed audio text"

    @pytest.mark.integration
    def test_transcribe_result_with_error(self):
        """Test transcription result with error"""
        result = ResultMessage(
            task_id="transcribe-test-456",
            status=TaskStatus.FAILED,
            result_type="transcription",
            result_data={},
            error="Audio file corrupted",
        )

        assert result.status == TaskStatus.FAILED
        assert result.error == "Audio file corrupted"


class TestTranscriptionProcessor:
    """Test transcription processor logic"""

    @pytest.mark.integration
    def test_processor_init(self):
        """Test transcription processor initialization"""
        from services.transcription_service.processor import TranscriptionProcessor

        processor = TranscriptionProcessor()
        assert processor is not None

    @pytest.mark.integration
    @patch("services.transcription_service.processor.WhisperTranscriber")
    def test_transcribe_audio_mock(self, mock_transcriber_class):
        """Test audio transcription with mock"""
        from services.transcription_service.processor import TranscriptionProcessor

        mock_transcriber = Mock()
        mock_transcriber.transcribe_audio = AsyncMock(
            return_value={"text": "Transcribed text", "language": "ru"}
        )
        mock_transcriber_class.return_value = mock_transcriber

        processor = TranscriptionProcessor()
        result = asyncio.get_event_loop().run_until_complete(processor.transcribe("/test.ogg"))

        assert result["text"] == "Transcribed text"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
