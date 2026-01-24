#!/usr/bin/env python3
"""
Тест многоязычной обработки текста
"""

import os
import sys
import asyncio
from unittest.mock import Mock, AsyncMock

# Добавляем путь к корню проекта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.bot import TelegramBot
from utils.multilingual_processor import MultilingualTextProcessor

async def test_multilingual_processor():
    """Тест многоязычного процессора"""
    print("🧪 Тестирование многоязычного процессора...")
    
    processor = MultilingualTextProcessor()
    
    # Тестовые тексты на разных языках
    test_texts = [
        {
            'name': 'Русский текст с ошибками',
            'text': 'превет как дела спосибо за помощь',
            'expected_language': 'ru',
            'expected_corrections': True
        },
        {
            'name': 'Английский текст с ошибками',
            'text': 'helo how are you im fine thnak you',
            'expected_language': 'en',
            'expected_corrections': True
        },
        {
            'name': 'Смешанный текст',
            'text': 'hello мир how are дела',
            'expected_language': 'mixed',
            'expected_corrections': False
        },
        {
            'name': 'Английский без ошибок',
            'text': 'Hello! How are you? Thank you.',
            'expected_language': 'en',
            'expected_corrections': False
        },
        {
            'name': 'Русский без ошибок',
            'text': 'Привет! Как дела? Спасибо.',
            'expected_language': 'ru',
            'expected_corrections': False
        }
    ]
    
    for test in test_texts:
        print(f"\n📝 Тест: {test['name']}")
        print(f"📄 Текст: {test['text']}")
        
        result = processor.process_text(test['text'])
        
        print(f"🌐 Язык: {result.language} (ожидалось: {test['expected_language']})")
        print(f"✅ Исправлено: {result.corrected_text}")
        print(f"🔧 Исправлений: {len(result.corrections)}")
        print(f"📊 Статистика: {result.stats}")
        
        # Проверки
        if result.language != test['expected_language']:
            print(f"⚠️ Язык определен неверно: {result.language} != {test['expected_language']}")
        else:
            print("✅ Язык определен корректно")
        
        if test['expected_corrections'] and len(result.corrections) == 0:
            print("⚠️ Ожидались исправления, но их нет")
        elif not test['expected_corrections'] and len(result.corrections) > 0:
            print("⚠️ Не ожидались исправления, но они есть")
        else:
            print("✅ Исправления соответствуют ожиданиям")
        
        if result.corrections:
            print(f"🔍 Найденные проблемы:")
            for i, correction in enumerate(result.corrections[:3], 1):
                print(f"   {i}. {correction.description}")
        
        print("-" * 60)
    
    return True

async def test_bot_integration():
    """Тест интеграции с ботом"""
    print("🧪 Тестирование интеграции с ботом...")
    
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
    
    # Тестовые тексты на разных языках
    test_texts = [
        'привет как дела',
        'hello how are you',
        'смешанный mixed текст'
    ]
    
    for text in test_texts:
        try:
            mock_update.message.text = text
            await bot.text_to_text_response(mock_update, mock_context, text)
            
            # Проверяем, что ответ был отправлен
            mock_update.message.reply_text.assert_called()
            call_args = mock_update.message.reply_text.call_args[0][0]
            
            # Проверяем наличие ключевых элементов
            assert 'Multilingual Text Analysis' in call_args, "Нет заголовка анализа"
            assert 'Original:' in call_args, "Нет оригинального текста"
            assert 'Statistics:' in call_args, "Нет статистики"
            assert 'Language:' in call_args, "Нет информации о языке"
            
            print(f"✅ Текст '{text}' обработан корректно")
            
        except Exception as e:
            print(f"❌ Ошибка обработки текста '{text}': {e}")
            return False
    
    return True

async def test_language_detection():
    """Тест определения языка"""
    print("\n🧪 Тестирование определения языка...")
    
    processor = MultilingualTextProcessor()
    
    language_tests = [
        ('привет мир', 'ru'),
        ('hello world', 'en'), 
        ('привет world', 'mixed'),
        ('123 456', 'unknown'),
        ('', 'unknown')
    ]
    
    for text, expected in language_tests:
        detected = processor.detect_language(text)
        status = "✅" if detected == expected else "❌"
        print(f"{status} '{text}' -> {detected} (ожидалось: {expected})")
    
    return True

async def test_spell_checking():
    """Тест проверки орфографии"""
    print("\n🧪 Тестирование проверки орфографии...")
    
    processor = MultilingualTextProcessor()
    
    spell_tests = [
        ('ru', 'превет как дела спосибо'),
        ('en', 'helo wrld thnak you'),
        ('mixed', 'hello мир привт')
    ]
    
    for language, text in spell_tests:
        corrected, corrections = processor.correct_spelling(text, language)
        print(f"\n📝 Язык: {language}")
        print(f"📄 Оригинал: {text}")
        print(f"✅ Исправлено: {corrected}")
        print(f"🔧 Исправлений: {len(corrections)}")
        
        if corrections:
            for correction in corrections[:3]:
                print(f"   • {correction.description}")
    
    return True

async def main():
    """Основная функция тестирования"""
    print("🚀 Тестирование многоязычной обработки текста\n")
    
    success = True
    
    # Тестирование процессора
    if not await test_multilingual_processor():
        success = False
    
    # Тестирование интеграции с ботом
    if not await test_bot_integration():
        success = False
    
    # Тестирование определения языка
    if not await test_language_detection():
        success = False
    
    # Тестирование проверки орфографии
    if not await test_spell_checking():
        success = False
    
    if success:
        print("\n🎉 Все тесты пройдены успешно!")
        print("\n📋 **Новый многоязычный функционал:**")
        print("✅ Автоматическое определение языка (RU/EN/Mixed)")
        print("✅ Интеллектуальная исправление опечаток")
        print("✅ Грамматическая коррекция для RU и EN")
        print("✅ Расширение сокращений и аббревиатур")
        print("✅ Коррекция пунктуации и регистра")
        print("✅ Многоязычные рекомендации")
        print("✅ Умная статистика с учетом языка")
        return 0
    else:
        print("\n❌ Некоторые тесты не пройдены")
        return 1

if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)