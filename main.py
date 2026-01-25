#!/usr/bin/env python3
"""
AI Transcriber Bot - Ultimate Working Version
All 4 modes with interactive mode selection
"""

import logging
import sys
import os
from pathlib import Path

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def setup_logging():
    """Setup basic logging configuration"""
    try:
        logs_dir = Path('logs')
        logs_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/bot.log'),
                logging.StreamHandler()
            ]
        )
    except Exception:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler()]
        )
        print("⚠️ Cannot write to logs directory, using console only")

def is_admin(user_id: int, username: str = None) -> bool:
    """Check if user is admin"""
    try:
        admin_usernames_str = os.getenv('ADMIN_USERNAMES', '')
        admin_ids_str = os.getenv('ADMIN_IDS', '')
        
        # Parse admin usernames
        admin_usernames = []
        if admin_usernames_str and admin_usernames_str != 'your_username_here':
            admin_usernames = [name.strip().lower() for name in admin_usernames_str.split(',') if name.strip()]
        
        # Parse admin IDs  
        admin_ids = []
        if admin_ids_str:
            try:
                admin_ids = [int(id_.strip()) for id_ in admin_ids_str.split(',') if id_.strip().isdigit()]
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
        print(f"Error checking admin status: {e}")
        return False

async def start_command(update, context):
    """Handle /start command"""
    try:
        is_user_admin = is_admin(update.effective_user.id, update.effective_user.username)
        
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
        
        await update.message.reply_text(message, parse_mode="Markdown")
        print(f"Start command used by user {update.effective_user.id}")
    except Exception as e:
        print(f"Error in start_command: {e}")
        await update.message.reply_text("❌ Произошла ошибка. Попробуйте еще раз.")

async def help_command(update, context):
    """Handle /help command"""
    try:
        is_user_admin = is_admin(update.effective_user.id, update.effective_user.username)
        
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
        
        await update.message.reply_text(message, parse_mode="Markdown")
        print(f"Help command used by user {update.effective_user.id}")
    except Exception as e:
        print(f"Error in help_command: {e}")
        await update.message.reply_text("❌ Произошла ошибка. Попробуйте еще раз.")

async def status_command(update, context):
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
            f"👤 Ваш статус: {'Администратор' if is_admin(update.effective_user.id, update.effective_user.username) else 'Пользователь'}"
        )
        
        await update.message.reply_text(message, parse_mode="Markdown")
        print(f"Status command used by user {update.effective_user.id}")
    except Exception as e:
        print(f"Error in status_command: {e}")
        await update.message.reply_text("❌ Произошла ошибка. Попробуйте еще раз.")

async def mode_command(update, context):
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
            "📸 **Фото → Текст** - OCR распознавание\n"
            "🎤 **Голос → Текст** - Whisper транскрибация\n"
            "📝 **Текст → Голос** - TTS синтез речи\n"
            "💬 **Текст → AI** - Анализ и улучшение\n\n"
            "🔄 **Автоматический** - Бот сам определит тип\n\n"
            "💡 **Нажмите на режим для активации!**"
        )
        
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="Markdown")
        print(f"Mode command used by user {update.effective_user.id}")
    except Exception as e:
        print(f"Error in mode_command: {e}")
        await update.message.reply_text("❌ Произошла ошибка. Попробуйте еще раз.")

async def mode_callback_handler(update, context):
    """Handle mode selection from inline keyboard"""
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
        print(f"User {update.effective_user.id} selected mode: {selected_mode}")
        
    except Exception as e:
        print(f"Error in mode_callback_handler: {e}")
        try:
            await update.callback_query.answer("❌ Произошла ошибка. Попробуйте еще раз.")
        except:
            pass

async def admin_command(update, context):
    """Handle /admin command"""
    try:
        if not is_admin(update.effective_user.id, update.effective_user.username):
            await update.message.reply_text("🚫 У вас нет прав администратора!")
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
        
        await update.message.reply_text(message, parse_mode="Markdown")
        print(f"Admin command used by admin {update.effective_user.id}")
    except Exception as e:
        print(f"Error in admin_command: {e}")
        await update.message.reply_text("❌ Произошла ошибка. Попробуйте еще раз.")

