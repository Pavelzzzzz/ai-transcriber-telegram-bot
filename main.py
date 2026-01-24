#!/usr/bin/env python3
import logging
from src.bot import TelegramBot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    try:
        bot = TelegramBot()
        bot.run()
    except Exception as e:
        logger.error(f"Ошибка запуска: {e}")