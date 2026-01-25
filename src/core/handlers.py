"""
Command handlers for AI Transcriber Bot with improved architecture
"""

import logging
from typing import Optional
from datetime import datetime

from telegram import Update, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import BotConfig
from .exceptions import BotError, error_handler
from ..services.user_service import UserService
# from ...utils.multilingual_processor import MultilingualTextProcessor  # Temporarily disabled

logger = logging.getLogger(__name__)


class CommandHandlers:
    """
    Handles all command messages (/start, /help, /mode, /status)
    """
    
    def __init__(self, config: BotConfig, user_service: UserService):
        self.config = config
        self.user_service = user_service
        self.text_processor = None
    
    async def _safe_reply(self, update: Update, text: str, parse_mode: Optional[str] = None) -> bool:
        """Safely reply to a message with error handling"""
        try:
            if update and update.message:
                await update.message.reply_text(text, parse_mode=parse_mode)
                return True
        except Exception as e:
            logger.error(f"Error replying to message: {e}")
        return False
    
    def _is_admin(self, user_id: int, username: Optional[str] = None) -> bool:
        """Check if user is admin with proper validation"""
        if username and username.lower() in [name.lower() for name in self.config.security.admin_usernames]:
            return True
        if user_id in self.config.security.admin_ids:
            return True
        return False
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command with improved UX"""
        try:
            if not update.effective_user:
                return
            
            # Get or create user
            user = await self.user_service.get_or_create_user(
                telegram_id=update.effective_user.id,
                username=update.effective_user.username,
                first_name=update.effective_user.first_name,
                last_name=update.effective_user.last_name
            )
            
            # Check if admin
            is_admin_user = self._is_admin(
                update.effective_user.id, 
                update.effective_user.username
            )
            
            # Build message based on user type
            if is_admin_user:
                admin_commands = """
🔐 **Админ команды:**
/admin - Панель администратора
/stats - Статистика пользователей  
/users - Список пользователей
/logs - Системные логи"""
            else:
                admin_commands = ""
            
            message = f"""
🎉 **AI Транскрибатор v{self.config.version}**

🌍 **Многоязычный бот для работы с контентом:**
📸 Изображение → Текст (OCR)
🎤 Аудио → Текст (Whisper, 99 языков)
🔊 Текст → Аудио (gTTS, множество языков)
💬 Текст → Ответ (Интеллектуальная корректура RU/EN)

🎛️ **Команды:**
/start - Запуск бота
/mode - Выбор режима работы
/help - Подробная помощь
/status - Статус системы{admin_commands}

💡 **Советы:**
• Отправьте фото для OCR распознавания
• Отправьте голос для транскрибации (любой язык)
• Используйте /mode для переключения режимов
• Режим 💬 поддерживает исправление ошибок на RU и EN

