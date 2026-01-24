import pytest
import os
from unittest.mock import Mock, patch, AsyncMock

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.bot import TelegramBot


class TestBotCommands:
    """Тесты для команд бота"""
    
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
                    return TelegramBot()
    
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
        return mock_context
    
    @pytest.mark.asyncio
    async def test_start_command_content(self, bot, mock_update, mock_context):
        """Тест содержимого команды /start"""
        await bot.start_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0]
        message = call_args[0]
        
        assert "🎉 Добро пожаловать в AI Транскрибатор" in message
        assert "Я помогу вам преобразовать изображения с текстом в аудио" in message
        assert "📸 **Как использовать:**" in message
        assert "1. Отправьте мне изображение с текстом" in message
        assert "2. Я распознаю текст и создам аудио" in message
        assert "3. Вы получите аудиофайл с транскрипцией" in message
        assert "🔧 **Доступные команды:**" in message
        assert "/start - Показать это сообщение" in message
        assert "/help - Помощь и инструкции" in message
        assert "/status - Проверить статус бота" in message
        assert "💡 **Совет:**" in message
    
    @pytest.mark.asyncio
    async def test_help_command_content(self, bot, mock_update, mock_context):
        """Тест содержимого команды /help"""
        await bot.help_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0]
        message = call_args[0]
        
        assert "📖 **Помощь - AI Транскрибатор**" in message
        assert "🔍 **Что я делаю:**" in message
        assert "- Распознаю текст на изображениях" in message
        assert "- Преобразую текст в речь с помощью Whisper" in message
        assert "- Создаю аудиофайлы с транскрипцией" in message
        assert "📸 **Как отправить изображение:**" in message
        assert "1. Нажмите на скрепку 📎" in message
        assert "2. Выберите \"Фото или видео\"" in message
        assert "3. Выберите изображение с текстом" in message
        assert "4. Отправьте мне" in message
        assert "⚠️ **Важные моменты:**" in message
        assert "- Изображение должно содержать читаемый текст" in message
        assert "- Поддерживаются форматы: JPG, PNG, WEBP" in message
        assert "- Максимальный размер: 20MB" in message
        assert "- Чем четче текст, тем лучше результат" in message
        assert "🔄 **Статус обработки:**" in message
        assert "- 🔄 Обработка..." in message
        assert "- ✅ Готово" in message
        assert "- ❌ Ошибка" in message
    
    @pytest.mark.asyncio
    async def test_status_command_content(self, bot, mock_update, mock_context):
        """Тест содержимого команды /status"""
        await bot.status_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0]
        message = call_args[0]
        
        assert "🤖 **Статус бота:**" in message
        assert "✅ Бот активен и готов к работе" in message
        assert "🔹 Whisper: Загружен" in message
        assert "🔹 Обработка изображений: Доступна" in message
        assert "⏰ Время:" in message
    
    @pytest.mark.asyncio
    async def test_status_command_timestamp(self, bot, mock_update, mock_context):
        """Тест временной метки в команде /status"""
        await bot.status_command(mock_update, mock_context)
        
        call_args = mock_update.message.reply_text.call_args[0]
        message = call_args[0]
        
        assert any(char.isdigit() for char in message)
        assert ":" in message
    
    @pytest.mark.asyncio
    async def test_unknown_command_handling(self, bot, mock_update, mock_context):
        """Тест обработки неизвестной команды"""
        mock_update.message.text = "/unknown_command"
        
        with patch('src.bot.CommandHandler') as mock_handler:
            bot.run()
            mock_handler.assert_called()
    
    @pytest.mark.asyncio
    async def test_command_case_sensitivity(self, bot, mock_update, mock_context):
        """Тест чувствительности к регистру команд"""
        mock_update.message.text = "/START"
        
        with patch('src.bot.CommandHandler') as mock_handler:
            bot.run()
            mock_handler.assert_called()
    
    @pytest.mark.asyncio
    async def test_command_with_parameters(self, bot, mock_update, mock_context):
        """Тест команды с параметрами"""
        mock_update.message.text = "/start param1 param2"
        
        await bot.start_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0]
        message = call_args[0]
        
        assert "Добро пожаловать в AI Транскрибатор" in message
    
    @pytest.mark.asyncio
    async def test_multiple_consecutive_commands(self, bot, mock_update, mock_context):
        """Тест нескольких последовательных команд"""
        await bot.start_command(mock_update, mock_context)
        await bot.help_command(mock_update, mock_context)
        await bot.status_command(mock_update, mock_context)
        
        assert mock_update.message.reply_text.call_count == 3
        
        calls = [call.args[0] for call in mock_update.message.reply_text.call_args_list]
        assert "Добро пожаловать" in calls[0]
        assert "Помощь" in calls[1]
        assert "Статус бота" in calls[2]
    
    @pytest.mark.asyncio
    async def test_command_error_handling(self, bot, mock_update, mock_context):
        """Тест обработки ошибок в командах"""
        mock_update.message.reply_text.side_effect = Exception("Reply error")
        
        with pytest.raises(Exception, match="Reply error"):
            await bot.start_command(mock_update, mock_context)
    
    @pytest.mark.asyncio
    async def test_command_message_formatting(self, bot, mock_update, mock_context):
        """Тест форматирования сообщений команд"""
        await bot.start_command(mock_update, mock_context)
        
        call_args = mock_update.message.reply_text.call_args[0]
        message = call_args[0]
        
        assert "🎉" in message
        assert "📸" in message
        assert "🔧" in message
        assert "💡" in message
        assert "**" in message
        assert "1." in message
        assert "2." in message
        assert "3." in message