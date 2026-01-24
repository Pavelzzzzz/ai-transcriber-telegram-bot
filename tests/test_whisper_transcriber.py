import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.whisper_transcriber import WhisperTranscriber


class TestWhisperTranscriber:
    """Тесты для класса WhisperTranscriber"""
    
    @pytest.fixture
    def mock_whisper_model(self):
        """Мок для Whisper модели"""
        mock_model = Mock()
        mock_model.transcribe.return_value = {
            "text": "Тестовый текст для транскрибации",
            "segments": [
                {
                    "audio": [0.1, 0.2, 0.3, 0.4, 0.5],
                    "text": "Тестовый сегмент"
                }
            ]
        }
        return mock_model
    
    @pytest.fixture
    def transcriber(self, mock_whisper_model):
        """Фикстура для создания экземпляра WhisperTranscriber с моком"""
        with patch('utils.whisper_transcriber.whisper.load_model', return_value=mock_whisper_model):
            with patch('utils.whisper_transcriber.torch.cuda.is_available', return_value=False):
                return WhisperTranscriber()
    
    def test_init(self, transcriber):
        """Тест инициализации"""
        assert transcriber.model_name == "base"
        assert transcriber.device == "cpu"
        assert transcriber.model is not None
    
    def test_init_with_custom_model(self, mock_whisper_model):
        """Тест инициализации с кастомной моделью"""
        with patch('utils.whisper_transcriber.whisper.load_model', return_value=mock_whisper_model):
            with patch('utils.whisper_transcriber.torch.cuda.is_available', return_value=True):
                transcriber = WhisperTranscriber("small")
                assert transcriber.model_name == "small"
                assert transcriber.device == "cuda"
    
    @pytest.mark.asyncio
    async def test_text_to_speech_success(self, transcriber):
        """Тест успешного преобразования текста в речь"""
        test_text = "Тестовый текст"
        user_id = 12345
        
        with patch('builtins.open', create=True) as mock_open:
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            with patch('os.path.exists', return_value=True):
                with patch('os.remove'):
                    with patch('numpy.array', return_value=[0.1, 0.2, 0.3]):
                        with patch('scipy.io.wavfile.write') as mock_write:
                            audio_path = await transcriber.text_to_speech(test_text, user_id)
                            
                            assert audio_path is not None
                            assert f"audio_{user_id}_" in audio_path
                            assert audio_path.endswith('.wav')
                            mock_write.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_text_to_speech_no_audio_data(self, transcriber):
        """Тест обработки отсутствия аудиоданных"""
        transcriber.model.transcribe.return_value = {
            "text": "Текст",
            "segments": []
        }
        
        test_text = "Тестовый текст"
        user_id = 12345
        
        with pytest.raises(ValueError, match="Нет аудиоданных для сохранения"):
            await transcriber.text_to_speech(test_text, user_id)
    
    @pytest.mark.asyncio
    async def test_text_to_speech_whisper_error(self, transcriber):
        """Тест обработки ошибки Whisper"""
        transcriber.model.transcribe.side_effect = Exception("Whisper error")
        
        test_text = "Тестовый текст"
        user_id = 12345
        
        with pytest.raises(Exception, match="Whisper error"):
            await transcriber.text_to_speech(test_text, user_id)
    
    @pytest.mark.asyncio
    async def test_transcribe_audio_success(self, transcriber):
        """Тест успешной транскрибации аудио"""
        audio_path = "/path/to/test/audio.wav"
        expected_text = "Распознанный текст"
        
        transcriber.model.transcribe.return_value = {
            "text": expected_text
        }
        
        result = await transcriber.transcribe_audio(audio_path)
        
        assert result == expected_text
        transcriber.model.transcribe.assert_called_once_with(audio_path, language="ru")
    
    @pytest.mark.asyncio
    async def test_transcribe_audio_error(self, transcriber):
        """Тест обработки ошибки транскрибации"""
        audio_path = "/path/to/test/audio.wav"
        transcriber.model.transcribe.side_effect = Exception("Audio error")
        
        with pytest.raises(Exception, match="Audio error"):
            await transcriber.transcribe_audio(audio_path)
    
    def test_load_model_error(self):
        """Тест обработки ошибки загрузки модели"""
        with patch('utils.whisper_transcriber.whisper.load_model', side_effect=Exception("Load error")):
            with pytest.raises(Exception, match="Load error"):
                WhisperTranscriber()
    
    @pytest.mark.asyncio
    async def test_text_to_speech_file_operations(self, transcriber):
        """Тест файловых операций в text_to_speech"""
        test_text = "Тестовый текст"
        user_id = 12345
        
        with patch('builtins.open', create=True) as mock_open:
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            with patch('os.path.exists', side_effect=lambda x: x.endswith('.txt')):
                with patch('os.remove') as mock_remove:
                    with patch('numpy.array', return_value=[0.1, 0.2, 0.3]):
                        with patch('scipy.io.wavfile.write'):
                            await transcriber.text_to_speech(test_text, user_id)
                            
                            mock_remove.assert_called()
    
    @pytest.mark.asyncio
    async def test_text_to_speech_audio_path_format(self, transcriber):
        """Тест формата пути к аудиофайлу"""
        test_text = "Тестовый текст"
        user_id = 12345
        
        with patch('builtins.open', create=True):
            with patch('os.path.exists', return_value=True):
                with patch('os.remove'):
                    with patch('numpy.array', return_value=[0.1, 0.2, 0.3]):
                        with patch('scipy.io.wavfile.write'):
                            audio_path = await transcriber.text_to_speech(test_text, user_id)
                            
                            assert audio_path.startswith("downloads/audio_")
                            assert str(user_id) in audio_path
                            assert audio_path.endswith(".wav")
                            
                            timestamp_pattern = "%Y%m%d_%H%M%S"
                            timestamp = datetime.now().strftime(timestamp_pattern)
                            assert timestamp in audio_path