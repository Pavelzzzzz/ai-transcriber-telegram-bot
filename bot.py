#!/usr/bin/env python3
"""
AI Transcriber Bot - Ultimate Working Version
All 4 modes with interactive mode selection
"""

import logging
import sys
import os

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from src.core.bot_core import BotCore

def main():
    """Main bot entry point"""
    try:
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/bot.log'),
                logging.StreamHandler()
            ]
        )
        
        logger = logging.getLogger(__name__)
        logger.info("Starting AI Transcriber Bot (Ultimate Working Version)...")
        
        # Initialize and run the bot
        bot_core = BotCore()
        bot_core.run()
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to start bot: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()