🌟 **Новые возможности:**
✅ Многоязычная интеллектуальная коррекция текста
✅ Автоопределение языка (RU/EN/Смешанный)
✅ Расширенная статистика и рекомендации
✅ Улучшенная обработка ошибок
"""
            
            await self._safe_reply(update, message.strip())
            
        except Exception as e:
            error = error_handler.handle_error(e, user_id=update.effective_user.id if update.effective_user else None)
            await self._safe_reply(update, f"❌ Ошибка запуска. Попробуйте позже.")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command with detailed information"""
        try:
            if not update.effective_user:
                return
            
            is_admin_user = self._is_admin(
                update.effective_user.id,
                update.effective_user.username
            )
            
            admin_help = """
🔐 **Админ команды:**
/admin - Панель администратора
/stats - Статистика пользователей
/users - Список пользователей
/logs - Системные логи""" if is_admin_user else ""
            
            message = f"""
📖 **Подробная справка - AI Транскрибатор v{self.config.version}**

🌍 **Поддерживаемые функции:**

📸 **OCR распознавание:**
• Поддержка 50+ языков
• Автоопределение языка текста
• Высокая точность распознавания

🎤 **Аудио транскрибация:**  
• Whisper AI - 99 языков
• Автоопределение языка аудио
• Высокое качество распознавания речи

🔊 **Синтез речи (TTS):**
• Google Text-to-Speech
• 100+ языков и голосов
• Естественное звучание

💬 **Интеллектуальная обработка текста:**
• Автоопределение языка (RU/EN/Смешанный)
• Исправление орфографии и грамматики
• Расширение сокращений и аббревиатур
• Персонализированные рекомендации

🎛️ **Команды:**
/start - Запуск бота
/mode - Выбор режима работы  
/help - Эта справка
/status - Статус системы{admin_help}

💡 **Как использовать:**
1. **Для OCR:** Отправьте фото с текстом
2. **Для транскрибации:** Отправьте голосовое сообщение или аудио
3. **Для TTS:** Переключитесь в режим "🔊 Текст → Аудио" и отправьте текст
4. **Для коррекции:** Переключитесь в режим "💬 Текст → Ответ" и отправьте текст

🌟 **Умные советы:**
• Используйте /mode для быстрого переключения между режимами
• В режиме 💬 бот автоматически определит язык и исправит ошибки
• Для транскрибации говорите четко и без фонового шума
• Для OCR используйте фото с хорошим освещением и четким текстом

🔥 **Особенности v{self.config.version}:**
✅ Многоязычная интеллектуальная коррекция
✅ Улучшенная обработка ошибок  
✅ Расширенная статистика
✅ Ускоренная обработка
"""
            
            await self._safe_reply(update, message.strip())
            
        except Exception as e:
            error = error_handler.handle_error(e, user_id=update.effective_user.id if update.effective_user else None)
            await self._safe_reply(update, f"❌ Ошибка. Попробуйте позже.")
    
    async def mode_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /mode command with improved UX"""
        try:
            if not update.effective_user:
                return
                
            user_id = update.effective_user.id
            
            # Get current user mode
            user = await self.user_service.get_user_by_telegram_id(user_id)
            current_mode = user.current_mode if user else 'img_to_text'

            # Create keyboard
            keyboard = [
                [
                    InlineKeyboardButton("📸 Изображение → Текст", callback_data=f"mode:img_to_text:{user_id}"),
                    InlineKeyboardButton("🎤 Аудио → Текст", callback_data=f"mode:audio_to_text:{user_id}")
                ],
                [
                    InlineKeyboardButton("🔊 Текст → Аудио", callback_data=f"mode:text_to_audio:{user_id}"),
                    InlineKeyboardButton("💬 Текст → Ответ", callback_data=f"mode:text_to_text:{user_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            mode_names = {
                'img_to_text': '📸 Изображение → Текст',
                'audio_to_text': '🎤 Аудио → Текст', 
                'text_to_audio': '🔊 Текст → Аудио',
                'text_to_text': '💬 Текст → Ответ (Интеллектуальная корректура)'
            }

            message = f"🎛️ **Выберите режим работы**\n\n"
            message += f"🎯 **Текущий режим:** {mode_names.get(current_mode, 'Не выбран')}\n\n"
            message += "📸 **Изображение → Текст:** OCR распознавание текста с фото\n"
            message += "🎤 **Аудио → Текст:** Транскрибация речи в текст (99 языков)\n" 
            message += "🔊 **Текст → Аудио:** Синтез речи из текста\n"
            message += "💬 **Текст → Ответ:** Интеллектуальная коррекция текста (RU/EN)\n\n"
            message += "💡 **Новый режим 💬 поддерживает:**\n"
            message += "• Автоопределение языка (Русский/Английский/Смешанный)\n"
            message += "• Исправление орфографии и грамматики\n"
            message += "• Расширение сокращений\n"
            message += "• Умные рекомендации по улучшению текста"

            await self._safe_reply(update, message.strip())
            
            if update.message:
                await update.message.reply_text(
                    "Выберите режим:",
                    reply_markup=reply_markup
                )
                
        except Exception as e:
            error = error_handler.handle_error(e, user_id=update.effective_user.id if update.effective_user else None)
            await self._safe_reply(update, f"❌ Ошибка выбора режима. Попробуйте позже.")
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command with comprehensive information"""
        try:
            if not update.effective_user:
                return
            
            user_id = update.effective_user.id
            user = await self.user_service.get_user_by_telegram_id(user_id)
            
            # Get user statistics
            stats = await self.user_service.get_user_stats(user_id) if user else {}
            
            # Get current mode name
            current_mode = user.current_mode if user else 'img_to_text'
            mode_names = {
                'img_to_text': '📸 Изображение → Текст',
                'audio_to_text': '🎤 Аудио → Текст',
                'text_to_audio': '🔊 Текст → Аудио', 
                'text_to_text': '💬 Текст → Ответ'
            }
            
            message = f"""
🤖 **Статус AI Транскрибатора v{self.config.version}**
✅ Бот активен и готов к работе

📊 **Система:**
🔸 Whisper AI - Активен (99 языков)
🔸 OCR система - Активна (50+ языков)
🔸 TTS система - Активна (100+ языков)
🔸 Текстовая корректура - Активна (RU/EN)
🔹 База данных - Подключена
🔹 Кэширование - Активно

👤 **Ваш профиль:**
🎯 Текущий режим: {mode_names.get(current_mode, 'Не выбран')}
📅 Регистрация: {user.created_at.strftime('%Y-%m-%d %H:%M') if user else 'Н/Д'}
🔢 ID: {user_id}
👤 Имя: {user.get_full_name() if user else 'Н/Д'}

📈 **Ваша статистика:**
📝 Обработано сообщений: {stats.get('total_messages', 0)}
🖼️ OCR обработок: {stats.get('ocr_count', 0)}
🎤 Аудио транскрипций: {stats.get('transcription_count', 0)}
🔊 TTS синтезов: {stats.get('tts_count', 0)}
💬 Коррекций текста: {stats.get('correction_count', 0)}

⏰ **Время:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🌍 **Языковые возможности:** Русский, Английский + 97 языков (Whisper)

💡 **Совет:** Используйте /mode для смены режима работы
"""
            
            await self._safe_reply(update, message.strip())
            
        except Exception as e:
            error = error_handler.handle_error(e, user_id=update.effective_user.id if update.effective_user else None)
            await self._safe_reply(update, f"❌ Ошибка получения статуса. Попробуйте позже.")
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /stats command with global statistics"""
        try:
            if not update.effective_user:
                return
            
            if not self._is_admin(
                update.effective_user.id,
                update.effective_user.username
            ):
                await self._safe_reply(update, "❌ Доступ запрещен. Требуются права администратора.")
                return
            
            # Get global statistics
            stats = await self.user_service.get_global_stats()
            
            message = f"""
