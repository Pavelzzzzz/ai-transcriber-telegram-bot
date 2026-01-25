"""
Core bot functionality with improved architecture
"""

import logging
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime

from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from ...config.settings import config
from .exceptions import BotError, ConfigurationError
from .handlers import CommandHandlers, MediaHandlers, AdminHandlers, CallbackHandlers
from .user_manager import UserManager

logger = logging.getLogger(__name__)


class BotCore:
    """
    Core bot functionality with clean separation of concerns
    """
    
    def __init__(self):
        """Initialize bot core components"""
        self.config = config
        self.app: Optional[Application] = None
        
        # Validate configuration
        validation_errors = self.config.validate()
        if validation_errors:
            raise ConfigurationError(
                f"Configuration validation failed: {'; '.join(validation_errors)}",
                field="config_validation"
            )
        
        # Initialize components
        self.user_manager = UserManager(self.config)
        self.command_handlers = CommandHandlers(self.config, self.user_manager)
        self.media_handlers = MediaHandlers(self.config, self.user_manager)
        self.admin_handlers = AdminHandlers(self.config, self.user_manager)
        self.callback_handlers = CallbackHandlers(self.config, self.user_manager)
        
        self._setup_logging()
        logger.info(f"BotCore initialized successfully. Admins: {self.config.security.admin_usernames}")
    
    def _setup_logging(self) -> None:
        """Setup logging configuration"""
        logging.basicConfig(
            level=getattr(logging, self.config.logging.level.upper()),
            format=self.config.logging.format,
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Add file logging if configured
        if self.config.logging.file_path:
            from logging.handlers import RotatingFileHandler
            
            handler = RotatingFileHandler(
                self.config.logging.file_path,
                maxBytes=self.config.logging.max_file_size,
                backupCount=self.config.logging.backup_count
            )
            handler.setFormatter(logging.Formatter(self.config.logging.format))
            logging.getLogger().addHandler(handler)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command with type safety"""
        try:
            await self.command_handlers.start_command(update, context)
        except Exception as e:
            logger.error(f"Error in start command: {e}")
            await self.command_handlers._safe_reply(update, "❌ Ошибка. Попробуйте позже.")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command with type safety"""
        try:
            await self.command_handlers.help_command(update, context)
        except Exception as e:
            logger.error(f"Error in help command: {e}")
            await self.command_handlers._safe_reply(update, "❌ Ошибка. Попробуйте позже.")
    
    async def mode_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /mode command with type safety"""
        try:
            await self.command_handlers.mode_command(update, context)
        except Exception as e:
            logger.error(f"Error in mode command: {e}")
            await self.command_handlers._safe_reply(update, "❌ Ошибка. Попробуйте позже.")
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command with type safety"""
        try:
            await self.command_handlers.status_command(update, context)
        except Exception as e:
            logger.error(f"Error in status command: {e}")
            await self.command_handlers._safe_reply(update, "❌ Ошибка. Попробуйте позже.")
    
    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /admin command with type safety"""
        try:
            await self.admin_handlers.admin_command(update, context)
        except Exception as e:
            logger.error(f"Error in admin command: {e}")
            await self.command_handlers._safe_reply(update, "❌ Ошибка. Попробуйте позже.")
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /stats command with type safety"""
        try:
            await self.admin_handlers.stats_command(update, context)
        except Exception as e:
            logger.error(f"Error in stats command: {e}")
            await self.command_handlers._safe_reply(update, "❌ Ошибка. Попробуйте позже.")
    
    async def users_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /users command with type safety"""
        try:
            await self.admin_handlers.users_command(update, context)
        except Exception as e:
            logger.error(f"Error in users command: {e}")
            await self.command_handlers._safe_reply(update, "❌ Ошибка. Попробуйте позже.")
    
    async def logs_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /logs command with type safety"""
        try:
            await self.admin_handlers.logs_command(update, context)
        except Exception as e:
            logger.error(f"Error in logs command: {e}")
            await self.command_handlers._safe_reply(update, "❌ Ошибка. Попробуйте позже.")
    
    async def callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle callback queries with type safety"""
        try:
            await self.callback_handlers.callback_handler(update, context)
        except Exception as e:
            logger.error(f"Error in callback handler: {e}")
            if update.callback_query:
                await update.callback_query.answer("❌ Ошибка обработки", show_alert=True)
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Global error handler with proper typing"""
        logger.error(f"Bot error: {context.error}")
        
        if isinstance(update, Update):
            try:
                await self.command_handlers._safe_reply(
                    update, 
                    "❌ Произошла ошибка. Пожалуйста, попробуйте позже."
                )
            except Exception as reply_error:
                logger.error(f"Error in error handler reply: {reply_error}")
    
    def _setup_handlers(self, application: Application) -> None:
        """Setup all handlers for the application"""
        # Command handlers
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("mode", self.mode_command))
        application.add_handler(CommandHandler("status", self.status_command))
        
        # Admin commands
        application.add_handler(CommandHandler("admin", self.admin_command))
        application.add_handler(CommandHandler("stats", self.stats_command))
        application.add_handler(CommandHandler("users", self.users_command))
        application.add_handler(CommandHandler("logs", self.logs_command))
        
        # Media handlers (delegated to MediaHandlers)
        application.add_handler(MessageHandler(filters.PHOTO, self.media_handlers.photo_handler))
        application.add_handler(MessageHandler(filters.VOICE, self.media_handlers.voice_handler))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.media_handlers.text_handler))
        
        # Callback handlers
        application.add_handler(CallbackQueryHandler(self.callback_handler))
        
        # Error handler
        application.add_error_handler(self.error_handler)
    
    async def set_bot_commands(self, application: Application) -> None:
        """Set bot commands in Telegram"""
        commands = [
            BotCommand("start", "🚀 Запуск бота"),
            BotCommand("help", "📖 Помощь"),
            BotCommand("mode", "🎛️ Выбор режима"),
            BotCommand("status", "📊 Статус"),
            BotCommand("admin", "🔛 Админка"),
            BotCommand("stats", "📈 Статистика"),
            BotCommand("users", "👥 Пользователи"),
            BotCommand("logs", "📝 Логи"),
        ]
        
        try:
            await application.bot.set_my_commands(commands)
            logger.info("Bot commands set successfully")
        except Exception as e:
            logger.error(f"Failed to set bot commands: {e}")
    
    def create_application(self) -> Application:
        """Create and configure the Telegram application"""
        if not self.config.security.telegram_token:
            raise ConfigurationError("TELEGRAM_BOT_TOKEN is required")
        
        application = Application.builder().token(self.config.security.telegram_token).build()
        
        # Setup handlers
        self._setup_handlers(application)
        
        # Set bot commands
        asyncio.create_task(self.set_bot_commands(application))
        
        self.app = application
        return application
    
    async def start(self) -> None:
        """Start the bot with proper error handling"""
        try:
            logger.info("Starting AI Transcriber Bot...")
            
            application = self.create_application()
            
            logger.info("Bot started successfully!")
            await application.run_polling(allowed_updates=Update.ALL_TYPES)
            
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            raise BotError(f"Bot startup failed: {e}", is_critical=True)
    
    def run(self) -> None:
        """Run the bot (synchronous entry point)"""
        try:
            asyncio.run(self.start())
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Bot crashed: {e}")
            raise