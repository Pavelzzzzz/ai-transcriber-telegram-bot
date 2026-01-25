"""
Administrative handlers for AI Transcriber Bot with simplified logic
"""

import logging
from typing import Dict, Any
from datetime import datetime

from telegram import Update, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import BotConfig
from .exceptions import BotError, error_handler
from .user_manager import UserManager

logger = logging.getLogger(__name__)


class AdminHandlers:
    """
    Administrative command handlers with simplified logic
    """
    
    def __init__(self, config: BotConfig, user_manager: UserManager):
        self.config = config
        self.user_manager = user_manager
    
    async def _safe_reply(self, update: Update, text: str, parse_mode: str = None) -> bool:
        """Safely reply to a message"""
        try:
            if update and update.message:
                await update.message.reply_text(text, parse_mode=parse_mode)
                return True
        except Exception as e:
            logger.error(f"Error replying to message: {e}")
        return False
    
    def _is_admin(self, user_id: int, username: str = None) -> bool:
        """Check if user is admin"""
        if username and username.lower() in [name.lower() for name in self.config.security.admin_usernames]:
            return True
        if user_id in self.config.security.admin_ids:
            return True
        return False
    
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
            stats = await self.user_manager.get_global_stats()
            
            message = f"""
📊 **Статистика бота:**

👥 **Пользователи:**
• Всего: {stats.get('users', {}).get('total', 0)}
• Заблокировано: {stats.get('users', {}).get('blocked', 0)}
• Администраторов: {stats.get('users', {}).get('admins', 0)}
• Активно сегодня: {stats.get('users', {}).get('active_today', 0)}

📈 **Транскрипции:**
• Всего: {stats.get('transcriptions', {}).get('total', 0)}
• Успешных: {stats.get('transcriptions', {}).get('successful', 0)}
• Неудачных: {stats.get('transcriptions', {}).get('failed', 0)}
• Успешность: {stats.get('transcriptions', {}).get('success_rate', 0):.1f}%

⏰ **Время:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            
            await query.edit_message_text(message)
            
        except Exception as e:
            logger.error(f"Error in stats callback: {e}")
            await query.edit_message_text("❌ Ошибка получения статистики")
    
    async def _handle_users_callback(self, update: Update, query):
        """Handle users callback"""
        try:
            users = await self.user_manager.get_all_users(limit=15)
            
            if not users:
                await query.edit_message_text("👥 Пользователи не найдены")
                return
            
            message = f"👥 **Пользователи (первые {len(users)}):**\n\n"
            
            for user in users:
                status_emoji = "🟢" if not user.get('is_blocked', False) else "🚫"
                admin_emoji = "👑" if user.get('role') == 'ADMIN' else "👤"
                
                last_activity = user.get('last_activity')
                if last_activity:
                    try:
                        formatted_time = last_activity.strftime('%d.%m.%Y %H:%M')
                    message += f"📅 {formatted_time}\n"
                    except:
                        message += f"Дата: {last_activity}\n"
                else:
                    message += "Никогда\n"
                
                message += f"{status_emoji} {admin_emoji} **{user.get('username', 'Unknown'}**\n"
                message += f"🆔 {user.get('telegram_id')}\n"
                
                message += f"🕐 Регистрация: {user.get('created_at', 'Н/Д') if user.get('created_at') else 'Н/Д'}\n"
                message += f"🕐 Текущий режим: {user.get('current_mode', 'Не выбран'}\n"
                message += f"{'─' * 30}\n"
            
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
                message += f"\n\n📂 **Всего файлов:** {len(log_files)}"
                message += f"\n📂 **Директория:** {log_dir}"
            else:
                message += "• Логи не найдены"
                message += f"\n\n📂 **Директория:** {log_dir}"
            
            await query.edit_message_text(message)
            
        except Exception as e:
            logger.error(f"Error in logs callback: {e}")
            await query.edit_message_text("❌ Ошибка получения логов")
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /stats command"""
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
            stats = await self.user_manager.get_global_stats()
            
            message = f"""
📊 **Статистика AI Транскрибатора:**

👥 **Пользователи:**
• Всего: {stats.get('users', {}).get('total', 0)}
• Заблокировано: {stats.get('users', {}).get('blocked', 0)}
• Администраторов: {stats.get('users', {}).get('admins', 0)}
• Активно сегодня: {stats.get('users', {}).get('active_today', 0)}

📈 **Транскрипции:**
• Всего: {stats.get('transcriptions', {}).get('total', 0)}
• Успешных: {stats.get('transcriptions', {}).get('successful', 0)}
• Неудачных: {stats.get('transcriptions', {}).get('failed', 0)}
• Успешность: {stats.get('transcriptions', {}).get('success_rate', 0):.1f}%

⏰ **Время:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🎛️ **Использование режимов:**
"""
            
            # Add mode distribution
            modes = stats.get('modes', {})
            for mode, count in modes.items():
                mode_names = {
                    'img_to_text': '📸 Изображение → Текст',
                    'audio_to_text': '🎤 Аудио → Текст',
                    'text_to_audio': '🔊 Текст → Аудио',
                    'text_to_text': '💬 Текст → Ответ'
                }
                message += f"• {mode_names.get(mode, mode)}: {count}\n"
            
            message += f"""
🤖 **Бот активен и обрабатывает запросы!**"""
            
            await self._safe_reply(update, message.strip())
                
        except Exception as e:
            error = error_handler.handle_error(e, user_id=update.effective_user.id if update.effective_user else None)
            await self._safe_reply(update, f"❌ Ошибка получения статистики. Попробуйте позже.")
    
    async def users_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /users command"""
        try:
            if not update.effective_user:
                return
                
            if not self._is_admin(
                update.effective_user.id,
                update.effective_user.username
            ):
                await self._safe_reply(update, "❌ Доступ запрещен. Требуются права администратора.")
                return
            
            # Get users list
            users = await self.user_manager.get_all_users(limit=15)
            
            if not users:
                await self._safe_reply(update, "👥 Пользователи не найдены.")
                return
            
            message = f"👥 **Пользователи (первые {len(users)}):**\n\n"
            
            for user in users:
                status_emoji = "🟢" if not user.get('is_blocked', False) else "🚫"
                admin_emoji = "👑" if user.get('role') == 'ADMIN' else "👤"
                
                last_activity = user.get('last_activity')
                if last_activity:
                    try:
                        formatted_time = last_activity.strftime('%d.%m.%Y %H:%M')
                        message += f"📅 {formatted_time}\n"
                    except:
                        message += f"Дата: {last_activity}\n"
                else:
                    message += "Никогда\n"
                
                message += f"{status_emoji} {admin_emoji} **{user.get('username', 'Unknown'}**\n"
                message += f"🆔 {user.get('telegram_id')}\n"
                message += f"🕐 Регистрация: {user.get('created_at', 'Н/Д') if user.get('created_at') else 'Н/Д'}\n"
                message += f"🕐 Текущий режим: {user.get('current_mode', 'Не выбран'}\n"
                message += f"{'─' * 30}\n"
            
            await self._safe_reply(update, message.strip())
                
        except Exception as e:
            error = error_handler.handle_error(e, user_id=update.effective_user.id if update.effective_user else None)
            await self._safe_reply(update, f"❌ Ошибка получения списка пользователей. Попробуйте позже.")
    
    async def logs_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /logs command"""
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
                        
            except Exception as e:
                logger.error(f"Error checking log directory: {e}")
            
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
• Пользователи: Работают с запросами
• Обработка: Все режимы активны

💡 **Рекомендации:**
• Для просмотра полного лога используйте файловый менеджер
• При необходимости можно очистить старые логи
• Для отладки используйте уровень DEBUG в LOG_LEVEL
"""
            
            await self._safe_reply(update, message.strip())
                
        except Exception as e:
            error = error_handler.handle_error(e, user_id=update.effective_user.id if update.effective_user else None)
            await self._safe_reply(update, f"❌ Ошибка получения логов. Попробуйте позже.")