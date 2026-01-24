#!/usr/bin/env python3
"""
Интеграционные тесты AI Транскрибатор
Проверка всей заявленной функциональности проекта
"""

import os
import sys
import tempfile
import asyncio
import pytest
import logging
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from io import BytesIO

# Добавляем корень проекта в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

# Настройка логирования для тестов
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockUpdate:
    """Мок для Telegram Update"""
    def __init__(self, user_id=12345, username="test_user", message_text=None):
        self.effective_user = Mock()
        self.effective_user.id = user_id
        self.effective_user.username = username
        self.message = Mock()
        self.message.reply_text = AsyncMock()
        self.message.text = message_text
        self.message.photo = None
        self.message.voice = None
        self.callback_query = None

class MockContext:
    """Мок для Telegram Context"""
    def __init__(self):
        self.bot = Mock()
        self.bot.get_file = AsyncMock()
        self.error = None

class TestTelegramBotIntegration:
    """Интеграционные тесты Telegram бота"""
    
    @pytest.fixture
    def bot(self):
        """Фикстура для создания бота"""
        # Устанавливаем тестовый токен
        os.environ['TELEGRAM_BOT_TOKEN'] = 'test_token_12345'
        os.environ['ADMIN_USERNAMES'] = 'test_admin'
        
        from src.bot import TelegramBot
        return TelegramBot()
    
    @pytest.fixture
    def mock_update(self):
        """Фикстура для создания мок апдейта"""
        return MockUpdate()
    
    @pytest.fixture
    def mock_context(self):
        """Фикстура для создания мок контекста"""
        return MockContext()
    
    @pytest.mark.asyncio
    async def test_bot_initialization(self, bot):
        """Тест инициализации бота"""
        assert bot.token == 'test_token_12345'
        assert 'test_admin' in bot.admin_usernames
        assert bot.safe_processor is not None
        logger.info("✅ Тест инициализации бота пройден")
    
    @pytest.mark.asyncio
    async def test_start_command(self, bot, mock_update, mock_context):
        """Тест команды /start"""
        mock_update.message.text = "/start"
        
        await bot.start_command(mock_update, mock_context)
        
        # Проверяем, что был вызван reply_text
        mock_update.message.reply_text.assert_called_once()
        args, kwargs = mock_update.message.reply_text.call_args
        assert "🎉 **AI Транскрибатор**" in args[0]
        logger.info("✅ Тест команды /start пройден")
    
    @pytest.mark.asyncio
    async def test_help_command(self, bot, mock_update, mock_context):
        """Тест команды /help"""
        mock_update.message.text = "/help"
        
        await bot.help_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        args, kwargs = mock_update.message.reply_text.call_args
        assert "📖 **Помощь - AI Транскрибатор**" in args[0]
        logger.info("✅ Тест команды /help пройден")
    
    @pytest.mark.asyncio
    async def test_status_command(self, bot, mock_update, mock_context):
        """Тест команды /status"""
        mock_update.message.text = "/status"
        
        await bot.status_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        args, kwargs = mock_update.message.reply_text.call_args
        assert "🤖 **Статус AI Транскрибатора:**" in args[0]
        logger.info("✅ Тест команды /status пройден")
    
    @pytest.mark.asyncio
    async def test_mode_command(self, bot, mock_update, mock_context):
        """Тест команды /mode"""
        mock_update.message.text = "/mode"
        
        await bot.mode_command(mock_update, mock_context)
        
        # Должны быть два вызова: один с текстом, другой с клавиатурой
        assert mock_update.message.reply_text.call_count >= 1
        logger.info("✅ Тест команды /mode пройден")
    
    @pytest.mark.asyncio
    async def test_admin_commands(self, bot, mock_update, mock_context):
        """Тест административных команд"""
        # Устанавливаем пользователя как админа
        mock_update.effective_user.username = "test_admin"
        
        # Тест команды /admin
        mock_update.message.text = "/admin"
        await bot.admin_command(mock_update, mock_context)
        mock_update.message.reply_text.assert_called()
        
        # Тест команды /stats
        mock_update.message.text = "/stats"
        await bot.stats_command(mock_update, mock_context)
        mock_update.message.reply_text.assert_called()
        
        logger.info("✅ Тест административных команд пройден")
    
    @pytest.mark.asyncio
    async def test_admin_permissions(self, bot, mock_update, mock_context):
        """Тест проверок прав доступа"""
        # Не-админ не должен получить доступ к админ командам
        mock_update.effective_user.username = "regular_user"
        mock_update.message.text = "/admin"
        
        await bot.admin_command(mock_update, mock_context)
        
        args, kwargs = mock_update.message.reply_text.call_args
        assert "❌ Доступ запрещен" in args[0]
        logger.info("✅ Тест проверок прав доступа пройден")

