import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from telegram import BotCommand, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from services.common.kafka_config import KafkaConfig
from services.common.schemas import ResultMessage, TaskStatus
from services.common.user_settings_repo import get_or_create_user_settings

from . import receipt_handlers, settings_handlers
from .kafka_consumer import NotificationConsumer, ResultConsumer
from .kafka_producer import TaskProducer

kafka_config = KafkaConfig.from_env()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimpleSafeProcessor:
    def __init__(self):
        pass

    async def safe_reply(self, update: Update, text: str, parse_mode=None):
        try:
            if update and update.message:
                await update.message.reply_text(text, parse_mode=parse_mode)
                return True
        except Exception as e:
            logger.error(f"Error replying: {e}")
        return False

    async def send_photo_to_chat(
        self, bot, chat_id: int, text: str, photo_path: str, parse_mode=None
    ):
        try:
            with open(photo_path, "rb") as photo:
                await bot.send_photo(
                    chat_id=chat_id, photo=photo, caption=text, parse_mode=parse_mode
                )
            return True
        except Exception as e:
            logger.error(f"Error sending photo to chat: {e}")
            return False

    async def send_message_to_chat(self, bot, chat_id: int, text: str, parse_mode=None):
        try:
            await bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)
            return True
        except Exception as e:
            logger.error(f"Error sending to chat: {e}")
            return False
            return False


