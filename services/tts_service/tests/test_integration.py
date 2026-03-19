import os
import sys
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
)

from services.common.schemas import ResultMessage, TaskMessage, TaskStatus, TaskType


class TestTTSServiceIntegration:
    """Integration tests for TTS service"""

    @pytest.mark.integration
    def test_tts_task_message_creation(self):
        """Test creating TTS task message"""
        task = TaskMessage(
            task_id="tts-test-123",
            task_type=TaskType.TRANSCRIBE,
            user_id=12345,
            chat_id=67890,
            timestamp=datetime.now(),
            file_path="Hello world",
            metadata={"language": "ru"},
        )

        assert task.task_type == TaskType.TRANSCRIBE
        assert task.file_path == "Hello world"

    @pytest.mark.integration
    def test_tts_result_message_creation(self):
        """Test creating TTS result message"""
        result = ResultMessage(
            task_id="tts-test-123",
            status=TaskStatus.SUCCESS,
            result_type="audio",
            result_data={"file_path": "/test/audio.mp3", "language": "ru"},
        )

        assert result.status == TaskStatus.SUCCESS
        assert "file_path" in result.result_data

    @pytest.mark.integration
    def test_tts_result_with_error(self):
        """Test TTS result with error"""
        result = ResultMessage(
            task_id="tts-test-456",
            status=TaskStatus.FAILED,
            result_type="audio",
            result_data={},
            error="Text too long",
        )

        assert result.status == TaskStatus.FAILED
        assert result.error == "Text too long"


class TestTTSProcessor:
    """Test TTS processor logic"""

    @pytest.mark.integration
    def test_processor_init(self):
        """Test TTS processor initialization"""
        from services.tts_service.processor import TTSProcessor

        processor = TTSProcessor()
        assert processor is not None

    @pytest.mark.integration
    @patch("services.tts_service.processor.gTTS")
    def test_text_to_speech_mock(self, mock_gtts_class):
        """Test text to speech with mock"""
        from services.tts_service.processor import TTSProcessor

        mock_gtts = Mock()
        mock_gtts.save = Mock()
        mock_gtts_class.return_value = mock_gtts

        processor = TTSProcessor()

        os.makedirs("/tmp", exist_ok=True)

        result = processor.generate_speech_async("Hello world", "/tmp/test.mp3")

        assert "audio_path" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