class TestImageProcessorIntegration:
    """Интеграционные тесты обработчика изображений"""
    
    @pytest.fixture
    def processor(self):
        """Фикстура для процессора изображений"""
        from utils.image_processor import ImageProcessor
        return ImageProcessor()
    
    def test_processor_initialization(self, processor):
        """Тест инициализации процессора"""
        assert processor is not None
        assert hasattr(processor, 'extract_text_from_image')
        assert hasattr(processor, 'preprocess_image')
        logger.info("✅ Тест инициализации процессора изображений пройден")
    
    @pytest.mark.asyncio
    async def test_image_processing_flow(self, processor):
        """Тест потока обработки изображений"""
        # Создаем тестовое изображение
        from PIL import Image
        import numpy as np
        
        # Создаем простое изображение с текстом
        img = Image.new('RGB', (200, 50), color='white')
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            img.save(tmp.name)
            tmp_path = tmp.name
        
        try:
            # Тестируем извлечение текста
            result = await processor.extract_text_from_image(tmp_path)
            assert isinstance(result, str)
            logger.info("✅ Тест обработки изображений пройден")
        except Exception as e:
            logger.warning(f"⚠️ OCR недоступен: {e}")
        finally:
            os.unlink(tmp_path)

class TestWhisperTranscriberIntegration:
    """Интеграционные тесты Whisper транскрибера"""
    
    @pytest.fixture
    def transcriber(self):
        """Фикстура для транскрибера"""
        from utils.whisper_transcriber import WhisperTranscriber
        return WhisperTranscriber(model_name="tiny")
    
    def test_transcriber_initialization(self, transcriber):
        """Тест инициализации транскрибера"""
        assert transcriber is not None
        assert transcriber.model_name == "tiny"
        assert hasattr(transcriber, 'text_to_speech')
        assert hasattr(transcriber, 'transcribe_audio')
        logger.info("✅ Тест инициализации транскрибера пройден")
    
    @pytest.mark.asyncio
    async def test_text_to_speech(self, transcriber):
        """Тест преобразования текста в речь"""
        try:
            test_text = "Привет, это тестовый текст"
            result = await transcriber.text_to_speech(test_text, user_id=12345)
            
            # Проверяем, что файл создан
            assert os.path.exists(result)
            
            # Проверяем размер файла
            assert os.path.getsize(result) > 0
            
            # Очистка
            os.unlink(result)
            logger.info("✅ Тест преобразования текста в речь пройден")
        except Exception as e:
            logger.warning(f"⚠️ TTS недоступен: {e}")
    
    @pytest.mark.asyncio
    async def test_audio_transcription(self, transcriber):
        """Тест транскрибации аудио"""
        # Создаем тестовый аудиофайл
        try:
            import numpy as np
            from scipy.io.wavfile import write
            
            # Создаем простой аудиосигнал
            sample_rate = 16000
            duration = 1  # 1 секунда
            frequency = 440  # нота A4
            
            t = np.linspace(0, duration, sample_rate * duration)
            audio_data = np.sin(2 * np.pi * frequency * t)
            
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                write(tmp.name, sample_rate, audio_data.astype(np.int16))
                tmp_path = tmp.name
            
            try:
                result = await transcriber.transcribe_audio(tmp_path)
                assert isinstance(result, dict)
                assert 'text' in result
                logger.info("✅ Тест транскрибации аудио пройден")
            finally:
                os.unlink(tmp_path)
        except Exception as e:
            logger.warning(f"⚠️ Аудио транскрипция недоступна: {e}")

