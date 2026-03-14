"""
Callback handlers for AI Transcriber Bot
"""

import logging
from typing import Optional
from telegram import Update
from telegram.ext import ContextTypes

from src.core.user_manager import UserManager
from config.settings import config

logger = logging.getLogger(__name__)


class CallbackHandlers:
    """Handles all callback-related operations"""
    
    def __init__(self, config, user_manager: UserManager):
        self.config = config
        self.user_manager = user_manager
    
    async def callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle callback queries from inline keyboards"""
        try:
            query = update.callback_query
            await query.answer()  # Acknowledge the callback
            
            mode_descriptions = {
                "mode_photo": "📸 **Режим: Фото → Текст (OCR)** активирован!\n\nТеперь отправляйте изображения с текстом, и бот распознает текст с помощью Tesseract OCR.",
                "mode_voice": "🎤 **Режим: Голос → Текст (Whisper)** активирован!\n\nТеперь отправляйте голосовые сообщения, и бот транскрибирует речь с помощью OpenAI Whisper.",
                "mode_tts": "📝 **Режим: Текст → Голос (TTS)** активирован!\n\nТеперь отправляйте текстовые сообщения, и бот преобразует их в аудио с помощью синтеза речи.",
                "mode_ai": "💬 **Режим: Текст → AI Ответ** активирован!\n\nТеперь отправляйте текстовые сообщения, и бот проанализирует и улучшит ваш текст.",
                "mode_help": "ℹ️ **Помощь по режимам работы:**\n\n📸 **Фото → Текст (OCR):**\n• Отправьте фото с текстом\n• Поддерживаются JPG, PNG, WEBP\n• Текст должен быть четким\n\n🎤 **Голос → Текст (Whisper):**\n• Отправьте голосовые сообщения\n• Поддерживаются OGG, WAV, M4A\n• Говорите четко\n\n📝 **Текст → Голос (TTS):**\n• Отправьте текстовые сообщения\n• Бот синтезирует естественную речь\n• Поддерживаются длинные сообщения\n\n💬 **Текст → AI Ответ:**\n• Отправьте текст для анализа\n• Бот исправляет ошибки и грамматику\n• Предлагает улучшения\n\n🔄 **Автоматический режим:**\n• Бот автоматически определяет тип файла\n• Применяет соответствующую обработку\n• Отправьте любой файл!",
                "mode_auto": "🔄 **Автоматический режим активирован!**\n\nБот будет автоматически определять тип файла и применять соответствующую обработку:\n\n• 📸 Фото → OCR распознавание\n• 🎤 Голос → Whisper транскрибация\n• 📝 Текст → TTS синтез речи\n• 💬 Текст → AI анализ\n\nПросто отправьте любой файл!"
            }
            
            # Get description for selected mode
            selected_mode = query.data
            description = mode_descriptions.get(selected_mode, "❌ Неизвестный режим")
            
            await query.edit_message_text(description, parse_mode="Markdown")
            logger.info(f"User {update.effective_user.id} selected mode: {selected_mode}")
            
        except Exception as e:
            logger.error(f"Error in callback_handler: {e}")
            try:
                await update.callback_query.answer("❌ Произошла ошибка. Попробуйте еще раз.")
            except:
                pass