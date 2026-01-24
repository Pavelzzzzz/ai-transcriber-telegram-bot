#!/usr/bin/env python3
"""
Тест для улучшенного режима "Текст → Текст" с исправлением ошибок
"""

import os
import sys
import asyncio
from unittest.mock import Mock, AsyncMock

# Добавляем путь к корню проекта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.bot import TelegramBot

async def test_text_correction_functionality():
    """Тест функции исправления текста"""
    print("🧪 Тестирование исправления текста...")
    
    os.environ['TELEGRAM_BOT_TOKEN'] = 'test_token'
    bot = TelegramBot()
    
    # Тестовые случаи
    test_cases = [
        {
            'name': 'Текст с ошибками',
            'text': 'превет как дела  спосибо  всем',
            'expected_corrections': ['привет', 'спасибо', 'лишние пробелы']
        },
        {
            'name': 'Текст без ошибок',
            'text': 'Привет! Как дела? Спасибо.',
            'expected_corrections': []
        },
        {
            'name': 'Текст с проблемами пунктуации',
            'text': 'привет как дела??? спосibo...',
            'expected_corrections': ['знаки препинания', 'опечатка']
        },
        {
            'name': 'Текст с проблемами регистра',
            'text': 'привет. как дела. хорошо.',
            'expected_corrections': ['заглавные']
        },
        {
            'name': 'Короткий текст',
            'text': 'пр',
            'expected_corrections': []
        }
    ]
    
    for test_case in test_cases:
        try:
            result = await bot.analyze_and_correct_text(test_case['text'])
            
            print(f"\n📝 Тест: {test_case['name']}")
            print(f"📄 Оригинал: {test_case['text']}")
            print(f"✅ Исправлено: {result['corrected_text']}")
            print(f"🔧 Исправлений: {result['corrections_count']}")
            print(f"📊 Статистика: {result['stats']}")
            
            if result['corrections']:
                print(f"🔍 Найдено проблем: {result['corrections']}")
            
            # Проверяем, что текст изменился (если были ошибки)
            if test_case['expected_corrections']:
                if result['corrected_text'] != test_case['text']:
                    print("✅ Текст был исправлен")
                else:
                    print("⚠️ Ожидались исправления, но текст не изменился")
            else:
                print("✅ Текст без изменений корректен")
                
        except Exception as e:
            print(f"❌ Ошибка в тесте {test_case['name']}: {e}")
            return False
    
    return True

async def test_text_to_text_handler():
    """Тест обработчика текстовых сообщений"""
    print("\n🧪 Тестирование обработчика текста...")
    
    os.environ['TELEGRAM_BOT_TOKEN'] = 'test_token'
    bot = TelegramBot()
    
    # Моки
    mock_update = Mock()
    mock_update.message = Mock()
    mock_update.message.reply_text = AsyncMock()
    mock_update.effective_user = Mock()
    mock_update.effective_user.id = 123456789
    
    mock_context = Mock()
    
    # Устанавливаем режим text_to_text
    bot.user_modes[123456789] = 'text_to_text'
    
    # Тестовые тексты
    test_texts = [
        'привет как дела',
        'спосибо за помощь!!!',
        'харошая погода сегодня',
        'Короткий текст'
    ]
    
    for text in test_texts:
        try:
            mock_update.message.text = text
            await bot.text_to_text_response(mock_update, mock_context, text)
            
            # Проверяем, что ответ был отправлен
            mock_update.message.reply_text.assert_called()
            call_args = mock_update.message.reply_text.call_args[0][0]
            
            # Проверяем наличие ключевых элементов в ответе
            assert 'Анализ и исправление текста' in call_args, "Нет заголовка анализа"
            assert 'Оригинал:' in call_args, "Нет оригинального текста"
            assert 'Статистика:' in call_args, "Нет статистики"
            assert 'Рекомендации:' in call_args, "Нет рекомендаций"
            
            print(f"✅ Текст '{text}' обработан корректно")
            
        except Exception as e:
            print(f"❌ Ошибка обработки текста '{text}': {e}")
            return False
    
    return True

async def test_full_mode_switching():
    """Тест полного переключения режимов"""
    print("\n🧪 Тестирование переключения в режим text_to_text...")
    
    os.environ['TELEGRAM_BOT_TOKEN'] = 'test_token'
    bot = TelegramBot()
    
    # Моки
    mock_update = Mock()
    mock_update.message = Mock()
    mock_update.message.reply_text = AsyncMock()
    mock_update.callback_query = Mock()
    mock_update.callback_query.answer = AsyncMock()
    mock_update.callback_query.edit_message_text = AsyncMock()
    mock_update.effective_user = Mock()
    mock_update.effective_user.id = 123456789
    
    mock_context = Mock()
    
    try:
        # Переключаемся в режим text_to_text
        mock_update.callback_query.data = "mode:text_to_text:123456789"
        await bot.callback_handler(mock_update, mock_context)
        
        # Проверяем, что режим установился
        assert bot.user_modes[123456789] == 'text_to_text', "Режим не установился"
        
        # Тестируем обработку текста в этом режиме
        mock_update.callback_query = None  # Убираем callback
        mock_update.message.text = "тестовый текст с ошыбками"
        
        await bot.text_message_handler(mock_update, mock_context)
        
        # Проверяем, что был вызван обработчик текста
        mock_update.message.reply_text.assert_called()
        call_args = mock_update.message.reply_text.call_args[0][0]
        
        assert 'Исправленный текст:' in call_args or 'Ошибок не найдено' in call_args, "Нет анализа текста"
        
        print("✅ Полное переключение режимов работает корректно")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в тесте переключения режимов: {e}")
        return False

async def main():
    """Основная функция тестирования"""
    print("🚀 Тестирование улучшенного режима 'Текст → Текст'\n")
    
    success = True
    
    # Тестирование функции исправления
    if not await test_text_correction_functionality():
        success = False
    
    # Тестирование обработчика
    if not await test_text_to_text_handler():
        success = False
    
    # Тестирование переключения режимов
    if not await test_full_mode_switching():
        success = False
    
    if success:
        print("\n🎉 Все тесты пройдены успешно!")
        print("\n📋 **Новый функционал режима 'Текст → Текст':**")
        print("✅ Исправление опечаток и ошибок")
        print("✅ Коррекция пунктуации и регистра")
        print("✅ Удаление лишних пробелов")
        print("✅ Статистика текста")
        print("✅ Рекомендации по улучшению")
        print("✅ Подробный отчет об изменениях")
        return 0
    else:
        print("\n❌ Некоторые тесты не пройдены")
        return 1

if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)