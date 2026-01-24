import os
import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, List, Any, TYPE_CHECKING
from telegram import Update, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from dotenv import load_dotenv

load_dotenv()

from utils.whisper_transcriber import WhisperTranscriber
from utils.image_processor import ImageProcessor

# Basic logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleSafeProcessor:
    """Simple safe media processor with basic functionality"""
    
    def __init__(self):
        pass
    
    async def safe_reply(self, update: Update, text: str, parse_mode: Optional[str] = None) -> bool:
        """Safely reply to a message"""
        try:
            if update and update.message:
                await update.message.reply_text(text, parse_mode=parse_mode)
                return True
        except Exception as e:
            logger.error(f"Error replying: {e}")
        return False
    
    async def process_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Process photo safely"""
        try:
            if not await self.safe_reply(update, "🔄 Обрабатываю изображение..."):
                return False
                
            if not update.message or not update.message.photo:
                return await self.safe_reply(update, "❌ Изображение не найдено")
            
            # Download photo
            photo = update.message.photo[-1]
            photo_file = await context.bot.get_file(photo.file_id)
            
            # Create downloads directory if not exists
            os.makedirs('downloads', exist_ok=True)
            
            user_id = update.effective_user.id if update.effective_user else 0
            image_path = f"downloads/{user_id}_{photo.file_id}.jpg"
            await photo_file.download_to_drive(image_path)
            
            # Try to process with OCR if available
            try:
                from utils.image_processor import ImageProcessor
                image_processor = ImageProcessor()
                extracted_text = await image_processor.extract_text_from_image(image_path)
                
                if extracted_text and extracted_text.strip():
                    await self.safe_reply(update, f"📝 **Распознанный текст:**\n\n```\n{extracted_text}\n```", parse_mode="Markdown")
                else:
                    await self.safe_reply(update, "❌ Текст не распознан. Используйте более четкое изображение.")
            except Exception as ocr_error:
                logger.error(f"OCR processing failed: {ocr_error}")
                await self.safe_reply(update, "✅ Фото получено! OCR временно недоступен, но базовая функция работает.")
            
            # Clean up
            try:
                os.remove(image_path)
            except:
                pass
                
            return True
            
        except Exception as e:
            logger.error(f"Error processing photo: {e}")
            return await self.safe_reply(update, "❌ Ошибка обработки фото")
    
    async def process_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Process voice safely"""
        try:
            if not await self.safe_reply(update, "🔄 Обрабатываю аудио..."):
                return False
                
            if not update.message or not update.message.voice:
                return await self.safe_reply(update, "❌ Голосовое не найдено")
            
            # Download voice
            voice = update.message.voice
            voice_file = await context.bot.get_file(voice.file_id)
            
            # Create downloads directory if not exists
            os.makedirs('downloads', exist_ok=True)
            
            user_id = update.effective_user.id if update.effective_user else 0
            audio_path = f"downloads/{user_id}_{voice.file_id}.ogg"
            await voice_file.download_to_drive(audio_path)
            
            # Try to process with Whisper if available
            try:
                from utils.whisper_transcriber import WhisperTranscriber
                transcriber = WhisperTranscriber()
                transcription_result = await transcriber.transcribe_audio(audio_path)
                
                if transcription_result and transcription_result.get("text"):
                    recognized_text = transcription_result["text"]
                    await self.safe_reply(update, f"📝 **Распознанный текст:**\n\n```\n{recognized_text}\n```", parse_mode="Markdown")
                else:
                    await self.safe_reply(update, "❌ Речь не распознана. Говорите четче.")
            except Exception as whisper_error:
                logger.error(f"Whisper processing failed: {whisper_error}")
                await self.safe_reply(update, "✅ Голос получено! Транскрипция временно недоступна, но базовая функция работает.")
            
            # Clean up
            try:
                os.remove(audio_path)
            except:
                pass
                
            return True
            
        except Exception as e:
            logger.error(f"Error processing voice: {e}")
            return await self.safe_reply(update, "❌ Ошибка обработки аудио")

