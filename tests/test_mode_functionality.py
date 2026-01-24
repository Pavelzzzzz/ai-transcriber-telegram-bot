#!/usr/bin/env python3
"""
Тест для проверки работы /mode и текстовых функций
"""

import os
import sys
import asyncio
from unittest.mock import Mock, AsyncMock

# Добавляем путь к корню проекта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.bot import TelegramBot

async def test_mode_command():
    """Тест команды /mode"""
    print("🧪 Тестирование команды /mode...")
    
    # Настройка окружения
    os.environ['TELEGRAM_BOT_TOKEN'] = 'test_token'
    
    # Создание бота
    bot = TelegramBot()
    
    # Моки для обновления
    mock_update = Mock()
    mock_update.message = Mock()
    mock_update.message.reply_text = AsyncMock()
    mock_update.effective_user = Mock()
    mock_update.effective_user.id = 123456789
    mock_update.effective_user.username = "testuser"
    
    mock_context = Mock()
    mock_context.args = []
    
    try:
        # Тест команды /mode
        await bot.mode_command(mock_update, mock_context)
        
        # Проверка вызова reply_text
        mock_update.message.reply_text.assert_called()
        call_args = mock_update.message.reply_text.call_args
        
        # Проверка наличия клавиатуры
        assert call_args[1]['reply_markup'] is not None, "❌ Клавиатура не найдена"
        print("✅ Команда /mode работает корректно")
        
        # Проверка callback handler
        mock_update.callback_query = Mock()
        mock_update.callback_query.answer = AsyncMock()
        mock_update.callback_query.edit_message_text = AsyncMock()
        mock_update.callback_query.data = "mode:text_to_audio:123456789"
        
        await bot.callback_handler(mock_update, mock_context)
        
        # Проверка смены режима
        assert bot.user_modes[123456789] == 'text_to_audio', "❌ Режим не изменился"
        print("✅ Callback handler работает корректно")
        
        # Тест обработчика текста
        mock_update.message.text = "Тестовый текст для преобразования"
        mock_update.callback_query = None  # Убираем callback
        
        await bot.text_message_handler(mock_update, mock_context)
        
        print("✅ Текстовый обработчик работает корректно")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

async def test_all_modes():
    """Тест всех режимов"""
    print("\n🧪 Тестирование всех режимов...")
    
    os.environ['TELEGRAM_BOT_TOKEN'] = 'test_token'
    bot = TelegramBot()
    
    mock_update = Mock()
    mock_update.message = Mock()
    mock_update.message.reply_text = AsyncMock()
    mock_update.effective_user = Mock()
    mock_update.effective_user.id = 123456789
    mock_update.effective_user.username = "testuser"
    
    mock_context = Mock()
    
    modes = [
        ('mode:img_to_text:123456789', 'img_to_text'),
        ('mode:audio_to_text:123456789', 'audio_to_text'), 
        ('mode:text_to_audio:123456789', 'text_to_audio'),
        ('mode:text_to_text:123456789', 'text_to_text')
    ]
    
    for callback_data, expected_mode in modes:
        try:
            mock_update.callback_query = Mock()
            mock_update.callback_query.answer = AsyncMock()
            mock_update.callback_query.edit_message_text = AsyncMock()
            mock_update.callback_query.data = callback_data
            
            await bot.callback_handler(mock_update, mock_context)
            
            assert bot.user_modes[123456789] == expected_mode, f"❌ Режим {expected_mode} не установился"
            print(f"✅ Режим {expected_mode} работает")
            
        except Exception as e:
            print(f"❌ Ошибка в режиме {expected_mode}: {e}")
            return False
    
    return True

async def main():
    """Основная функция тестирования"""
    print("🚀 Запуск тестов для /mode и текстовых функций\n")
    
    success = True
    
    # Тест команды /mode
    if not await test_mode_command():
        success = False
    
    # Тест всех режимов
    if not await test_all_modes():
        success = False
    
    if success:
        print("\n🎉 Все тесты пройдены успешно!")
        print("\n📋 **Результат:**")
        print("✅ Команда /mode работает")
        print("✅ Переключение режимов работает")
        print("✅ Текстовые обработчики работают")
        print("✅ Callback handler работает")
        return 0
    else:
        print("\n❌ Некоторые тесты не пройдены")
        return 1

if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)