class TelegramBotService:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN не найден")

        self.user_modes = {}
        self.safe_processor = SimpleSafeProcessor()
        self.producer = TaskProducer(kafka_config) if kafka_config.bootstrap_servers else None
        self.result_consumer = None
        self.notification_consumer = None
        self.pending_tasks = {}
        self.chat_id_to_user_id = {}
        self.application = None

        self._async_loop: asyncio.AbstractEventLoop | None = None

        logger.info("Bot Service initialized")

    def _get_async_loop(self) -> asyncio.AbstractEventLoop:
        if self._async_loop is None or self._async_loop.is_closed():
            self._async_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._async_loop)
        return self._async_loop

    def handle_result(self, result: ResultMessage):
        logger.info(f"Handling result for task {result.task_id}: {result.status}")

        task_info = self.pending_tasks.get(result.task_id)
        if not task_info:
            logger.warning(
                f"No pending task found for {result.task_id}, result_data: {result.result_data}"
            )
            return

        chat_id = task_info.get("chat_id")
        task_type = task_info.get("task_type")

        if not chat_id:
            logger.warning(f"No chat_id for task {result.task_id}")
            return

        if self.application:
            loop = self._get_async_loop()
            try:
                bot = self.application.bot
                if result.status == TaskStatus.SUCCESS:
                    if task_type == "image_gen" and result.result_data.get("file_path"):
                        file_path = result.result_data.get("file_path")
                        logger.info(f"Sending image to chat {chat_id}, file_path: {file_path}")
                        loop.run_until_complete(
                            self.safe_processor.send_photo_to_chat(
                                bot,
                                chat_id,
                                "✅ **Изображение сгенерировано!**",
                                file_path,
                                parse_mode="Markdown",
                            )
                        )
                    elif result.result_data.get("text"):
                        text = result.result_data.get("text")
                        loop.run_until_complete(
                            self.safe_processor.send_message_to_chat(
                                bot, chat_id, f"✅ **Результат:**\n\n{text}"
                            )
                        )
                    else:
                        loop.run_until_complete(
                            self.safe_processor.send_message_to_chat(
                                bot, chat_id, "✅ **Задача выполнена!**"
                            )
                        )
                else:
                    error_msg = result.error or "Неизвестная ошибка"
                    loop.run_until_complete(
                        self.safe_processor.send_message_to_chat(
                            bot, chat_id, f"❌ **Ошибка:** {error_msg}"
                        )
                    )
            except Exception as e:
                logger.error(f"Error sending result to user: {e}")

        if result.task_id in self.pending_tasks:
            del self.pending_tasks[result.task_id]

    def handle_notification(self, user_id: str, message: str):
        logger.info(f"Handling notification for user {user_id}: {message[:50]}...")

        chat_id = self._find_chat_id_for_user(user_id)
        if not chat_id:
            logger.warning(f"No chat_id found for user {user_id}")
            return

        if self.application:
            loop = self._get_async_loop()
            try:
                bot = self.application.bot
                loop.run_until_complete(
                    self.safe_processor.send_message_to_chat(bot, int(chat_id), message)
                )
            except Exception as e:
                logger.error(f"Error sending notification to user: {e}")

    def _find_chat_id_for_user(self, user_id: str) -> str | None:
        for chat_id, uid in self.chat_id_to_user_id.items():
            if uid == user_id:
                return chat_id
        return None

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = """
🎉 **AI Транскрибатор**

Я конвертирую контент между форматами с помощью ИИ.

🎛️ **Режимы работы:**
📸 Изображение → Текст (OCR)
🎤 Аудио → Текст
🔊 Текст → Аудио
🖼️ Текст → Изображение

🔧 **Команды:**
/start - Запуск
/mode - Выбрать режим работы
/settings - Настройки генерации изображений
/receipt - Товарные чеки WB
/queue - Ваша очередь задач
/help - Помощь
/status - Статус

💡 **Советы:**
• Отправьте фото для OCR
• Отправьте голос для транскрипции
• В режиме 🖼️ напишите текст для генерации изображения
• В режиме 🧾 отправьте артикулы WB для создания чека
• Используйте /mode для переключения режимов
• Используйте /settings для настройки генерации изображений
        """.strip()
        await self.safe_processor.safe_reply(update, message)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = """
📖 **Помощь - AI Транскрибатор**

🔍 **Функции:**
- OCR распознавание текста
- Распознавание речи
- Преобразование текста в аудио
- Генерация изображений по тексту
- Генерация товарных чеков WB

🎛️ **Режимы работы (/mode):**
📸 Изображение → Текст (OCR)
🎤 Аудио → Текст
🔊 Текст → Аудио
🖼️ Текст → Изображение

🔧 **Команды:**
/start - Запуск бота
/mode - Выбор режима
/settings - Настройки генерации изображений
/receipt - Товарные чеки WB
/queue - Ваша очередь задач
/help - Эта помощь
/status - Статус системы

💡 **Советы:**
• Для генерации изображения: /mode → выберите 🖼️ → напишите текст
• Для товарного чека: /receipt → следуйте инструкциям
• Используйте /queue для просмотра активных задач
• Используйте /settings для выбора модели, стиля, размера
• Используйте четкие изображения для OCR
• Говорите естественно для транскрипции
        """.strip()
        await self.safe_processor.safe_reply(update, message)

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        from datetime import datetime

        message = f"""
🤖 **Статус AI Транскрибатора:**
✅ Бот активен и готов к работе

🔹 **Компоненты:**
🔸 Kafka - Подключен
🔸 OCR система - Готова
🔸 Whisper AI - Готов

⏰ **Время:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

🎯 **Текущий режим:** {self.user_modes.get(update.effective_user.id if update.effective_user else 0, "img_to_text")}
        """.strip()
        await self.safe_processor.safe_reply(update, message)

    async def queue_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id if update.effective_chat else 0

        user_tasks = {
            task_id: info
            for task_id, info in self.pending_tasks.items()
            if info.get("chat_id") == chat_id
        }

        if not user_tasks:
            message = """
📭 **Очередь задач пуста**

У вас нет активных задач в очереди.
            """.strip()
            await self.safe_processor.safe_reply(update, message)
            return

        task_lines = []
        for i, (task_id, info) in enumerate(user_tasks.items(), 1):
            task_type = info.get("task_type", "unknown")
            type_names = {
                "ocr": "📸 OCR",
                "transcribe": "🎤 Транскрипция",
                "image_gen": "🖼️ Изображение",
            }
            task_type_display = type_names.get(task_type, task_type)
            task_lines.append(f"{i}. `{task_id[:8]}...` - {task_type_display}")

        total = len(user_tasks)
        message = f"""
📋 **Ваша очередь задач ({total}):**

{chr(10).join(task_lines)}

💡 Используйте /status для проверки общего состояния системы.
        """.strip()
        await self.safe_processor.safe_reply(update, message, parse_mode="Markdown")

    async def mode_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

        keyboard = [
            [InlineKeyboardButton("📸 Изображение → Текст", callback_data="mode:img_to_text")],
            [InlineKeyboardButton("🎤 Аудио → Текст", callback_data="mode:audio_to_text")],
            [InlineKeyboardButton("🔊 Текст → Аудио", callback_data="mode:text_to_audio")],
            [InlineKeyboardButton("🖼️ Текст → Изображение", callback_data="mode:text_to_image")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.message:
            await update.message.reply_text(
                "🎛️ **Выберите режим работы**", reply_markup=reply_markup, parse_mode="Markdown"
            )

    async def callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        query = update.callback_query
        if not query or not update.effective_user:
            return

        await query.answer()
        user_id = update.effective_user.id
        action = query.data

        if action and action.startswith("mode:"):
            mode = action.split(":")[1]
            self.user_modes[user_id] = mode

            mode_names = {
                "img_to_text": "📸 Изображение → Текст",
                "audio_to_text": "🎤 Аудио → Текст",
                "text_to_audio": "🔊 Текст → Аудио",
                "text_to_image": "🖼️ Текст → Изображение",
            }

            mode_descriptions = {
                "img_to_text": "Отправьте фото для распознавания текста",
                "audio_to_text": "Отправьте голосовое сообщение для транскрипции",
                "text_to_audio": "Напишите текст для преобразования в аудио",
                "text_to_image": "Напишите текст для генерации изображения",
            }

            await query.edit_message_text(
                f"✅ **Режим изменен**\n\n"
                f"📋 Текущий режим: {mode_names.get(mode, mode)}\n\n"
                f"💡 {mode_descriptions.get(mode, '')}"
            )

    async def process_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.message.photo:
            return await self.safe_processor.safe_reply(update, "❌ Изображение не найдено")

        if not await self.safe_processor.safe_reply(update, "🔄 Обрабатываю изображение..."):
            return

        try:
            photo = update.message.photo[-1]
            photo_file = await context.bot.get_file(photo.file_id)

            os.makedirs("downloads", exist_ok=True)

            user_id = update.effective_user.id if update.effective_user else 0
            chat_id = update.effective_chat.id if update.effective_chat else 0
            image_path = f"downloads/{user_id}_{photo.file_id}.jpg"
            await photo_file.download_to_drive(image_path)

            if self.producer:
                task = self.producer.create_ocr_task(
                    user_id=user_id,
                    chat_id=chat_id,
                    file_path=image_path,
                    metadata={"message_id": update.message.message_id},
                )
                self.producer.send_task(task)
                self.pending_tasks[task.task_id] = {
                    "chat_id": chat_id,
                    "task_type": "ocr",
                    "file_path": image_path,
                }
                self.chat_id_to_user_id[str(chat_id)] = str(user_id)
                await self.safe_processor.safe_reply(
                    update,
                    "✅ Фото получено! Отправляю на OCR обработку...\n⏳ Ожидайте результат.",
                )
            else:
                await self.safe_processor.safe_reply(update, "✅ Фото получено! (Kafka недоступен)")

        except Exception as e:
            logger.error(f"Error processing photo: {e}")
            await self.safe_processor.safe_reply(update, "❌ Ошибка обработки фото")

    async def process_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.message.voice:
            return await self.safe_processor.safe_reply(update, "❌ Голосовое не найдено")

        if not await self.safe_processor.safe_reply(update, "🔄 Обрабатываю аудио..."):
            return

        try:
            voice = update.message.voice
            voice_file = await context.bot.get_file(voice.file_id)

            os.makedirs("downloads", exist_ok=True)

            user_id = update.effective_user.id if update.effective_user else 0
            chat_id = update.effective_chat.id if update.effective_chat else 0
            audio_path = f"downloads/{user_id}_{voice.file_id}.ogg"
            await voice_file.download_to_drive(audio_path)

            if self.producer:
                try:
                    settings = get_or_create_user_settings(user_id)
                    noise_reduction = settings.noise_reduction if settings else True
                except Exception as e:
                    logger.warning(f"DB not available, using default noise_reduction: {e}")
                    noise_reduction = True

                task = self.producer.create_transcribe_task(
                    user_id=user_id,
                    chat_id=chat_id,
                    file_path=audio_path,
                    metadata={
                        "message_id": update.message.message_id,
                        "language": "ru",
                        "noise_reduction": noise_reduction,
                    },
                )
                self.producer.send_task(task)
                self.pending_tasks[task.task_id] = {
                    "chat_id": chat_id,
                    "task_type": "transcribe",
                    "file_path": audio_path,
                }
                self.chat_id_to_user_id[str(chat_id)] = str(user_id)
                await self.safe_processor.safe_reply(
                    update,
                    "✅ Голос получено! Отправляю на транскрипцию...\n⏳ Ожидайте результат.",
                )
            else:
                await self.safe_processor.safe_reply(
                    update, "✅ Голос получено! (Kafka недоступен)"
                )

        except Exception as e:
            logger.error(f"Error processing voice: {e}")
            await self.safe_processor.safe_reply(update, "❌ Ошибка обработки аудио")

    async def text_message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.message.text:
            return

        user_id = update.effective_user.id if update.effective_user else 0
        text = update.message.text

        if await settings_handlers.handle_negative_prompt_input(update, context, user_id):
            return

        current_mode = self.user_modes.get(user_id, "img_to_text")

        if current_mode == "text_to_audio":
            await self.text_to_audio(update, text)
        elif current_mode == "text_to_image":
            await self.text_to_image(update, text, context)
        else:
            await self.safe_processor.safe_reply(
                update,
                f"ℹ️ **Режим:** {current_mode}\n\n"
                f"Отправьте фото или голос для обработки.\n"
                f"Используйте /mode для смены режима.",
            )

    async def text_to_audio(self, update: Update, text: str):
        try:
            from gtts import gTTS

            os.makedirs("downloads", exist_ok=True)

            user_id = update.effective_user.id if update.effective_user else 0
            audio_filename = f"downloads/{user_id}_tts.mp3"

            tts = gTTS(text=text, lang="ru")
            tts.save(audio_filename)

            if update.message:
                with open(audio_filename, "rb") as audio_file:
                    await update.message.reply_voice(voice=audio_file)

            os.remove(audio_filename)

        except Exception as e:
            logger.error(f"TTS error: {e}")
            await self.safe_processor.safe_reply(update, f"❌ Ошибка TTS: {str(e)}")

    async def text_to_image(self, update: Update, text: str, context: ContextTypes.DEFAULT_TYPE):
        try:
            await self.safe_processor.safe_reply(
                update,
                f"🎨 **Генерация изображения...**\n\nЗапрос: {text}\n\n⏳ Пожалуйста, подождите...",
            )

            if self.producer:
                user_id = update.effective_user.id if update.effective_user else 0
                chat_id = update.effective_chat.id if update.effective_chat else 0

                try:
                    settings = get_or_create_user_settings(user_id)
                    metadata = {
                        "message_id": update.message.message_id,
                        "model": settings.image_model or "sd15",
                        "style": settings.image_style or "",
                        "aspect_ratio": settings.aspect_ratio or "1:1",
                        "num_variations": settings.num_variations or 1,
                        "negative_prompt": settings.negative_prompt or "",
                    }
                except Exception as e:
                    logger.warning(f"Failed to get user settings: {e}")
                    metadata = {"message_id": update.message.message_id}

                task = self.producer.create_image_gen_task(
                    user_id=user_id, chat_id=chat_id, prompt=text, metadata=metadata
                )
                self.producer.send_task(task)
                self.pending_tasks[task.task_id] = {"chat_id": chat_id, "task_type": "image_gen"}
                self.chat_id_to_user_id[str(chat_id)] = str(user_id)

                await self.safe_processor.safe_reply(
                    update,
                    "✅ Запрос отправлен в очередь генерации изображений!\n\n"
                    "🖼️ Изображение будет сгенерировано и отправлено вам.",
                )
            else:
                await self.safe_processor.safe_reply(
                    update,
                    "⚠️ **Режим генерации изображений**\n\n"
                    "Для генерации изображений требуется подключение к Kafka.\n"
                    "Пожалуйста, попробуйте позже.",
                )

        except Exception as e:
            logger.error(f"Image generation error: {e}")
            await self.safe_processor.safe_reply(
                update, f"❌ Ошибка генерации изображения: {str(e)}"
            )

    def setup_handlers(self, application: Application):
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("mode", self.mode_command))
        application.add_handler(CommandHandler("status", self.status_command))
        application.add_handler(CommandHandler("queue", self.queue_command))
        application.add_handler(CommandHandler("settings", settings_handlers.settings_command))
        application.add_handler(CommandHandler("receipt", receipt_handlers.receipt_command))

        application.add_handler(
            CallbackQueryHandler(settings_handlers.settings_callback, pattern="^settings:")
        )
        application.add_handler(
            CallbackQueryHandler(receipt_handlers.receipt_callback, pattern="^receipt:")
        )
        application.add_handler(
            CallbackQueryHandler(
                receipt_handlers.cancel_receipt_creation, pattern="^receipt:cancel$"
            )
        )
        application.add_handler(
            CallbackQueryHandler(
                settings_handlers.handle_settings_model_callback, pattern="^settings:model:"
            )
        )
        application.add_handler(
            CallbackQueryHandler(
                settings_handlers.handle_settings_style_callback, pattern="^settings:style:"
            )
        )
        application.add_handler(
            CallbackQueryHandler(
                settings_handlers.handle_settings_aspect_callback, pattern="^settings:aspect:"
            )
        )
        application.add_handler(
            CallbackQueryHandler(
                settings_handlers.handle_settings_variations_callback,
                pattern="^settings:variations:",
            )
        )
        application.add_handler(
            CallbackQueryHandler(
                settings_handlers.handle_settings_noise_callback,
                pattern="^settings:noise$",
            )
        )

        application.add_handler(MessageHandler(filters.PHOTO, self.process_photo))
        application.add_handler(MessageHandler(filters.VOICE, self.process_voice))
        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.text_message_handler)
        )
        application.add_handler(CallbackQueryHandler(self.callback_handler))

    async def set_bot_commands(self, application: Application):
        commands = [
            BotCommand("start", "🚀 Запуск бота"),
            BotCommand("help", "📖 Помощь"),
            BotCommand("mode", "🔧 Выбор режима"),
            BotCommand("settings", "🎨 Настройки изображений"),
            BotCommand("receipt", "📋 Товарные чеки WB"),
            BotCommand("status", "📊 Статус"),
            BotCommand("queue", "📋 Ваша очередь задач"),
        ]
        await application.bot.set_my_commands(commands)

    def run(self):
        logger.info("Starting Bot Service...")

        application = Application.builder().token(self.token).build()
        self.application = application
        self.setup_handlers(application)

        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.set_bot_commands(application))

        if self.producer:
            self.result_consumer = ResultConsumer(kafka_config, self.handle_result)
            self.result_consumer.start()
            logger.info("Result consumer started")

            self.notification_consumer = NotificationConsumer(
                kafka_config, self.handle_notification
            )
            self.notification_consumer.start()
            logger.info("Notification consumer started")

        logger.info("Telegram bot started successfully!")
        application.run_polling(allowed_updates=Update.ALL_TYPES)


def main():
    bot = TelegramBotService()
    try:
        bot.run()
    except KeyboardInterrupt:
        logger.info("Bot stopped")
    finally:
        if bot.result_consumer:
            bot.result_consumer.stop()
        if bot.notification_consumer:
            bot.notification_consumer.stop()
        if bot._async_loop and not bot._async_loop.is_closed():
            bot._async_loop.close()
        logger.info("Cleanup completed")


if __name__ == "__main__":
    main()
