import os
import sys
from unittest.mock import Mock, patch

import pytest

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
)

from services.tts_service.processor import TTSProcessor


class TestTTSProcessor:
    @pytest.fixture
    def processor(self):
        return TTSProcessor(language="ru")

    def test_init_default(self):
        processor = TTSProcessor()
        assert processor.language == "ru"
        assert processor.slow is False

    def test_init_custom_language(self):
        processor = TTSProcessor(language="en", slow=True)
        assert processor.language == "en"
        assert processor.slow is True

    @patch("services.tts_service.processor.gTTS")
    @patch("services.tts_service.processor.os.makedirs")
    def test_generate_speech_success(self, mock_makedirs, mock_gtts, processor):
        mock_tts = Mock()
        mock_tts.save = Mock()
        mock_gtts.return_value = mock_tts

        with patch("os.path.exists", return_value=True):
            result = processor.generate_speech("Hello world", "/tmp/test.mp3")

            assert result == "/tmp/test.mp3"
            mock_gtts.assert_called_once()
            mock_tts.save.assert_called_once_with("/tmp/test.mp3")

    @patch("services.tts_service.processor.gTTS")
    def test_generate_speech_empty_text(self, mock_gtts, processor):
        with pytest.raises(ValueError, match="Text cannot be empty"):
            processor.generate_speech("")

    @patch("services.tts_service.processor.gTTS")
    @patch("services.tts_service.processor.os.makedirs")
    def test_generate_speech_async(self, mock_makedirs, mock_gtts, processor):
        mock_tts = Mock()
        mock_tts.save = Mock()
        mock_gtts.return_value = mock_tts

        with patch("os.path.exists", return_value=True):
            result = processor.generate_speech_async("Hello world")

            assert "audio_path" in result
            assert result["language"] == "ru"
            assert result["text_length"] == 11

    @patch("services.tts_service.processor.gTTS")
    def test_generate_speech_error(self, mock_gtts, processor):
        mock_gtts.side_effect = Exception("gTTS error")

        with pytest.raises(Exception, match="gTTS error"):
            processor.generate_speech("Hello world")