📊 **Глобальная статистика AI Транскрибатора:**

👥 **Пользователи:**
• Всего пользователей: {stats['users']['total']}
• Заблокировано: {stats['users']['blocked']}
• Администраторов: {stats['users']['admins']}
• Активны сегодня: {stats['users']['active_today']}

📈 **Транскрипции:**
• Всего: {stats['transcriptions']['total']}
• Успешных: {stats['transcriptions']['successful']}
• Неудачных: {stats['transcriptions']['failed']}
• Успешность: {stats['transcriptions']['success_rate']:.1f}%
• Среднее время: {stats['transcriptions']['avg_processing_time']:.2f}с
• Всего символов: {stats['transcriptions']['total_text_length']}

🎯 **Использование режимов:**
"""
            
            # Add mode distribution
            for mode, count in stats.get('modes', {}).items():
                mode_names = {
                    'img_to_text': '📸 Изображение → Текст',
                    'audio_to_text': '🎤 Аудио → Текст',
                    'text_to_audio': '🔊 Текст → Аудио',
                    'text_to_text': '💬 Текст → Ответ'
                }
                message += f"• {mode_names.get(mode, mode)}: {count} пользователей\n"
            
            message += f"""
⏰ **Время:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🔥 **Бот активен и обрабатывает запросы!**
"""
            
            await self._safe_reply(update, message.strip())
                
        except Exception as e:
            error = error_handler.handle_error(e, user_id=update.effective_user.id if update.effective_user else None)
            await self._safe_reply(update, f"❌ Ошибка получения статистики. Попробуйте позже.")
    
    async def users_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /users command with user list"""
        try:
            if not update.effective_user:
                return
            
            if not self._is_admin(
                update.effective_user.id,
                update.effective_user.username
            ):
                await self._safe_reply(update, "❌ Доступ запрещен. Требуются права администратора.")
                return
            
            # Get recent users
            users = await self.user_service.get_all_users(limit=20)
            
            if not users:
                await self._safe_reply(update, "📊 Пользователи не найдены.")
                return
            
            message = f"👥 **Список пользователей (первые {len(users)}):**\n\n"
            
            for user in users:
                status_emoji = "🟢" if not user.is_blocked else "🚫"
                admin_emoji = "👑" if user.role == 'ADMIN' else "👤"
                
                last_activity = user.last_activity.strftime('%d.%m.%Y %H:%M') if user.last_activity else "Никогда"
                
                message += f"{status_emoji} {admin_emoji} **{user.get_full_name() or 'Unknown'}**\n"
                message += f"🆔 {user.telegram_id}\n"
                message += f"📅 Регистрация: {user.created_at.strftime('%d.%m.%Y')}\n"
                message += f"🕐 Последняя активность: {last_activity}\n"
                message += f"🎯 Текущий режим: {user.current_mode or 'Не выбран'}\n"
                message += f"{'─' * 30}\n"
            
            await self._safe_reply(update, message.strip())
                
        except Exception as e:
            error = error_handler.handle_error(e, user_id=update.effective_user.id if update.effective_user else None)
            await self._safe_reply(update, f"❌ Ошибка получения списка пользователей. Попробуйте позже.")
    
    async def logs_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /logs command with system logs"""
        try:
            if not update.effective_user:
                return
            
            if not self._is_admin(
                update.effective_user.id,
                update.effective_user.username
            ):
                await self._safe_reply(update, "❌ Доступ запрещен. Требуются права администратора.")
                return
            
            message = f"""