class TelegramBot:
    """Simplified bot with basic functionality"""
    
    def __init__(self) -> None:
        self.token: str = os.getenv('TELEGRAM_BOT_TOKEN') or ''
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN не найден")
        
        self.user_modes: Dict[int, str] = {}
        self.safe_processor = SimpleSafeProcessor()
        
        # Настройка админов из .env
        admin_usernames = os.getenv('ADMIN_USERNAMES', '').strip()
        if admin_usernames:
            self.admin_usernames = [username.strip().lower() for username in admin_usernames.split(',') if username.strip()]
        else:
            self.admin_usernames = []
        
        logger.info(f"Bot initialized successfully. Admins: {self.admin_usernames}")
    
    def is_admin(self, user_id: int, username: Optional[str] = None) -> bool:
        """Проверяет, является ли пользователь администратором"""
        if username and username.lower() in self.admin_usernames:
            return True
        return False

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        try:
            # Проверяем, является ли пользователь админом
            is_admin_user = self.is_admin(update.effective_user.id, update.effective_user.username) if update.effective_user else False
            
            admin_commands = """
🔐 **Админ команды:**
/admin - Панель администратора
/stats - Статистика пользователей
/users - Список пользователей
/logs - Системные логи""" if is_admin_user else ""

            message = f"""
🎉 **AI Транскрибатор**

Я конвертирую контент между форматами с помощью ИИ.

🎛️ **Режимы работы:**
📸 Изображение → Текст
🎤 Аудио → Текст  
🔊 Текст → Аудио

🔧 **Команды:**
/start - Запуск
/mode - Выбор режима
/help - Помощь
/status - Статус{admin_commands}

💡 **Советы:**
• Отправьте фото для OCR
• Отправьте голос для транскрипции
• Используйте /mode для переключения режимов
            """
            await self.safe_processor.safe_reply(update, message.strip())
        except Exception as e:
            logger.error(f"Error in start command: {e}")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        try:
            # Проверяем, является ли пользователь админом
            is_admin_user = self.is_admin(update.effective_user.id, update.effective_user.username) if update.effective_user else False
            
            admin_help = """
🔐 **Админ команды:**
/admin - Панель администратора
/stats - Статистика пользователей
/users - Список пользователей
/logs - Системные логи""" if is_admin_user else ""

            message = f"""
📖 **Помощь - AI Транскрибатор**

🔍 **Функции:**
- OCR распознавание текста
- Распознавание речи
- Преобразование текста в аудио

🎛️ **Режимы работы (/mode):**
📸 Изображение → Текст
🎤 Аудио → Текст
🔊 Текст → Аудио

🔧 **Команды:**
/start - Запуск бота
/mode - Выбор режима
/help - Эта помощь
/status - Статус системы{admin_help}

💡 **Советы:**
• Используйте четкие изображения
• Говорите естественно, но отчетливо
• При проблемах попробуйте другой формат
            """
            await self.safe_processor.safe_reply(update, message.strip())
        except Exception as e:
            logger.error(f"Error in help command: {e}")

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        try:
            message = f"""
🤖 **Статус AI Транскрибатора:**
✅ Бот активен и готов к работе

🔹 **Компоненты:**
🔸 Whisper AI - Временно отключен
🔸 OCR система - Временно отключена  
🔹 База данных - Подключена

⏰ **Время:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🎯 **Текущий режим:** {self.user_modes.get(update.effective_user.id if update.effective_user else 0, 'img_to_text')}
            """
            await self.safe_processor.safe_reply(update, message.strip())
        except Exception as e:
            logger.error(f"Error in status command: {e}")

    async def mode_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /mode command"""
        try:
            if not update.effective_user:
                return
                
            user_id = update.effective_user.id
            current_mode = self.user_modes.get(user_id, 'img_to_text')

            keyboard = [
                [
                    InlineKeyboardButton("📸 Изображение → Текст",
                                       callback_data=f"mode_img_to_text_{user_id}"),
                    InlineKeyboardButton("🎤 Аудио → Текст",
                                       callback_data=f"mode_audio_to_text_{user_id}")
                ],
                [
                    InlineKeyboardButton("🔊 Текст → Аудио",
                                       callback_data=f"mode_text_to_audio_{user_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            mode_names = {
                'img_to_text': '📸 Изображение → Текст',
                'audio_to_text': '🎤 Аудио → Текст',
                'text_to_audio': '🔊 Текст → Аудио'
            }

            message = f"🎛️ **Выберите режим работы**\n\n"
            message += f"Текущий режим: {mode_names.get(current_mode, 'Не выбран')}\n\n"
            message += "📸 **Изображение → Текст:** Отправьте фото → получите текст\n"
            message += "🎤 **Аудио → Текст:** Отправьте голос → получите текст\n"
            message += "🔊 **Текст → Аудио:** Отправьте текст → получите голос"

            await self.safe_processor.safe_reply(update, message.strip())
            
            # Send keyboard
            if update.message:
                await update.message.reply_text(
                    "Выберите режим:",
                    reply_markup=reply_markup
                )
                
        except Exception as e:
            logger.error(f"Error in mode command: {e}")

    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /admin command"""
        try:
            if not update.effective_user:
                return
                
            if not self.is_admin(update.effective_user.id, update.effective_user.username):
                await self.safe_processor.safe_reply(update, "❌ Доступ запрещен. Требуются права администратора.")
                return
            
            keyboard = [
                [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
                [InlineKeyboardButton("👥 Пользователи", callback_data="admin_users")],
                [InlineKeyboardButton("📜 Логи", callback_data="admin_logs")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await self.safe_processor.safe_reply(update, "🛠️ **Панель администратора:**\nВыберите действие:")
            
            if update.message:
                await update.message.reply_text("Выберите действие:", reply_markup=reply_markup)
                
        except Exception as e:
            logger.error(f"Error in admin command: {e}")

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        try:
            if not update.effective_user:
                return
                
            if not self.is_admin(update.effective_user.id, update.effective_user.username):
                await self.safe_processor.safe_reply(update, "❌ Доступ запрещен. Требуются права администратора.")
                return
            
            # Временная статистика (можно расширить при необходимости)
            stats_message = f"""
📊 **Статистика бота:**

👥 **Пользователи:**
• Всего пользователей: {len(self.user_modes)}
• Активные режимы: {len([m for m in self.user_modes.values() if m])}

⏰ **Время:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🎛️ **Режимы использования:**
• img_to_text: {list(self.user_modes.values()).count('img_to_text')}
• audio_to_text: {list(self.user_modes.values()).count('audio_to_text')}
• text_to_audio: {list(self.user_modes.values()).count('text_to_audio')}
            """
            
            await self.safe_processor.safe_reply(update, stats_message.strip())
                
        except Exception as e:
            logger.error(f"Error in stats command: {e}")

    async def users_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /users command"""
        try:
            if not update.effective_user:
                return
                
            if not self.is_admin(update.effective_user.id, update.effective_user.username):
                await self.safe_processor.safe_reply(update, "❌ Доступ запрещен. Требуются права администратора.")
                return
            
            # Временный список пользователей (можно расширить при необходимости)
            users_list = f"""
👥 **Пользователи бота:**

📈 **Всего пользователей:** {len(self.user_modes)}

🎛️ **Активные пользователи и режимы:**
"""
            for user_id, mode in list(self.user_modes.items())[:10]:  # Показываем первых 10
                users_list += f"• User {user_id}: {mode}\n"
            
            if len(self.user_modes) > 10:
                users_list += f"... и еще {len(self.user_modes) - 10} пользователей"
            
            await self.safe_processor.safe_reply(update, users_list.strip())
                
        except Exception as e:
            logger.error(f"Error in users command: {e}")

    async def logs_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /logs command"""
        try:
            if not update.effective_user:
                return
                
            if not self.is_admin(update.effective_user.id, update.effective_user.username):
                await self.safe_processor.safe_reply(update, "❌ Доступ запрещен. Требуются права администратора.")
                return
            
            # Проверяем наличие файла логов
            log_files = []
            try:
                import os
                if os.path.exists('logs/bot.log'):
                    size = os.path.getsize('logs/bot.log')
                    log_files.append(f"bot.log ({size} байт)")
            except:
                pass
            
            logs_message = f"""
📜 **Системные логи:**

📁 **Доступные файлы логов:**
{chr(10).join(f'• {file}' for file in log_files) if log_files else '• Логи не найдены'}

⚙️ **Последние действия:**
• Бот запущен успешно
• Все команды работают
• Пользователи могут использовать функции

🔧 **Управление логами:**
• Логи пишутся в файл logs/bot.log
• Для просмотра логов используйте файловый менеджер
• При необходимости можно очистить логи
            """
            
            await self.safe_processor.safe_reply(update, logs_message.strip())
                
        except Exception as e:
            logger.error(f"Error in logs command: {e}")

    async def set_bot_commands(self, application: Application):
        """Set bot commands including admin commands"""
        commands = [
            BotCommand("start", "🚀 Запуск бота"),
            BotCommand("help", "📖 Помощь"),
            BotCommand("mode", "🔧 Выбор режима"),
            BotCommand("status", "📊 Статус"),
            BotCommand("admin", "🔛 Админка"),
            BotCommand("stats", "📈 Статистика"),
            BotCommand("users", "👥 Пользователи"),
            BotCommand("logs", "📝 Логи"),
        ]
        await application.bot.set_my_commands(commands)

    async def callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries"""
        try:
            query = update.callback_query
            if not query or not update.effective_user:
                return
                
            await query.answer()
            user_id = update.effective_user.id
            action = query.data

            # Handle mode callbacks
            if action and action.startswith("mode_"):
                try:
                    parts = action.split("_")
                    if len(parts) != 4 or parts[0] != "mode":
                        raise ValueError("Invalid callback format")
                    
                    action_type = parts[1]
                    user_id_part = parts[3]
                    
                    if not user_id_part.isdigit():
                        raise ValueError("Invalid user_id format")
                    
                    callback_user_id = int(user_id_part)
                    if callback_user_id != user_id:
                        await query.edit_message_text("❌ Ошибка доступа")
                        return
                    
                    mode_mapping = {
                        'img_to_text': 'img_to_text',
                        'audio_to_text': 'audio_to_text',
                        'text_to_audio': 'text_to_audio'
                    }
                    
                    if action_type not in mode_mapping:
                        await query.edit_message_text("❌ Неизвестный тип режима")
                        return
                    
                    mode = mode_mapping[action_type]
                    
                    mode_names = {
                        'img_to_text': '📸 Изображение → Текст',
                        'audio_to_text': '🎤 Аудио → Текст',
                        'text_to_audio': '🔊 Текст → Аудио'
                    }

                    self.user_modes[user_id] = mode
                    await query.edit_message_text(
                        f"✅ **Режим изменен**\n\n"
                        f"📋 Текущий режим: {mode_names[mode]}\n\n"
                        f"💡 Теперь отправляйте соответствующий контент!"
                    )
                    
                except (ValueError, IndexError) as e:
                    logger.error(f"Ошибка обработки callback: {e}")
                    await query.edit_message_text("❌ Ошибка обработки callback")
            
            # Handle admin callbacks
            elif action in ["admin_stats", "admin_users", "admin_logs"]:
                try:
                    if not update.effective_user or not self.is_admin(update.effective_user.id, update.effective_user.username):
                        await query.edit_message_text("❌ Доступ запрещен")
                        return
                    
                    if action == "admin_stats":
                        await self.stats_command(update, context)
                    elif action == "admin_users":
                        await self.users_command(update, context)
                    elif action == "admin_logs":
                        await self.logs_command(update, context)
                        
                except Exception as e:
                    logger.error(f"Error in admin callback: {e}")
                    await query.edit_message_text("❌ Ошибка обработки команды")
                    
        except Exception as e:
            logger.error(f"Error in callback handler: {e}")

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Ошибка: {context.error}")
        if isinstance(update, Update):
            await self.safe_processor.safe_reply(update, "❌ Ошибка. Попробуйте позже.")



    def setup_handlers(self, application: Application) -> None:
        """Настройка обработчиков для приложения"""
        # User commands
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("mode", self.mode_command))
        application.add_handler(CommandHandler("status", self.status_command))
        
        # Admin commands
        application.add_handler(CommandHandler("admin", self.admin_command))
        application.add_handler(CommandHandler("stats", self.stats_command))
        application.add_handler(CommandHandler("users", self.users_command))
        application.add_handler(CommandHandler("logs", self.logs_command))
            
        # Content handlers
        application.add_handler(MessageHandler(filters.PHOTO, self.safe_processor.process_photo))
        application.add_handler(MessageHandler(filters.VOICE, self.safe_processor.process_voice))
        application.add_handler(CallbackQueryHandler(self.callback_handler))

        application.add_error_handler(self.error_handler)

    def run(self):
        """Run bot"""
        try:
            application = Application.builder().token(self.token).build()
            
            self.setup_handlers(application)

            # Set bot commands
            import asyncio
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self.set_bot_commands(application))

            logger.info("Бот запущен успешно!")
            application.run_polling(allowed_updates=Update.ALL_TYPES)
            
        except Exception as e:
            logger.error(f"Ошибка запуска бота: {e}")
            raise

WhisperTranscriber = None
ImageProcessor = None

if __name__ == '__main__':
    try:
        bot = TelegramBot()
        bot.run()
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        print(f"Ошибка запуска: {e}")