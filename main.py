"""Основной файл запуска AI Транскрибатора с исправленным event loop"""

import os
import sys
import logging
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from telegram.ext import Application

# Настройка логирования с проверкой прав
def setup_logging():
    """Настройка логирования с проверкой прав"""
    logs_dir = Path('logs')
    
    # Пробуем создать директорию
    try:
        logs_dir.mkdir(exist_ok=True)
        
        # Проверяем права записи
        test_file = logs_dir / '.permission_check'
        try:
            test_file.write_text('test')
            test_file.unlink()
            
            # Если успешно, настраиваем логирование
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler('logs/bot.log', mode='a', encoding='utf-8'),
                    logging.StreamHandler(sys.stdout)
                ]
            )
            return True
            
        except (PermissionError, OSError) as e:
            pass
        
    except (PermissionError, OSError) as e:
        pass
    
    # Fallback - только console логирование
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    print("⚠️ Cannot write to logs directory, using console only")
    return False

# Установка логирования
file_logging_enabled = setup_logging()
logger = logging.getLogger(__name__)

# Импортируем после настройки логирования
from src.bot import TelegramBot
from src.exceptions import ErrorHandler, ConfigurationError

def signal_handler(signum, frame):
    """Простой обработчик сигналов"""
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)

def main():
    """Основная функция с корректным управлением event loop"""
    try:
        # Настройка обработчиков сигналов (только для Unix-подобных систем)
        if sys.platform != 'win32':
            import signal
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
        
        # Загрузка переменных окружения
        load_dotenv()
        
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not token:
            raise ConfigurationError("TELEGRAM_BOT_TOKEN environment variable is required")
        
        logger.info("Starting AI Transcriber Bot...")
        
        # Создание бота
        bot = TelegramBot()
        
        # Создание приложения
        application = Application.builder().token(token).build()
        
        # Настройка обработчиков бота
        bot.setup_handlers(application)
        
        # Настройка обработчика ошибок
        async def enhanced_error_handler(update, context):
            if context.error:
                ErrorHandler.handle_telegram_error(
                    context.error, 
                    update, 
                    context,
                    "❌ Произошла ошибка. Попробуйте еще раз."
                )
        
        application.add_error_handler(enhanced_error_handler)
        
        # Установка команд бота (синхронно)
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            
            async def set_commands():
                await bot.set_bot_commands(application)
            
            # Установка команд перед запуском
            loop.run_until_complete(set_commands())
            logger.info("Bot commands set successfully")
            
            logger.info("Bot configured, starting polling...")
            logger.info(f"File logging: {'enabled' if file_logging_enabled else 'disabled'}")
            
            # Запуск polling без дополнительного управления event loop
            application.run_polling()
            
        except Exception as e:
            logger.error(f"Error during bot startup: {e}")
            raise
            
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        return 0
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        return 1
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())