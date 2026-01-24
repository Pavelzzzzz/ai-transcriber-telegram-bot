import pytest
import os
from unittest.mock import Mock, patch, MagicMock, AsyncMock

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.bot import TelegramBot


class TestTelegramBot:
    """Тесты для класса TelegramBot"""
    
    @pytest.fixture
    def mock_transcriber(self):
        """Мок для WhisperTranscriber"""
        mock_transcriber = Mock()
        mock_transcriber.text_to_speech = AsyncMock(return_value="/path/to/audio.wav")
        return mock_transcriber
    
    @pytest.fixture
    def mock_image_processor(self):
        """Мок для ImageProcessor"""
        mock_processor = Mock()
        mock_processor.extract_text_from_image = AsyncMock(return_value="Тестовый текст")
        return mock_processor
    
    @pytest.fixture
    def bot(self, mock_transcriber, mock_image_processor):
        """Фикстура для создания экземпляра TelegramBot с моками"""
        with patch.dict(os.environ, {'TELEGRAM_BOT_TOKEN': 'test_token'}):
            with patch('src.bot.WhisperTranscriber', return_value=mock_transcriber):
                with patch('src.bot.ImageProcessor', return_value=mock_image_processor):
                    with patch('src.bot.create_tables'):
                        with patch('database.models.get_db') as mock_get_db:
                            mock_get_db.return_value = Mock()
                            bot = TelegramBot()
                            bot.admin_service = Mock()
                            bot.admin_service.is_admin = Mock(return_value=False)
                            bot.admin_service.create_or_update_user = Mock(return_value=Mock(is_admin=Mock(return_value=False)))
                            bot.admin_service.log_transcription = Mock()
                            return bot
    
    @pytest.fixture
    def mock_update(self):
        """Мок для Update"""
        mock_update = Mock()
        mock_update.message = Mock()
        mock_update.message.reply_text = AsyncMock()
        mock_update.effective_user = Mock()
        mock_update.effective_user.id = 12345
        return mock_update
    
    @pytest.fixture
    def mock_context(self):
        """Мок для ContextTypes.DEFAULT_TYPE"""
        mock_context = Mock()
        mock_context.bot = Mock()
        mock_context.bot.get_file = AsyncMock()
        mock_context.bot.get_file.return_value.download_to_drive = AsyncMock()
        mock_context.bot.set_my_commands = AsyncMock()
        return mock_context
    
    def test_init_success(self, mock_transcriber, mock_image_processor):
        """Тест успешной инициализации"""
        with patch.dict(os.environ, {'TELEGRAM_BOT_TOKEN': 'test_token'}):
            with patch('src.bot.WhisperTranscriber', return_value=mock_transcriber):
                with patch('src.bot.ImageProcessor', return_value=mock_image_processor):
                    bot = TelegramBot()
                    assert bot.token == 'test_token'
                    assert bot.transcriber == mock_transcriber
                    assert bot.image_processor == mock_image_processor
    
    def test_init_no_token(self):
        """Тест инициализации без токена"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN не найден"):
                TelegramBot()
    
    @pytest.mark.asyncio
    async def test_start_command(self, bot, mock_update, mock_context):
        """Тест команды /start"""
        await bot.start_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0]
        message = call_args[0]
        
        assert "AI Транскрибатор" in message
        assert "/start" in message
        assert "/help" in message
        assert "/status" in message
    
    @pytest.mark.asyncio
    async def test_help_command(self, bot, mock_update, mock_context):
        """Тест команды /help"""
        await bot.help_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0]
        message = call_args[0]
        
        assert "Помощь - AI Транскрибатор" in message
        assert "OCR распознавание текста на изображениях" in message
        assert "Преобразование текста в аудио (TTS)" in message
    
    @pytest.mark.asyncio
    async def test_status_command(self, bot, mock_update, mock_context):
        """Тест команды /status"""
        await bot.status_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0]
        message = call_args[0]
        
        assert "Статус бота" in message
        assert "Бот активен" in message
        assert "Whisper: загружен" in message
    
    @pytest.mark.asyncio
    async def test_handle_photo_success(self, bot, mock_update, mock_context):
        """Тест успешной обработки фото"""
        mock_photo = Mock()
        mock_photo.file_id = "test_file_id"
        mock_update.message.photo = [mock_photo]
        
        await bot.handle_photo(mock_update, mock_context)
        
        assert mock_update.message.reply_text.call_count >= 2
        
        calls = [call.args[0] for call in mock_update.message.reply_text.call_args_list]
        assert "Обрабатываю изображение" in calls[0]
        assert "Текст из изображения" in calls[1]
        
        bot.image_processor.extract_text_from_image.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_photo_empty_text(self, bot, mock_update, mock_context):
        """Тест обработки фото с пустым текстом"""
        mock_photo = Mock()
        mock_photo.file_id = "test_file_id"
        mock_update.message.photo = [mock_photo]
        
        bot.image_processor.extract_text_from_image.return_value = ""
        
        await bot.handle_photo(mock_update, mock_context)
        
        error_calls = [call for call in mock_update.message.reply_text.call_args_list 
                      if "Текст не распознан" in call.args[0]]
        assert len(error_calls) > 0
    
    @pytest.mark.asyncio
    async def test_handle_photo_error(self, bot, mock_update, mock_context):
        """Тест обработки ошибки при обработке фото"""
        mock_photo = Mock()
        mock_photo.file_id = "test_file_id"
        mock_update.message.photo = [mock_photo]
        
        bot.image_processor.extract_text_from_image.side_effect = Exception("Processing error")
        
        await bot.handle_photo(mock_update, mock_context)
        
        error_calls = [call for call in mock_update.message.reply_text.call_args_list 
                      if "Ошибка обработки" in call.args[0]]
        assert len(error_calls) > 0
    
    @pytest.mark.asyncio
    async def test_error_handler(self, bot, mock_update, mock_context):
        """Тест обработчика ошибок"""
        error = Exception("Test error")
        mock_context.error = error
        
        await bot.error_handler(mock_update, mock_context)
        
        if mock_update and mock_update.message:
            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args[0]
            assert "Ошибка" in call_args[0]
    
    @pytest.mark.asyncio
    async def test_set_bot_commands(self, bot, mock_context):
        """Тест установки команд бота"""
        mock_application = Mock()
        mock_application.bot = mock_context.bot
        
        await bot.set_bot_commands(mock_application)
        
        mock_context.bot.set_my_commands.assert_called_once()
        call_args = mock_context.bot.set_my_commands.call_args[0]
        commands = call_args[0]
        
        command_names = [cmd.command for cmd in commands]
        assert "start" in command_names
        assert "help" in command_names
        assert "status" in command_names
    
    @pytest.mark.asyncio
    async def test_handle_photo_file_operations(self, bot, mock_update, mock_context):
        """Тест файловых операций при обработке фото"""
        mock_photo = Mock()
        mock_photo.file_id = "test_file_id"
        mock_update.message.photo = [mock_photo]
        
        with patch('os.remove') as mock_remove:
            await bot.handle_photo(mock_update, mock_context)
            
            assert mock_remove.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_handle_photo_text_truncation(self, bot, mock_update, mock_context):
        """Тест усечения длинного текста"""
        mock_photo = Mock()
        mock_photo.file_id = "test_file_id"
        mock_update.message.photo = [mock_photo]
        
        long_text = "Тестовый текст " * 50
        bot.image_processor.extract_text_from_image.return_value = long_text
        
        await bot.handle_photo(mock_update, mock_context)
        
        text_calls = [call for call in mock_update.message.reply_text.call_args_list 
                     if "Создаю аудио из текста" in call.args[0]]
        assert len(text_calls) > 0
        
        text_message = text_calls[0].args[0]
        assert "..." in text_message
    
    @pytest.mark.asyncio
    async def test_handle_photo_voice_reply(self, bot, mock_update, mock_context):
        """Тест отправки голосового сообщения"""
        mock_photo = Mock()
        mock_photo.file_id = "test_file_id"
        mock_update.message.photo = [mock_photo]
        
        mock_update.message.reply_voice = AsyncMock()
        
        with patch('builtins.open', create=True) as mock_open:
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            with patch('os.remove'):
                await bot.handle_photo(mock_update, mock_context)
                
                mock_update.message.reply_voice.assert_called_once()
    
    def test_run_method(self, bot):
        """Тест метода run"""
        with patch('src.bot.Application') as mock_application:
            mock_app_builder = Mock()
            mock_application.builder.return_value = mock_app_builder
            mock_app = Mock()
            mock_app_builder.build.return_value = mock_app
            mock_app_builder.return_value.token.return_value = mock_app_builder
            
            with patch('asyncio.run') as mock_asyncio:
                bot.run()
                
                mock_application.builder.assert_called_once()
                mock_app.add_handler.assert_called()
                mock_app.run_polling.assert_called_once()