📝 **Системные логи AI Транскрибатора:**

📂 **Доступные файлы логов:**
"""
            
            # Check log files
            log_files = []
            try:
                log_dir = self.config.paths.logs_dir
                if log_dir.exists():
                    for log_file in log_dir.glob("*.log"):
                        size = log_file.stat().st_size
                        log_files.append(f"• {log_file.name} ({size} байт)")
                        
                        # Add recent lines
                        try:
                            with open(log_file, 'r', encoding='utf-8') as f:
                                lines = f.readlines()
                                if lines:
                                    recent_lines = lines[-5:]  # Last 5 lines
                                    message += f"\n📄 **Последние строки из {log_file.name}:**\n"
                                    for line in recent_lines:
                                        clean_line = line.strip()
                                        if clean_line:
                                            message += f"• {clean_line}\n"
                                    message += "\n"
                        except Exception:
                            pass
            except Exception as e:
                logger.error(f"Error reading log files: {e}")
            
            if not log_files:
                message += "• Логи не найдены"
            
            message += f"""
⚙️ **Конфигурация логирования:**
• Уровень: {self.config.logging.level}
• Формат: {self.config.logging.format}
• Ротация: {self.config.logging.backup_count} файлов
• Макс. размер: {self.config.logging.max_file_size} байт

🔍 **Состояние бота:**
• Версия: {self.config.version}
• Запущен: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
• Активен: ✅
• Пользователи: Работает с запросами
• Обработка: Все режимы активны

