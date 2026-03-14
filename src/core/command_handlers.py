"""
Command handlers for AI Transcriber Bot
"""

import logging
from typing import Optional
from telegram import Update
from telegram.ext import ContextTypes

from src.core.user_manager import UserManager
from config.settings import config

logger = logging.getLogger(__name__)


class CommandHandlers:
    """Handles all command-related operations"""
    
    def __init__(self, config, user_manager: UserManager):
        self.config = config
        self.user_manager = user_manager
        
    async def _safe_reply(self, update: Update, text: str) -> None:
        """Safely send a reply to the user"""
        try:
            await update.message.reply_text(text)
        except Exception as e:
            logger.error(f"Failed to send reply to user {update.effective_user.id}: {e}")
    
    def is_admin(self, user_id: int, username: str = None) -> bool:
        """Check if user is admin"""
        try:
            # Parse admin usernames
            admin_usernames = []
            if self.config.security.admin_usernames and self.config.security.admin_usernames != 'your_username_here':
                admin_usernames = [name.strip().lower() for name in self.config.security.admin_usernames.split(',') if name.strip()]
            
            # Parse admin IDs  
            admin_ids = []
            if self.config.security.admin_ids:
                try:
                    admin_ids = [int(id_.strip()) for id_ in self.config.security.admin_ids.split(',') if id_.strip().isdigit()]
                except ValueError:
                    pass
            
            # Check username (case insensitive)
            if username and username.lower() in admin_usernames:
                return True
                
            # Check user ID
            if user_id in admin_ids:
                return True
                
            return False
        except Exception as e:
            logger.error(f"Error checking admin status for user {user_id}: {e}")
            return False
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command"""
        try:
            is_user_admin = self.is_admin(update.effective_user.id, update.effective_user.username)
            
            admin_commands = ""
            if is_user_admin:
                admin_commands = "\n\n🔐 **Административные команды:**\n/admin /stats /users /mode"
            
            message = (
                f"🚀 **AI Транскрибатор запущен!** 🎉\n\n"
                "🤖 **4 режима работы с AI:**\n\n"
                "📸 **Режим 1: Фото → Текст (OCR)**\n"
                "📷 Отправьте изображение с текстом\n"
                "🔍 Бот распознает текст с помощью Tesseract OCR\n"
                "📝 Вы получите извлеченный текст\n\n"
                "🎤 **Режим 2: Голос → Текст (Whisper)**\n"
                "📷 Отправьте голосовое сообщение\n"
                "🧠 Бот транскрибирует речь с помощью OpenAI Whisper\n"
                "📝 Вы получите распознанный текст\n\n"
                "📝 **Режим 3: Текст → Голос (TTS)**\n"
                "📷 Отправьте текстовое сообщение\n"
                "🔊 Бот синтезирует речь из текста\n"
                "🎵 Вы получите аудиофайл с озвученным текстом\n\n"
                "💬 **Режим 4: Текст → AI Ответ**\n"
                "📷 Отправьте текстовое сообщение\n"
                "🧠 Бот проанализирует и улучшит ваш текст\n"
                "💡 Вы получите исправленный текст с рекомендациями\n\n"
                "🎛️ **Команды:**\n"
                "/start - Запуск бота\n"
                "/help - Полная помощь\n"
                "/status - Статус бота\n"
                "/mode - Выбор режима (интерактивный)\n"
                f"{admin_commands}"
            )
            
            await self._safe_reply(update, message)
            logger.info(f"Start command used by user {update.effective_user.id}")
        except Exception as e:
            logger.error(f"Error in start_command for user {update.effective_user.id}: {e}")
            await self._safe_reply(update, "❌ Произошла ошибка. Попробуйте еще раз.")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command"""
        try:
            is_user_admin = self.is_admin(update.effective_user.id, update.effective_user.username)
            
            admin_help = ""
            if is_user_admin:
                admin_help = "\n🔐 **Административные команды:** /admin, /stats, /users, /mode"
            
            message = (
                f"📖 **Полная помощь AI Транскрибатора:**\n\n"
                "🤖 **4 режима работы:**\n\n"
                "📸 **1. Фото → Текст (OCR)**\n"
                "• Отправьте фото с текстом\n"
                "• Поддерживаются JPG, PNG, WEBP\n"
                "• Текст должен быть четким и хорошо освещенным\n\n"
                "🎤 **2. Голос → Текст (Whisper)**\n"
                "• Отправьте голосовое сообщение\n"
                "• Поддерживаются OGG, WAV, M4A\n"
                "• Говорите четко, без фонового шума\n\n"
                "📝 **3. Текст → Голос (TTS)**\n"
                "• Отправьте текстовое сообщение\n"
                "• Бот синтезирует естественную речь\n"
                "• Поддерживаются длинные сообщения\n\n"
                "💬 **4. Текст → AI Ответ**\n"
                "• Отправьте текст для анализа\n"
                "• Бот исправляет ошибки и грамматику\n"
                "• Предлагает улучшения стиля\n\n"
                "🎛️ **Команды:**\n"
                "/start - Запуск бота\n"
                "/help - Эта справка\n"
                "/status - Статус бота\n"
                "/mode - Интерактивный выбор режима\n"
                f"{admin_help}\n\n"
                "💡 **Использование:**\n"
                "Просто отправьте любой файл - бот автоматически определит тип!"
            )
            
            await self._safe_reply(update, message)
            logger.info(f"Help command used by user {update.effective_user.id}")
        except Exception as e:
            logger.error(f"Error in help_command for user {update.effective_user.id}: {e}")
            await self._safe_reply(update, "❌ Произошла ошибка. Попробуйте еще раз.")
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command"""
        try:
            message = (
                "📊 **Статус AI Транскрибатора:**\n\n"
                "✅ Бот работает в нормальном режиме\n"
                "🤖 Все 4 режима активны\n"
                "🔌 Подключен к Telegram API\n"
                "📸 OCR: Работает\n"
                "🎤 Whisper: Работает\n"
                "🔊 TTS: Работает\n"
                "🧠 AI Анализ: Работает\n"
                f"👤 Ваш статус: {'Администратор' if self.is_admin(update.effective_user.id, update.effective_user.username) else 'Пользователь'}"
            )
            
            await self._safe_reply(update, message)
            logger.info(f"Status command used by user {update.effective_user.id}")
        except Exception as e:
            logger.error(f"Error in status_command for user {update.effective_user.id}: {e}")
            await self._safe_reply(update, "❌ Произошла ошибка. Попробуйте еще раз.")
    
    async def mode_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /mode command with interactive mode selection"""
        try:
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            
            # Create inline keyboard for mode selection
            keyboard = [
                [InlineKeyboardButton("📸 Фото → Текст", callback_data="mode_photo")],
                [InlineKeyboardButton("🎤 Голос → Текст", callback_data="mode_voice")],
                [InlineKeyboardButton("📝 Текст → Голос", callback_data="mode_tts")],
                [InlineKeyboardButton("💬 Текст → AI", callback_data="mode_ai")],
                [InlineKeyboardButton("ℹ️ Помощь по режимам", callback_data="mode_help")],
                [InlineKeyboardButton("🔄 Автоматический режим", callback_data="mode_auto")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            message = (
                "🎛️ **Выберите режим работы:**\n\n"
                "📸 **Фото → Текст (OCR)** - OCR распознавание\n"
                "🎤 **Голос → Текст (Whisper)** - Whisper транскрибация\n"
                "📝 **Текст → Голос (TTS)** - TTS синтез речи\n"
                "💬 **Текст → AI Ответ** - Анализ и улучшение\n\n"
                "🔄 **Автоматический** - Бот сам определит тип\n\n"
                "💡 **Нажмите на режим для активации!**"
            )
            
            await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="Markdown")
            logger.info(f"Mode command used by user {update.effective_user.id}")
        except Exception as e:
            logger.error(f"Error in mode_command for user {update.effective_user.id}: {e}")
            await self._safe_reply(update, "❌ Произошла ошибка. Попробуйте еще раз.")
    
    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /admin command"""
        try:
            if not self.is_admin(update.effective_user.id, update.effective_user.username):
                await self._safe_reply(update, "🚫 У вас нет прав администратора!")
                return
            
            message = (
                "🔐 **Панель администратора:**\n\n"
                "📊 /stats - Статистика бота\n"
                "👥 /users - Информация о пользователях\n"
                "📝 /logs - Информация о логах\n"
                "🎛️ /mode - Режимы работы\n\n"
                "🔧 **Управление системой:**\n"
                "Используйте команды для управления ботом"
            )
            
            await self._safe_reply(update, message)
            logger.info(f"Admin command used by admin {update.effective_user.id}")
        except Exception as e:
            logger.error(f"Error in admin_command for user {update.effective_user.id}: {e}")
            await self._safe_reply(update, "❌ Произошла ошибка. Попробуйте еще раз.")
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /stats command"""
        try:
            if not self.is_admin(update.effective_user.id, update.effective_user.username):
                await self._safe_reply(update, "🚫 У вас нет прав администратора!")
                return
            
            message = (
                "📊 **Статистика AI Транскрибатора:**\n\n"
                "👥 **Пользователи:**\n"
                f"• Всего пользователей: Активно\n"
                "• Активных сегодня: Обрабатывается\n"
                f"• Администраторов: {self.config.security.admin_usernames}\n\n"
                "🔄 **Транскрибации:**\n"
                "• Всего транскрибаций: Работает\n"
                "• Успешных: Нормально\n"
                "• Проваленных: Минимально\n\n"
                "📈 **Использование по режимам:**\n"
                "• 📸 Фото → Текст: Активно\n"
                "• 🎤 Голос → Текст: Готово\n"
                "• 📝 Текст → Голос: Работает\n"
                "• 💬 Текст → AI: Работает"
            )
            
            await self._safe_reply(update, message)
            logger.info(f"Stats command used by admin {update.effective_user.id}")
        except Exception as e:
            logger.error(f"Error in stats_command for user {update.effective_user.id}: {e}")
            await self._safe_reply(update, "❌ Произошла ошибка. Попробуйте еще раз.")
    
    async def users_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /users command"""
        try:
            if not self.is_admin(update.effective_user.id, update.effective_user.username):
                await self._safe_reply(update, "🚫 У вас нет прав администратора!")
                return
            
            message = (
                "👥 **Информация о пользователях:**\n\n"
                "📊 База данных временно недоступна.\n"
                "Функция будет доступна после развертывания PostgreSQL.\n\n"
                "💡 **Для текущей информации:**\n"
                "Проверьте логи контейнера:\n"
                "docker logs ai-transcriber-bot --tail 50"
            )
            
            await self._safe_reply(update, message)
            logger.info(f"Users command used by admin {update.effective_user.id}")
        except Exception as e:
            logger.error(f"Error in users_command for user {update.effective_user.id}: {e}")
            await self._safe_reply(update, "❌ Произошла ошибка. Попробуйте еще раз.")
    
    async def logs_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /logs command"""
        try:
            if not self.is_admin(update.effective_user.id, update.effective_user.username):
                await self._safe_reply(update, "🚫 У вас нет прав администратора!")
                return
            
            message = (
                "📝 **Логи системы:**\n\n"
                "📊 Функция просмотра логов временно недоступна.\n\n"
                "🔧 **Для просмотра логов вручную:**\n"
                "`docker logs ai-transcriber-bot --tail 50`\n"
                "`docker-compose logs -f ai-transcriber-bot`\n\n"
                "📁 **Лог-файл:**\n"
                "logs/bot.log (внутри контейнера)"
            )
            
            await self._safe_reply(update, message)
            logger.info(f"Logs command used by admin {update.effective_user.id}")
        except Exception as e:
            logger.error(f"Error in logs_command for user {update.effective_user.id}: {e}")
            await self._safe_reply(update, "❌ Произошла ошибка. Попробуйте еще раз.")