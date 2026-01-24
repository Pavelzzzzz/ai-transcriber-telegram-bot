import os
import logging
from datetime import datetime
from telegram import Update, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from dotenv import load_dotenv
from database.models import get_db, create_tables, TranscriptionType
from utils.admin_service import AdminService
from utils.whisper_transcriber import WhisperTranscriber
from utils.image_processor import ImageProcessor

load_dotenv()
logging.basicConfig(level=logging.INFO, handlers=[logging.FileHandler('logs/bot.log'), logging.StreamHandler()])
logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN не найден")

        self.transcriber = WhisperTranscriber()
        self.image_processor = ImageProcessor()
        create_tables()
        self.admin_service = None
        self.admin_usernames = [username.strip().lower() for username in os.getenv('ADMIN_USERNAMES', '').split(',') if username.strip()]
        self.user_modes = {}  # user_id -> mode

    def is_admin(self, user_id: int, username: str = None) -> bool:
        # Проверка по username из .env (быстро)
        if username and username.lower() in self.admin_usernames:
            return True

        # Проверка через базу данных (для динамических прав)
        db = next(get_db())
        try:
            return self.admin_service.is_admin(user_id) if self.admin_service else False
        finally:
            db.close()

    def get_admin_service(self):
        if not self.admin_service:
            db = next(get_db())
            self.admin_service = AdminService(db)
        return self.admin_service

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        admin_service = self.get_admin_service()
        user = admin_service.create_or_update_user(
            telegram_id=user_id,
            username=update.effective_user.username,
            first_name=update.effective_user.first_name,
            last_name=update.effective_user.last_name
        )

        admin_commands = """
🔐 **Админ команды:**
/admin - Панель администратора
/stats - Статистика
/users - Пользователи
/block <id> - Блокировка
/unblock <id> - Разблокировка
/logs - Логи""" if user.is_admin() else ""

        message = f"""
🎉 **AI Транскрибатор**

Я конвертирую контент между форматами с помощью ИИ.

🎛️ **Выберите режим работы:** /mode

📸 **Изображение → Текст:**
Отправьте фото с текстом → получите распознанный текст

🎤 **Аудио → Текст:**
Отправьте голосовое сообщение → получите транскрипцию

🔊 **Текст → Аудио:**
Отправьте текстовое сообщение → получите голосовое озвучивание

🔧 **Команды:**
/start - Запуск
/mode - Выбор режима работы
/help - Помощь
/status - Статус
/profile - Профиль
/history - История{admin_commands}

💡 **Советы:**
• Изображения: четкий текст, хорошее освещение
• Аудио: говорите четко, без шума
• Текст: до 5000 символов, поддержка русского и английского
        """
        await update.message.reply_text(message, parse_mode='Markdown')

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        admin_help = """
🔐 **Админ команды:**
/admin - Меню администрирования
/stats - Статистика
/users - Список пользователей
/block <id> - Блокировка
/unblock <id> - Разблокировка
/logs - Системные логи
/broadcast <msg> - Рассылка""" if self.is_admin(user_id) else ""

        message = f"""
📖 **Помощь - AI Транскрибатор**

🔍 **Функции:**
- OCR распознавание текста на изображениях
- Преобразование текста в аудио (TTS)
- Распознавание речи в голосовых сообщениях (ASR)
- Создание текстовых транскрипций

🎛️ **Режимы работы (/mode):**

📸 **Изображение → Текст:**
1. Выберите режим "Изображение → Текст"
2. Отправьте фото с текстом
3. Получите распознанный текст

🎤 **Аудио → Текст:**
1. Выберите режим "Аудио → Текст"
2. Отправьте голосовое сообщение
3. Получите текстовую транскрипцию

🔊 **Текст → Аудио:**
1. Выберите режим "Текст → Аудио"
2. Отправьте текстовое сообщение
3. Получите голосовое озвучивание

⚠️ **Требования:**
• Изображения: JPG/PNG/WEBP, до 20MB, четкий текст
• Аудио: голосовые сообщения Telegram, четкая речь
• Текст: до 5000 символов, русский/английский

🔧 **Команды:**
/start - Запуск бота
/mode - Выбор режима работы
/help - Эта помощь
/status - Статус системы
/profile - Ваш профиль
/history - История транскрипций{admin_help}

💡 **Советы:**
• Используйте четкие изображения
• Говорите естественно, но отчетливо
• При проблемах попробуйте другой формат
        """
        await update.message.reply_text(message, parse_mode='Markdown')
        
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = f"""
🤖 **Статус бота:**
✅ Бот активен
🔹 Whisper: загружен
🔹 OCR: доступен

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        await update.message.reply_text(message, parse_mode='Markdown')

    async def mode_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда выбора режима работы"""
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

        await update.message.reply_text(
            f"🎛️ **Выберите режим работы**\n\n"
            f"Текущий режим: {mode_names.get(current_mode, 'Не выбран')}\n\n"
            f"📸 **Изображение → Текст:** Отправьте фото → получите текст\n"
            f"🎤 **Аудио → Текст:** Отправьте голос → получите текст\n"
            f"🔊 **Текст → Аудио:** Отправьте текст → получите голос",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        mode = self.user_modes.get(user_id, 'img_to_text')  # по умолчанию режим OCR

        try:
            photo = update.message.photo[-1]
            await update.message.reply_text("🔄 Обрабатываю изображение...")

            photo_file = await context.bot.get_file(photo.file_id)
            image_path = f"downloads/{user_id}_{photo.file_id}.jpg"
            await photo_file.download_to_drive(image_path)

            extracted_text = await self.image_processor.extract_text_from_image(image_path)
            if not extracted_text.strip():
                await update.message.reply_text("❌ Текст не распознан. Используйте более четкое изображение.")
                return

            admin_service = self.get_admin_service()

            if mode == 'img_to_text':
                # Режим: Изображение → Текст
                admin_service.log_transcription(
                    user_id=user_id,
                    transcription_type=TranscriptionType.IMAGE_TO_TEXT,
                    input_text=extracted_text,
                    status='completed'
                )
                await update.message.reply_text(f"📝 **Текст из изображения:**\n\n```\n{extracted_text}\n```", parse_mode='Markdown')

            elif mode == 'img_to_audio':
                # Режим: Изображение → Аудио (старый режим)
                await update.message.reply_text(f"🎙️ Создаю аудио:\n```\n{extracted_text[:200]}{'...' if len(extracted_text) > 200 else ''}\n```", parse_mode='Markdown')

                admin_service.log_transcription(
                    user_id=user_id,
                    transcription_type=TranscriptionType.TEXT_TO_AUDIO,
                    input_text=extracted_text,
                    status='processing'
                )

                audio_path = self.transcriber.text_to_speech(extracted_text, user_id)
                admin_service.log_transcription(
                    user_id=user_id,
                    transcription_type=TranscriptionType.TEXT_TO_AUDIO,
                    input_text=extracted_text,
                    output_audio_path=audio_path,
                    status='completed'
                )

                await update.message.reply_text("✅ Готово!")
                with open(audio_path, 'rb') as audio_file:
                    await update.message.reply_voice(audio_file, caption="🎵 Готово")

                os.remove(audio_path)
            else:
                await update.message.reply_text("❌ Этот режим не поддерживает изображения. Используйте /mode для выбора режима.")

            os.remove(image_path)

        except Exception as e:
            logger.error(f"Ошибка обработки фото: {e}")
            try:
                admin_service = self.get_admin_service()
                admin_service.log_text_to_audio_transcription(user_id=user_id, status='failed', error_message=str(e))
            except:
                pass
            await update.message.reply_text("❌ Ошибка обработки. Попробуйте еще раз.")

    async def handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        mode = self.user_modes.get(user_id, 'img_to_text')  # по умолчанию режим OCR
        audio_path = None

        try:
            voice = update.message.voice
            if not voice:
                return

            if mode != 'audio_to_text':
                await update.message.reply_text("❌ Этот режим не поддерживает голосовые сообщения. Используйте /mode для выбора режима '🎤 Аудио → Текст'.")
                return

            await update.message.reply_text("🔄 Обрабатываю голосовое сообщение...")

            voice_file = await context.bot.get_file(voice.file_id)
            audio_path = f"downloads/{user_id}_{voice.file_id}.ogg"
            await voice_file.download_to_drive(audio_path)

            admin_service = self.get_admin_service()
            admin_service.log_transcription(
                user_id=user_id,
                transcription_type=TranscriptionType.AUDIO_TO_TEXT,
                input_audio_path=audio_path,
                status='processing'
            )

            transcription_result = await self.transcriber.transcribe_audio(audio_path)
            recognized_text = transcription_result["text"]

            if not recognized_text.strip():
                await update.message.reply_text("❌ Речь не распознана. Говорите четче.")
                admin_service.log_transcription(
                    user_id=user_id,
                    transcription_type=TranscriptionType.AUDIO_TO_TEXT,
                    input_audio_path=audio_path,
                    status='failed',
                    error_message="Речь не распознана"
                )
                return

            admin_service.log_transcription(
                user_id=user_id,
                transcription_type=TranscriptionType.AUDIO_TO_TEXT,
                input_audio_path=audio_path,
                input_text=recognized_text,
                status='completed'
            )

            await update.message.reply_text(f"📝 Текст:\n```\n{recognized_text}\n```", parse_mode='Markdown')
            os.remove(audio_path)

        except Exception as e:
            logger.error(f"Ошибка обработки голоса: {e}")
            try:
                admin_service = self.get_admin_service()
                admin_service.log_audio_to_text_transcription(
                    user_id=user_id, status='failed', error_message=str(e), input_audio_path=audio_path
                )
            except:
                pass
            await update.message.reply_text("❌ Ошибка обработки. Попробуйте еще раз.")
            
    async def profile_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        admin_service = self.get_admin_service()

        user = admin_service.get_user_info(user_id)
        if not user:
            await update.message.reply_text("❌ Профиль не найден.")
            return

        transcriptions = admin_service.get_user_transcriptions(user_id, limit=5)
        text_to_audio = sum(1 for t in transcriptions if t.is_text_to_audio())
        audio_to_text = sum(1 for t in transcriptions if t.is_audio_to_text())

        message = f"""
👤 **Профиль:**

📝 **Инфо:**
• Имя: {user.get_full_name()}
• ID: `{user.telegram_id}`
• Роль: {'👑 Админ' if user.is_admin() else '👤 Пользователь'}
• Статус: {'🚫 Заблокирован' if user.is_blocked else '✅ Активен'}
• Регистрация: {user.created_at.strftime('%d.%m.%Y %H:%M')}
• Активность: {user.last_activity.strftime('%d.%m.%Y %H:%M')}

🎙️ **Транскрипции:**
• Всего: {len(transcriptions)}
• 📸 Изобр→Аудио: {text_to_audio}
• 🎤 Аудио→Текст: {audio_to_text}
        """
        await update.message.reply_text(message, parse_mode='Markdown')

    async def history_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        admin_service = self.get_admin_service()

        transcriptions = admin_service.get_user_transcriptions(user_id, limit=10)

        if not transcriptions:
            await update.message.reply_text("📭 Транскрипций нет.")
            return

        message = "📜 **История:**\n\n"

        for trans in transcriptions:
            status = "✅" if trans.status == 'completed' else "❌" if trans.status == 'failed' else "🔄"
            date = trans.created_at.strftime('%d.%m.%Y %H:%M')

            if trans.is_text_to_audio():
                icon = "📸"
                text = (trans.input_text or 'Нет текста')[:50]
            elif trans.is_audio_to_text():
                icon = "🎤"
                text = (trans.input_text or 'Нет текста')[:50]
            else:
                icon = "❓"
                text = "N/A"

            text += "..." if len(text) > 47 else ""
            message += f"{status} {icon} {date}\n📝 {text}\n⏱️ {trans.processing_time or 'N/A'} сек\n\n"

        await update.message.reply_text(message, parse_mode='Markdown')

    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_admin(update.effective_user.id, update.effective_user.username):
            await update.message.reply_text("❌ Нет прав.")
            return

        keyboard = [
            [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton("👥 Пользователи", callback_data="admin_users")],
            [InlineKeyboardButton("🚫 Блокировка", callback_data="admin_block")],
            [InlineKeyboardButton("📜 Логи", callback_data="admin_logs")],
            [InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "🛠️ **Админ панель:**\nВыберите действие:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_admin(update.effective_user.id, update.effective_user.username):
            await update.message.reply_text("❌ Нет прав.")
            return

        admin_service = self.get_admin_service()
        user_stats = admin_service.get_user_statistics()
        transcription_stats = admin_service.get_transcription_statistics()

        message = f"""
📊 **Статистика:**

👥 **Пользователи:**
• Всего: {user_stats['total_users']}
• Активные (7д): {user_stats['active_users']}
• Заблокированные: {user_stats['blocked_users']}
• Админы: {user_stats['admin_users']}

🎙️ **Транскрипции:**
• Всего: {transcription_stats['total_transcriptions']}
• Успешных: {transcription_stats['successful_transcriptions']}
• Успех: {transcription_stats['success_rate']}%

📸 Изобр→Аудио: {transcription_stats['text_to_audio_count']}
🎤 Аудио→Текст: {transcription_stats['audio_to_text_count']}

⏱️ Ср. время: {transcription_stats['avg_processing_time']} сек
⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        await update.message.reply_text(message, parse_mode='Markdown')

    async def users_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_admin(update.effective_user.id, update.effective_user.username):
            await update.message.reply_text("❌ Нет прав.")
            return

        admin_service = self.get_admin_service()
        users = admin_service.get_users_list(limit=10)

        if not users:
            await update.message.reply_text("📭 Пользователей нет.")
            return

        message = "👥 **Пользователи:**\n\n"
        for user in users:
            status = "🚫" if user.is_blocked else "✅"
            role = "👑" if user.is_admin() else "👤"
            last_active = user.last_activity.strftime('%d.%m.%Y %H:%M')

            message += f"{status} {role} {user.get_full_name()}\n"
            message += f"ID: `{user.telegram_id}` | {last_active}\n\n"

        message += f"Показаны последние {len(users)} пользователей"
        await update.message.reply_text(message, parse_mode='Markdown')

    async def block_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_admin(update.effective_user.id, update.effective_user.username):
            await update.message.reply_text("❌ Нет прав.")
            return

        if not context.args:
            await update.message.reply_text("Используйте: /block <user_id> [причина]")
            return

        target_id = context.args[0]
        reason = " ".join(context.args[1:]) or "Не указана"

        admin_service = self.get_admin_service()
        if admin_service.block_user(update.effective_user.id, int(target_id), reason):
            await update.message.reply_text(f"✅ Пользователь `{target_id}` заблокирован.\nПричина: {reason}", parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ Не удалось заблокировать.")

    async def unblock_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_admin(update.effective_user.id, update.effective_user.username):
            await update.message.reply_text("❌ Нет прав.")
            return

        if not context.args:
            await update.message.reply_text("Используйте: /unblock <user_id> [причина]")
            return

        target_id = context.args[0]
        reason = " ".join(context.args[1:]) or "Не указана"

        admin_service = self.get_admin_service()
        if admin_service.unblock_user(update.effective_user.id, int(target_id), reason):
            await update.message.reply_text(f"✅ Пользователь `{target_id}` разблокирован.\nПричина: {reason}", parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ Не удалось разблокировать.")

    async def callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id
        action = query.data

        # Обработка mode callback'ов
        if action.startswith("mode_"):
            mode_data = action.split("_")
            if len(mode_data) >= 4 and mode_data[-1] == str(user_id):
                mode = "_".join(mode_data[1:-1])  # mode_name without user_id

                mode_names = {
                    'img_to_text': '📸 Изображение → Текст',
                    'audio_to_text': '🎤 Аудио → Текст',
                    'text_to_audio': '🔊 Текст → Аудио'
                }

                if mode in mode_names:
                    self.user_modes[user_id] = mode
                    await query.edit_message_text(
                        f"✅ **Режим изменен**\n\n"
                        f"Текущий режим: {mode_names[mode]}\n\n"
                        f"Теперь отправляйте соответствующий контент!",
                        parse_mode='Markdown'
                    )
                else:
                    await query.edit_message_text("❌ Неизвестный режим")
            else:
                await query.edit_message_text("❌ Ошибка доступа")
            return

        # Admin callbacks
        if not self.is_admin(user_id, update.effective_user.username):
            await query.edit_message_text("❌ Нет прав.")
            return

        if action == "admin_stats":
            admin_service = self.get_admin_service()
            user_stats = admin_service.get_user_statistics()
            transcription_stats = admin_service.get_transcription_statistics()

            message = f"""
📊 **Статистика:**

👥 **Пользователи:**
• Всего: {user_stats['total_users']}
• Активные (7д): {user_stats['active_users']}
• Заблокированные: {user_stats['blocked_users']}
• Админы: {user_stats['admin_users']}

🎙️ **Транскрипции:**
• Всего: {transcription_stats['total_transcriptions']}
• Успешных: {transcription_stats['successful_transcriptions']}
• Успех: {transcription_stats['success_rate']}%

📸 Изобр→Аудио: {transcription_stats['text_to_audio_count']}
🎤 Аудио→Текст: {transcription_stats['audio_to_text_count']}

⏱️ Ср. время: {transcription_stats['avg_processing_time']} сек
⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """
            await query.edit_message_text(message, parse_mode='Markdown')
        elif action == "admin_users":
            await self.users_command(update, context)
        elif action == "admin_block":
            await query.edit_message_text(
                "🚫 **Блокировка:**\n\nИспользуйте:\n/block <user_id> [причина]\n\nПример:\n/block 123456789 Нарушение",
                parse_mode='Markdown'
            )
        elif action == "admin_logs":
            await query.edit_message_text(
                "📜 **Логи:**\n\nКоманда: /logs\n\nФайл: logs/bot.log"
            )
        elif action == "admin_broadcast":
            await query.edit_message_text(
                "📢 **Рассылка:**\n\nКоманда: /broadcast <сообщение>\n\nПример: /broadcast Техработы"
            )

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений для TTS режима"""
        user_id = update.effective_user.id
        mode = self.user_modes.get(user_id, 'img_to_text')

        if mode != 'text_to_audio':
            return  # Игнорируем текстовые сообщения в других режимах

        text = update.message.text
        if not text or len(text.strip()) < 1:
            return

        if len(text) > 5000:  # Ограничение на длину текста
            await update.message.reply_text("❌ Текст слишком длинный (макс. 5000 символов)")
            return

        try:
            await update.message.reply_text("🔄 Создаю аудио...")

            admin_service = self.get_admin_service()
            admin_service.log_transcription(
                user_id=user_id,
                transcription_type=TranscriptionType.TEXT_TO_AUDIO,
                input_text=text,
                status='processing'
            )

            audio_path = self.transcriber.text_to_speech(text, user_id)
            admin_service.log_transcription(
                user_id=user_id,
                transcription_type=TranscriptionType.TEXT_TO_AUDIO,
                input_text=text,
                output_audio_path=audio_path,
                status='completed'
            )

            await update.message.reply_text("✅ Готово!")
            with open(audio_path, 'rb') as audio_file:
                await update.message.reply_voice(audio_file, caption="🎵 Готово")

            os.remove(audio_path)

        except Exception as e:
            logger.error(f"Ошибка TTS: {e}")
            try:
                admin_service = self.get_admin_service()
                admin_service.log_transcription(
                    user_id=user_id,
                    transcription_type=TranscriptionType.TEXT_TO_AUDIO,
                    input_text=text,
                    status='failed',
                    error_message=str(e)
                )
            except:
                pass
            await update.message.reply_text("❌ Ошибка создания аудио. Попробуйте еще раз.")

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.error(f"Ошибка: {context.error}")
        if update and update.message:
            await update.message.reply_text("❌ Ошибка. Попробуйте позже.")

    async def set_bot_commands(self, application: Application):
        commands = [
            BotCommand("start", "Запуск"),
            BotCommand("help", "Помощь"),
            BotCommand("mode", "Выбор режима"),
            BotCommand("status", "Статус")
        ]
        await application.bot.set_my_commands(commands)

    def run(self):
        application = Application.builder().token(self.token).build()

        # User commands
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("mode", self.mode_command))
        application.add_handler(CommandHandler("status", self.status_command))
        application.add_handler(CommandHandler("profile", self.profile_command))
        application.add_handler(CommandHandler("history", self.history_command))

        # Admin commands
        application.add_handler(CommandHandler("admin", self.admin_command))
        application.add_handler(CommandHandler("stats", self.stats_command))
        application.add_handler(CommandHandler("users", self.users_command))
        application.add_handler(CommandHandler("block", self.block_command))
        application.add_handler(CommandHandler("unblock", self.unblock_command))

        # Handlers
        application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        application.add_handler(MessageHandler(filters.VOICE, self.handle_voice))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
        application.add_handler(CallbackQueryHandler(self.callback_handler))

        application.add_error_handler(self.error_handler)

        logger.info("Бот запущен")
        application.run_polling(allowed_updates=Update.ALL_TYPES)