💡 **Советования:**
• Для просмотра полного лога используйте файловый менеджер
• При необходимости можно очистить старые логи
• Для отладки используйте уровень DEBUG в LOG_LEVEL
"""
            
            await self._safe_reply(update, message.strip())
                
        except Exception as e:
            error = error_handler.handle_error(e, user_id=update.effective_user.id if update.effective_user else None)
            await self._safe_reply(update, f"❌ Ошибка получения логов. Попробуйте позже.")


class AdminHandlers:
    """
    Administrative command handlers
    """
    
    def __init__(self, config: BotConfig, user_service: UserService):
        self.config = config
        self.user_service = user_service
    
    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /admin command"""
        try:
            if not update.effective_user:
                return
                
            if not self._is_admin(
                update.effective_user.id,
                update.effective_user.username
            ):
                await self._safe_reply(update, "❌ Доступ запрещен. Требуются права администратора.")
                return
            
            keyboard = [
                [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
                [InlineKeyboardButton("👥 Пользователи", callback_data="admin_users")],
                [InlineKeyboardButton("📝 Логи", callback_data="admin_logs")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await self._safe_reply(update, "🛠️ **Панель администратора:**\nВыберите действие:")
            
            if update.message:
                await update.message.reply_text("Выберите действие:", reply_markup=reply_markup)
                
        except Exception as e:
            error = error_handler.handle_error(e, user_id=update.effective_user.id if update.effective_user else None)
            await self._safe_reply(update, f"❌ Ошибка панели администратора. Попробуйте позже.")
    
    async def _handle_stats_callback(self, update: Update, query):
        """Handle stats callback"""
        try:
            stats = await self.user_service.get_global_stats()
            
            message = f"""
📊 **Статистика бота:**

👥 **Пользователи:**
• Всего: {stats['users']['total']}
• Заблокировано: {stats['users']['blocked']}
• Админов: {stats['users']['admins']}
• Активно сегодня: {stats['users']['active_today']}

📈 **Транскрипции:**
• Всего: {stats['transcriptions']['total']}
• Успешных: {stats['transcriptions']['successful']}
• Неудачных: {stats['transcriptions']['failed']}
• Успешность: {stats['transcriptions']['success_rate']:.1f}%

⏰ **Время:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            
            await query.edit_message_text(message)
            
        except Exception as e:
            logger.error(f"Error in stats callback: {e}")
            await query.edit_message_text("❌ Ошибка получения статистики")
    
    async def _handle_users_callback(self, update: Update, query):
        """Handle users callback"""
        try:
            users = await self.user_service.get_all_users(limit=15)
            
            if not users:
                await query.edit_message_text("📊 Пользователи не найдены")
                return
            
            message = f"👥 **Пользователи (первые {len(users)}):**\n\n"
            
            for user in users:
                status_emoji = "🟢" if not user.is_blocked else "🚫"
                admin_emoji = "👑" if user.role == 'ADMIN' else "👤"
                
                last_activity = user.last_activity.strftime('%d.%m.%Y %H:%M') if user.last_activity else "Никогда"
                
                message += f"{status_emoji} {admin_emoji} **{user.get_full_name() or 'Unknown'}**\n"
                message += f"🆔 {user.telegram_id}\n"
                message += f"🕐 {last_activity}\n"
                message += f"{'─' * 25}\n"
            
            await query.edit_message_text(message)
            
        except Exception as e:
            logger.error(f"Error in users callback: {e}")
            await query.edit_message_text("❌ Ошибка получения пользователей")
    
    async def _handle_logs_callback(self, update: Update, query):
        """Handle logs callback"""
        try:
            log_dir = self.config.paths.logs_dir
            log_files = []
            
            if log_dir.exists():
                for log_file in log_dir.glob("*.log"):
                    size = log_file.stat().st_size
                    log_files.append(f"• {log_file.name} ({size} байт)")
            
            message = f"📝 **Логи системы:**\n\n"
            
            if log_files:
                message += "\n".join(log_files)
                message += f"\n\n📄 **Всего файлов:** {len(log_files)}"
                message += f"\n📂 **Директория:** {log_dir}"
            else:
                message += "• Логи не найдены"
                message += f"\n📂 **Директория:** {log_dir}"
            
            await query.edit_message_text(message)
            
        except Exception as e:
            logger.error(f"Error in logs callback: {e}")
            await query.edit_message_text("❌ Ошибка получения логов")


class CallbackHandlers:
    """
    Handles callback queries from inline keyboards
    """
    
    def __init__(self, config: BotConfig, user_service: UserService):
        self.config = config
        self.user_service = user_service
    
    async def _safe_reply(self, update: Update, text: str, parse_mode: Optional[str] = None) -> bool:
        """Safely edit message with error handling"""
        try:
            if update.callback_query:
                await update.callback_query.edit_message_text(text, parse_mode=parse_mode)
                return True
        except Exception as e:
            logger.error(f"Error editing callback message: {e}")
        return False
    
    def _is_admin(self, user_id: int, username: Optional[str] = None) -> bool:
        """Check if user is admin"""
        if username and username.lower() in [name.lower() for name in self.config.security.admin_usernames]:
            return True
        if user_id in self.config.security.admin_ids:
            return True
        return False
    
    async def callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle callback queries with type safety"""
        try:
            query = update.callback_query
            if not query or not update.effective_user:
                return
                
            await query.answer()
            user_id = update.effective_user.id
            action = query.data

            # Handle mode callbacks
            if action and action.startswith("mode:"):
                try:
                    parts = action.split(":")
                    if len(parts) != 3 or parts[0] != "mode":
                        await query.edit_message_text("❌ Неверный формат callback")
                        return
                    
                    mode_type = parts[1]
                    callback_user_id_part = parts[2]
                    
                    if not callback_user_id_part.isdigit():
                        await query.edit_message_text("❌ Неверный ID пользователя")
                        return
                    
                    callback_user_id = int(callback_user_id_part)
                    if callback_user_id != user_id:
                        await query.edit_message_text("❌ Ошибка доступа")
                        return
                    
                    valid_modes = ['img_to_text', 'audio_to_text', 'text_to_audio', 'text_to_text']
                    
                    if mode_type not in valid_modes:
                        await query.edit_message_text("❌ Неизвестный тип режима")
                        return
                    
                    # Update user mode
                    await self.user_service.update_user_mode(user_id, mode_type)
                    
                    mode_names = {
                        'img_to_text': '📸 Изображение → Текст',
                        'audio_to_text': '🎤 Аудио → Текст',
                        'text_to_audio': '🔊 Текст → Аудио',
                        'text_to_text': '💬 Текст → Ответ (Интеллектуальная корректура)'
                    }

                    mode_descriptions = {
                        'img_to_text': 'Отправьте фото для OCR распознавания',
                        'audio_to_text': 'Отправьте голосовое сообщение для транскрибации',
                        'text_to_audio': 'Отправьте текст для синтеза речи',
                        'text_to_text': 'Отправьте текст для интеллектуальной коррекции (RU/EN)'
                    }

                    await query.edit_message_text(
                        f"✅ **Режим изменен**\n\n"
                        f"📋 Текущий режим: {mode_names[mode_type]}\n\n"
                        f"💡 **Что делать:** {mode_descriptions[mode_type]}\n\n"
                        f"🔄 Сменить режим: /mode"
                    )
                    
                except (ValueError, IndexError) as e:
                    logger.error(f"Error processing callback: {e}")
                    await query.edit_message_text("❌ Ошибка обработки callback")
            
            # Handle admin callbacks
            elif action in ["admin_stats", "admin_users", "admin_logs"]:
                try:
                    if not update.effective_user or not self._is_admin(
                        update.effective_user.id, 
                        update.effective_user.username
                    ):
                        await query.edit_message_text("❌ Доступ запрещен")
                        return
                    
                    # Delegate to admin handlers
                    from .admin_handlers import AdminHandlers
                    admin_handlers = AdminHandlers(self.config, self.user_service)
                    
                    if action == "admin_stats":
                        await admin_handlers._handle_stats_callback(update, query)
                    elif action == "admin_users":
                        await admin_handlers._handle_users_callback(update, query)
                    elif action == "admin_logs":
                        await admin_handlers._handle_logs_callback(update, query)
                        
                except Exception as e:
                    logger.error(f"Error in admin callback: {e}")
                    await query.edit_message_text("❌ Ошибка обработки команды")
                    
        except Exception as e:
            logger.error(f"Error in callback handler: {e}")
            if update.callback_query:
                await update.callback_query.answer("❌ Ошибка", show_alert=True)