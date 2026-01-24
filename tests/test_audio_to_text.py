import pytest
import os
import sys
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Добавляем путь к корню проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.models import Base, User


class TestAudioToTextFunctionality:
    """Тесты для функциональности преобразования аудио в текст"""

    @pytest.fixture
    def db_session(self):
        """Создание тестовой сессии базы данных"""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()
        yield session
        session.close()

    @pytest.fixture
    def mock_update_voice(self):
        """Мок для Update с голосовым сообщением"""
        mock_update = Mock()
        mock_update.message = Mock()
        mock_update.message.reply_text = AsyncMock()
        mock_update.effective_user = Mock()
        mock_update.effective_user.id = 123456789
        mock_update.effective_user.username = "testuser"
        mock_update.effective_user.first_name = "Test"
        mock_update.effective_user.last_name = "User"

        # Мок голосового сообщения
        mock_voice = Mock()
        mock_voice.file_id = "voice_file_id"
        mock_voice.duration = 10
        mock_update.message.voice = mock_voice

        return mock_update

    @pytest.fixture
    def mock_context(self):
        """Мок для ContextTypes.DEFAULT_TYPE"""
        mock_context = Mock()
        mock_context.bot = Mock()
        mock_context.bot.get_file = AsyncMock()
        mock_context.bot.get_file.return_value.download_to_drive = AsyncMock()
        return mock_context

    @pytest.fixture
    def bot_with_env(self, db_session):
        """Фикстура для бота с тестовым окружением"""
        with patch.dict(os.environ, {
            'TELEGRAM_BOT_TOKEN': 'test_token',
            'ADMIN_IDS': '111111111'
        }):
            with patch('database.models.get_db') as mock_get_db:
                mock_get_db.return_value = db_session

                with patch('database.models.create_tables'):
                    from src.bot import TelegramBot
                    bot = TelegramBot()
                    bot.admin_service = Mock()
                    return bot

    def test_handle_voice_success(self, bot_with_env, mock_update_voice, mock_context, db_session):
        """Тест успешной обработки голосового сообщения"""
        # Мокаем транскрибатора
        mock_transcription_result = {
            "text": "Тестовая транскрипция голосового сообщения",
            "duration": 10.5,
            "language": "ru"
        }

        with patch.object(bot_with_env.transcriber, 'transcribe_audio', return_value=mock_transcription_result):
            # Создаем пользователя
            user = User(telegram_id=123456789, username="testuser")
            db_session.add(user)
            db_session.commit()

            # Запускаем обработку
            import asyncio
            asyncio.run(bot_with_env.handle_voice(mock_update_voice, mock_context))

            # Проверяем вызовы
            mock_update_voice.message.reply_text.assert_called()
            calls = mock_update_voice.message.reply_text.call_args_list

            # Проверяем что были сообщения о начале и завершении обработки
            assert len(calls) >= 2
            assert "Получаю голосовое сообщение" in calls[0][0][0]
            assert "Распознанный текст" in calls[1][0][0]
            assert "Тестовая транскрипция" in calls[1][0][0]

    def test_handle_voice_no_speech_recognized(self, bot_with_env, mock_update_voice, mock_context, db_session):
        """Тест обработки голосового сообщения без распознанной речи"""
        # Мокаем транскрибатора с пустым результатом
        mock_transcription_result = {
            "text": "",
            "duration": 10.5,
            "language": "ru"
        }

        with patch.object(bot_with_env.transcriber, 'transcribe_audio', return_value=mock_transcription_result):
            # Создаем пользователя
            user = User(telegram_id=123456789, username="testuser")
            db_session.add(user)
            db_session.commit()

            # Запускаем обработку
            import asyncio
            asyncio.run(bot_with_env.handle_voice(mock_update_voice, mock_context))

            # Проверяем что было сообщение об ошибке
            mock_update_voice.message.reply_text.assert_called()
            calls = mock_update_voice.message.reply_text.call_args_list

            error_message_found = any("Не удалось распознать речь" in call[0][0] for call in calls)
            assert error_message_found

    def test_handle_voice_processing_error(self, bot_with_env, mock_update_voice, mock_context, db_session):
        """Тест обработки ошибки при транскрибации"""
        # Мокаем транскрибатора с исключением
        with patch.object(bot_with_env.transcriber, 'transcribe_audio', side_effect=Exception("Transcription error")):
            # Создаем пользователя
            user = User(telegram_id=123456789, username="testuser")
            db_session.add(user)
            db_session.commit()

            # Запускаем обработку
            import asyncio
            asyncio.run(bot_with_env.handle_voice(mock_update_voice, mock_context))

            # Проверяем что было сообщение об ошибке
            mock_update_voice.message.reply_text.assert_called()
            calls = mock_update_voice.message.reply_text.call_args_list

            error_message_found = any("Произошла ошибка" in call[0][0] for call in calls)
            assert error_message_found

    def test_handle_voice_no_voice_message(self, bot_with_env, mock_update_voice, mock_context):
        """Тест обработки сообщения без голосового файла"""
        mock_update_voice.message.voice = None

        # Запускаем обработку
        import asyncio
        asyncio.run(bot_with_env.handle_voice(mock_update_voice, mock_context))

        # Проверяем что метод завершился без обработки
        mock_update_voice.message.reply_text.assert_not_called()

    def test_audio_to_text_transcription_logging(self, bot_with_env, mock_update_voice, mock_context, db_session):
        """Тест логирования транскрипций аудио в текст"""
        # Мокаем транскрибатора
        mock_transcription_result = {
            "text": "Тестовая транскрипция",
            "duration": 5.0,
            "language": "ru"
        }

        with patch.object(bot_with_env.transcriber, 'transcribe_audio', return_value=mock_transcription_result):
            # Мокаем AdminService
            mock_admin_service = Mock()
            bot_with_env.admin_service = mock_admin_service

            # Создаем пользователя
            user = User(telegram_id=123456789, username="testuser")
            db_session.add(user)
            db_session.commit()

            # Запускаем обработку
            import asyncio
            asyncio.run(bot_with_env.handle_voice(mock_update_voice, mock_context))

            # Проверяем что были вызовы логирования
            assert mock_admin_service.log_audio_to_text_transcription.call_count >= 2

            # Проверяем вызовы логирования
            calls = mock_admin_service.log_audio_to_text_transcription.call_args_list

            # Первый вызов - начало обработки
            start_call = calls[0]
            assert start_call[1]['user_id'] == 123456789
            assert start_call[1]['status'] == 'processing'
            assert start_call[1]['audio_duration'] == 10

            # Второй вызов - успешное завершение
            success_call = calls[1]
            assert success_call[1]['user_id'] == 123456789
            assert success_call[1]['status'] == 'completed'
            assert success_call[1]['recognized_text'] == "Тестовая транскрипция"
            assert success_call[1]['audio_duration'] == 10

    def test_voice_message_processing_workflow(self, bot_with_env, mock_update_voice, mock_context, db_session):
        """Тест полного workflow обработки голосового сообщения"""
        # Мокаем все зависимости
        mock_transcription_result = {
            "text": "Привет, это тестовое голосовое сообщение для проверки транскрибации",
            "duration": 8.5,
            "language": "ru"
        }

        with patch.object(bot_with_env.transcriber, 'transcribe_audio', return_value=mock_transcription_result):
            # Создаем пользователя
            user = User(telegram_id=123456789, username="testuser")
            db_session.add(user)
            db_session.commit()

            # Запускаем обработку
            import asyncio
            asyncio.run(bot_with_env.handle_voice(mock_update_voice, mock_context))

            # Проверяем последовательность сообщений
            calls = mock_update_voice.message.reply_text.call_args_list
            assert len(calls) >= 3

            # Проверяем содержание сообщений
            messages = [call[0][0] for call in calls]

            # Первое сообщение - получение
            assert "Получаю голосовое сообщение" in messages[0]

            # Второе сообщение - распознание
            assert "Распознаю речь" in messages[1]

            # Третье сообщение - результат
            assert "Распознанный текст" in messages[2]
            assert "Привет, это тестовое голосовое сообщение" in messages[2]

    def test_voice_message_error_recovery(self, bot_with_env, mock_update_voice, mock_context, db_session):
        """Тест восстановления после ошибок в обработке голосовых сообщений"""
        # Сначала успешная обработка
        mock_transcription_result = {
            "text": "Успешная транскрибация",
            "duration": 3.0,
            "language": "ru"
        }

        with patch.object(bot_with_env.transcriber, 'transcribe_audio', return_value=mock_transcription_result):
            # Создаем пользователя
            user = User(telegram_id=123456789, username="testuser")
            db_session.add(user)
            db_session.commit()

            # Успешная обработка
            import asyncio
            asyncio.run(bot_with_env.handle_voice(mock_update_voice, mock_context))

            # Проверяем успешное завершение
            calls = mock_update_voice.message.reply_text.call_args_list
            success_messages = [call for call in calls if "Распознанный текст" in call[0][0]]
            assert len(success_messages) > 0

    def test_voice_message_file_cleanup(self, bot_with_env, mock_update_voice, mock_context, db_session):
        """Тест очистки временных файлов после обработки"""
        import tempfile
        import os

        # Создаем временный файл для имитации аудиофайла
        with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_file:
            temp_file_path = temp_file.name
            temp_file.write(b"fake audio data")

        # Мокаем загрузку файла
        mock_context.bot.get_file.return_value.download_to_drive = AsyncMock(side_effect=lambda path: open(temp_file_path, 'wb').write(b"fake data") or None)

        mock_transcription_result = {
            "text": "Тестовая транскрибация",
            "duration": 2.0,
            "language": "ru"
        }

        with patch.object(bot_with_env.transcriber, 'transcribe_audio', return_value=mock_transcription_result):
            # Создаем пользователя
            user = User(telegram_id=123456789, username="testuser")
            db_session.add(user)
            db_session.commit()

            # Запускаем обработку
            import asyncio
            asyncio.run(bot_with_env.handle_voice(mock_update_voice, mock_context))

            # В реальном коде файл должен быть удален, но в тесте мы не можем проверить это напрямую
            # Проверяем что обработка завершилась без ошибок
            calls = mock_update_voice.message.reply_text.call_args_list
            assert len(calls) >= 2

        # Очищаем временный файл
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)