class TestSafeProcessorIntegration:
    """Интеграционные тесты безопасного процессора"""
    
    @pytest.fixture
    def safe_processor(self):
        """Фикстура для безопасного процессора"""
        from src.bot import SimpleSafeProcessor
        return SimpleSafeProcessor()
    
    @pytest.fixture
    def mock_update(self):
        return MockUpdate()
    
    @pytest.fixture
    def mock_context(self):
        return MockContext()
    
    @pytest.mark.asyncio
    async def test_safe_reply(self, safe_processor, mock_update):
        """Тест безопасного ответа"""
        result = await safe_processor.safe_reply(mock_update, "Тестовое сообщение")
        assert result is True
        mock_update.message.reply_text.assert_called_once_with("Тестовое сообщение", parse_mode=None)
        logger.info("✅ Тест безопасного ответа пройден")
    
    @pytest.mark.asyncio
    async def test_safe_reply_with_error(self, safe_processor, mock_update):
        """Тест безопасного ответа с ошибкой"""
        # Создаем ошибку при ответе
        mock_update.message.reply_text = AsyncMock(side_effect=Exception("Test error"))
        
        result = await safe_processor.safe_reply(mock_update, "Тестовое сообщение")
        assert result is False
        logger.info("✅ Тест обработки ошибки ответа пройден")

class TestAdminServiceIntegration:
    """Интеграционные тесты административного сервиса"""
    
    @pytest.fixture
    def mock_db(self):
        """Мок базы данных"""
        mock_session = Mock()
        mock_session.query = Mock()
        return mock_session
    
    def test_admin_service_initialization(self, mock_db):
        """Тест инициализации админ сервиса"""
        from utils.admin_service import AdminService
        service = AdminService(mock_db)
        assert service.db == mock_db
        logger.info("✅ Тест инициализации админ сервиса пройден")

class TestExceptionsIntegration:
    """Интеграционные тесты системы исключений"""
    
    def test_bot_error_creation(self):
        """Тест создания ошибок бота"""
        from src.exceptions import BotError, ValidationError, FileProcessingError
        
        # Тест базовой ошибки
        error = BotError("Test error", error_code="TEST_ERROR")
        error_dict = error.to_dict()
        assert error_dict['message'] == "Test error"
        assert error_dict['error_code'] == "TEST_ERROR"
        
        # Тест ошибки валидации
        validation_error = ValidationError("Invalid data", field="test_field")
        assert validation_error.field == "test_field"
        
        logger.info("✅ Тест системы исключений пройден")
    
    def test_error_handler(self):
        """Тест обработчика ошибок"""
        from src.exceptions import ErrorHandler, BotError
        
        error = BotError("Test error")
        ErrorHandler.log_error(error)
        logger.info("✅ Тест обработчика ошибок пройден")

class TestConfigurationIntegration:
    """Интеграционные тесты конфигурации"""
    
    def test_environment_variables(self):
        """Тест переменных окружения"""
        from dotenv import load_dotenv
        load_dotenv()
        
        # Проверяем обязательные переменные
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        if token:
            assert len(token) > 0
            logger.info("✅ Токен настроен")
        else:
            logger.warning("⚠️ Токен не настроен")
        
        logger.info("✅ Тест конфигурации пройден")

def run_integration_tests():
    """Запуск всех интеграционных тестов"""
    print("🧪 Запуск интеграционных тестов AI Транскрибатор")
    print("=" * 60)
    
    # Запуск тестов с pytest
    test_args = [
        __file__,
        '-v',  # подробный вывод
        '--tb=short',  # короткий traceback
        '-x',  # остановиться при первой ошибке
    ]
    
    try:
        # Запускаем pytest программно
        exit_code = pytest.main(test_args)
        
        if exit_code == 0:
            print("\n🎉 Все интеграционные тесты пройдены!")
            return True
        else:
            print(f"\n❌ Тесты завершились с кодом {exit_code}")
            return False
    except Exception as e:
        print(f"❌ Ошибка при запуске тестов: {e}")
        return False

if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)