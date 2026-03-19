"""Безопасная обработка медиа с улучшенной обработкой ошибок и кешированием"""

import logging
from typing import Optional

from telegram import Message, Photo, Update, Voice

from src.safe_media_processor import MediaProcessor

logger = logging.getLogger(__name__)

class SafeMediaProcessor:
    """Класс для безопасной обработки медиа с улучшенной обработкой ошибок и кешированием"""

    def __init__(self, image_processor=None, transcriber=None):
        """Инициализация с опциональными компонентами"""
        self.image_processor = image_processor
        self.transcriber = transcriber
        self.media_processor = MediaProcessor()

    async def safe_message_check(self, update: Update) -> Message | None:
        """Безопасная проверка объекта сообщения"""
        if not update:
            return None

        if update.message:
            return update.message

        return None

    def safe_user_check(self, update: Update) -> Optional:
        """Безопасная проверка пользователя"""
        if not update or not update.effective_user:
            return None
        return update.effective_user

    def safe_voice_check(self, update: Update) -> Voice | None:
        """Безопасная проверка голосового сообщения"""
        message = self.safe_message_check(update)
        if not message:
            return None

        if message.voice:
            return message.voice

        return None

    def safe_photo_check(self, update: Update) -> Photo | None:
        """Безопасная проверка фотографии"""
        message = self.safe_message_check(update)
        if not message:
            return None

        if message.photo and len(message.photo) > 0:
            return message.photo[-1]  # Выбираем фото максимального качества

        return None

    def send_error_with_fallback(self, update: Update, title: str, main_message: str, technical_details: str = None) -> bool:
        """Отправляет ошибку с резервным методом"""
        try:
            # Основная попытка
            await update.message.reply_text(f"❌ {title}\n\n{main_message}")
            return True

        except Exception:
            # Резервный метод с деталями ошибки
            if technical_details:
                await update.message.reply_text(f"❌ {title}\n\n{main_message}\n\n**Технические детали:**\n{technical_details}")
            return False

    async def send_processing_start(self, update: Update, process_type: str) -> bool:
        """Отправляет сообщение о начале обработки"""
        try:
            status_emoji = {
                'photo': "📸",
                'voice': '🎤',
                'text': '🔊'
            }.get(process_type, 'text')

            message = f"{status_emoji} **{process_type} обработка...**"

            if update.message:
                await update.message.reply_text(message)
                return True
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения о начале обработки: {e}")
            return False

    async def send_success_result(self, update: Update, title: str, result_data: str, audio_path: str = None) -> bool:
        """Отправляет успешный результат"""
        try:
            if audio_path:
                # Для TTS результатов
                await update.message.reply_voice(audio_file=audio_path, caption=f"✅ {result_data}")
            else:
                await update.message.reply_text(f"✅ {result_data}")
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки результата: {e}")
            return self.send_error_with_fallback(
                update,
                "❌ **Ошибка результата**",
                "Не удалось отправить результат",
                "Попробуйте еще раз"
            )

    async def safe_download_file(self, update: Update, file_id: str, suffix: str = ".tmp") -> str | None:
        """Безопасное скачивание файла"""
        try:
            file = await update.bot.get_file(file_id)
            if not file:
                return None

            # Создаем безопасное имя файла
            safe_filename = f"safe_{file_id}{suffix}"

            file_path = f"downloads/{safe_filename}"

            await file.download_to_drive(file_path)
            logger.info(f"Файл успешно скачан: {safe_filename}")
            return file_path

        except Exception as e:
            logger.error(f"Ошибка скачивания файла: {e}")
            await self.send_error_with_fallback(
                update,
                "❌ **Ошибка скачивания**",
                "Не удалось скачать файл",
                "Попробуйте отправить файл другим способом"
            )
            return None

    async def safe_delete_file(self, file_path: str) -> bool:
        """Безопасное удаление файла"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Файл удален: {file_path}")
                return True
        except Exception as e:
            logger.error(f"Ошибка удаления файла {file_path}: {e}")
            return False

    async def validate_file(self, file_path: str, max_size_mb: int = 20) -> bool:
        """Валидация файла перед обработкой"""
        if not os.path.exists(file_path):
            return False

        # Проверяем размер файла
        try:
            file_size = os.path.getsize(file_path) / (1024 * 1024)  # в MB
            if file_size > max_size_mb:
                return False
        except OSError:
            return False

        return True

    def format_error_message(self, error: Exception, context: str = "") -> str:
        """Форматирует ошибку с техническими деталями"""
        error_type = type(error).__name__
        error_msg = str(error)

        base_msg = f"{error_type}: {error_msg}"

        if context:
            base_msg += f"\n\n**Контекст:** {context}"

        return base_msg