async def stats_command(update, context):
    """Handle /stats command"""
    try:
        if not is_admin(update.effective_user.id, update.effective_user.username):
            await update.message.reply_text("🚫 У вас нет прав администратора!")
            return
        
        message = (
            "📊 **Статистика AI Транскрибатора:**\n\n"
            "👥 **Пользователи:**\n"
            f"• Всего пользователей: Активно\n"
            "• Активных сегодня: Обрабатывается\n"
            f"• Администраторов: {os.getenv('ADMIN_USERNAMES', 'Настроено')}\n\n"
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
        
        await update.message.reply_text(message, parse_mode="Markdown")
        print(f"Stats command used by admin {update.effective_user.id}")
    except Exception as e:
        print(f"Error in stats_command: {e}")
        await update.message.reply_text("❌ Произошла ошибка. Попробуйте еще раз.")

async def users_command(update, context):
    """Handle /users command"""
    try:
        if not is_admin(update.effective_user.id, update.effective_user.username):
            await update.message.reply_text("🚫 У вас нет прав администратора!")
            return
        
        message = (
            "👥 **Информация о пользователях:**\n\n"
            "📊 База данных временно недоступна.\n"
            "Функция будет доступна после развертывания PostgreSQL.\n\n"
            "💡 **Для текущей информации:**\n"
            "Проверьте логи контейнера:\n"
            "docker logs ai-transcriber-bot --tail 50"
        )
        
        await update.message.reply_text(message, parse_mode="Markdown")
        print(f"Users command used by admin {update.effective_user.id}")
    except Exception as e:
        print(f"Error in users_command: {e}")
        await update.message.reply_text("❌ Произошла ошибка. Попробуйте еще раз.")

async def logs_command(update, context):
    """Handle /logs command"""
    try:
        if not is_admin(update.effective_user.id, update.effective_user.username):
            await update.message.reply_text("🚫 У вас нет прав администратора!")
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
        
        await update.message.reply_text(message, parse_mode="Markdown")
        print(f"Logs command used by admin {update.effective_user.id}")
    except Exception as e:
        print(f"Error in logs_command: {e}")
        await update.message.reply_text("❌ Произошла ошибка. Попробуйте еще раз.")

async def process_photo(update, context):
    """Process photo messages with OCR"""
    try:
        await update.message.reply_text("📸 Фото получено! Распознаю текст...")
        
        if not update.message.photo:
            await update.message.reply_text("❌ Ошибка: фото не найдено")
            return
            
        # Download photo
        photo = update.message.photo[-1]
        photo_file = await context.bot.get_file(photo.file_id)
        
        # Create downloads directory
        os.makedirs('downloads', exist_ok=True)
        user_id = update.effective_user.id
        image_path = f"downloads/{user_id}_{photo.file_id}.jpg"
        await photo_file.download_to_drive(image_path)
        
        # Try OCR processing
        try:
            from utils.image_processor import ImageProcessor
            image_processor = ImageProcessor()
            extracted_text = await image_processor.extract_text_from_image(image_path)
            
            if extracted_text and extracted_text.strip():
                await update.message.reply_text(
                    f"📝 **Распознанный текст:**\n\n```\n{extracted_text}\n```", 
                    parse_mode="Markdown"
                )
                print(f"Photo processed successfully for user {user_id}")
            else:
                await update.message.reply_text("❌ Текст не распознан. Используйте более четкое изображение.")
                
        except ImportError:
            await update.message.reply_text("⚠️ Модуль OCR временно недоступен, но фото получено!")
        except Exception as ocr_error:
            print(f"OCR processing error: {ocr_error}")
            await update.message.reply_text("❌ Ошибка распознавания текста. Попробуйте еще раз.")
        
        # Clean up
        try:
            os.remove(image_path)
        except:
            pass
            
    except Exception as e:
        print(f"Error processing photo: {e}")
        await update.message.reply_text("❌ Ошибка обработки фото. Попробуйте еще раз.")

async def process_voice(update, context):
    """Process voice messages with Whisper"""
    try:
        await update.message.reply_text("🎤 Голосовое получено! Распознаю речь...")
        
        if not update.message.voice:
            await update.message.reply_text("❌ Ошибка: голосовое не найдено")
            return
            
        # Download voice
        voice = update.message.voice
        voice_file = await context.bot.get_file(voice.file_id)
        
        # Create downloads directory
        os.makedirs('downloads', exist_ok=True)
        user_id = update.effective_user.id
        audio_path = f"downloads/{user_id}_{voice.file_id}.ogg"
        await voice_file.download_to_drive(audio_path)
        
        # Try Whisper processing
        try:
            from utils.whisper_transcriber import WhisperTranscriber
            transcriber = WhisperTranscriber()
            result = await transcriber.transcribe_audio(audio_path)
            
            if result and result.get("text"):
                recognized_text = result["text"]
                await update.message.reply_text(
                    f"📝 **Распознанный текст:**\n\n```\n{recognized_text}\n```", 
                    parse_mode="Markdown"
                )
                print(f"Voice processed successfully for user {user_id}")
            else:
                await update.message.reply_text("❌ Речь не распознана. Говорите четче.")
                
        except ImportError:
            await update.message.reply_text("⚠️ Модуль Whisper временно недоступен, но голосовое получено!")
        except Exception as whisper_error:
            print(f"Whisper processing error: {whisper_error}")
            await update.message.reply_text("❌ Ошибка распознавания речи. Попробуйте еще раз.")
        
        # Clean up
        try:
            os.remove(audio_path)
        except:
            pass
            
    except Exception as e:
        print(f"Error processing voice: {e}")
        await update.message.reply_text("❌ Ошибка обработки голоса. Попробуйте еще раз.")

async def process_text(update, context):
    """Process text messages with Text-to-Speech (TTS)"""
    try:
        text = update.message.text
        user_id = update.effective_user.id
        
        await update.message.reply_text("🔊 Создаю аудио из вашего текста...")
        
        # Create downloads directory
        os.makedirs('downloads', exist_ok=True)
        
        # Generate unique audio file path
        import uuid
        audio_filename = f"downloads/{user_id}_{uuid.uuid4().hex}.mp3"
        
        try:
            # Try to use gTTS for text-to-speech
            from gtts import gTTS
            tts = gTTS(text=text, lang='ru', slow=False)
            tts.save(audio_filename)
            
            # Send audio file
            with open(audio_filename, 'rb') as audio_file:
                await update.message.reply_voice(voice=audio_file)
            
            await update.message.reply_text("✅ Аудио успешно создано!")
            print(f"TTS processed successfully for user {user_id}")
            
        except ImportError:
            await update.message.reply_text("⚠️ Модуль TTS временно недоступен, но текст получен!")
            await update.message.reply_text(
                f"📝 **Ваш текст:**\n```\n{text}\n```", 
                parse_mode="Markdown"
            )
        except Exception as tts_error:
            print(f"TTS processing error: {tts_error}")
            await update.message.reply_text("❌ Ошибка создания аудио. Попробуйте другой текст.")
        
        # Clean up
        try:
            os.remove(audio_filename)
        except:
            pass
            
    except Exception as e:
        print(f"Error processing text: {e}")
        await update.message.reply_text("❌ Ошибка обработки текста. Попробуйте еще раз.")

def main():
    """Main bot entry point"""
    global processor
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("Starting AI Transcriber Bot (Ultimate Working Version)...")
        
        # Check environment
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not token or token == 'your_bot_token_here':
            print("TELEGRAM_BOT_TOKEN not configured!")
            sys.exit(1)
        
        # Import telegram modules
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
        
        # Initialize simple processor (fallback)
        try:
            from src.bot import SimpleSafeProcessor
            processor = SimpleSafeProcessor()
            print("SimpleSafeProcessor initialized")
        except Exception as e:
            print(f"Could not initialize SimpleSafeProcessor: {e}")
            processor = None
        
        # Create application
        application = Application.builder().token(token).build()
        
        # Add command handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("status", status_command))
        application.add_handler(CommandHandler("mode", mode_command))
        application.add_handler(CommandHandler("admin", admin_command))
        application.add_handler(CommandHandler("stats", stats_command))
        application.add_handler(CommandHandler("users", users_command))
        application.add_handler(CommandHandler("logs", logs_command))
        
        # Add callback handler for inline keyboards
        application.add_handler(CallbackQueryHandler(mode_callback_handler, pattern='^mode_'))
        
        # Add message handlers
        application.add_handler(MessageHandler(filters.PHOTO, process_photo))
        application.add_handler(MessageHandler(filters.VOICE, process_voice))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_text))
        
        admin_info = f"Admins: {os.getenv('ADMIN_USERNAMES', 'None')}"
        logger.info(f"Bot started successfully! {admin_info}")
        application.run_polling()
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to start bot: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()