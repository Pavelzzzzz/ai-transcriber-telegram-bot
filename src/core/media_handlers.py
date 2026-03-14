"""
Media handlers for AI Transcriber Bot
"""

import logging
import os
import uuid
from typing import Optional
from telegram import Update
from telegram.ext import ContextTypes

from src.core.user_manager import UserManager
from config.settings import config

logger = logging.getLogger(__name__)


class MediaHandlers:
    """Handles all media-related operations"""
    
    def __init__(self, config, user_manager: UserManager):
        self.config = config
        self.user_manager = user_manager
    
    async def _safe_reply(self, update: Update, text: str) -> None:
        """Safely send a reply to the user"""
        try:
            await update.message.reply_text(text)
        except Exception as e:
            logger.error(f"Failed to send reply to user {update.effective_user.id}: {e}")
    
    async def process_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Process photo messages with OCR"""
        try:
            # Create downloads directory if needed
            os.makedirs(self.config.paths.downloads_dir, exist_ok=True)
            
            await self._safe_reply(update, "📸 Фото получено! Распознаю текст...")
            
            if not update.message.photo:
                await self._safe_reply(update, "❌ Ошибка: фото не найдено")
                return
                
            # Download photo
            photo = update.message.photo[-1]
            photo_file = await context.bot.get_file(photo.file_id)
            
            user_id = update.effective_user.id
            image_path = f"{self.config.paths.downloads_dir}/{user_id}_{photo.file_id}.jpg"
            await photo_file.download_to_drive(image_path)
            
            # Try OCR processing
            try:
                from utils.image_processor import ImageProcessor
                image_processor = ImageProcessor()
                extracted_text = await image_processor.extract_text_from_image(image_path)
                
                if extracted_text and extracted_text.strip():
                    await self._safe_reply(update, 
                        f"📝 **Распознанный текст:**\n\n```\n{extracted_text}\n```", 
                        parse_mode="Markdown"
                    )
                    logger.info(f"Photo processed successfully for user {user_id}")
                else:
                    await self._safe_reply(update, "❌ Текст не распознан. Используйте более четкое изображение.")
                    
            except ImportError:
                await self._safe_reply(update, "⚠️ Модуль OCR временно недоступен, но фото получено!")
            except Exception as ocr_error:
                logger.error(f"OCR processing error for user {user_id}: {ocr_error}")
                await self._safe_reply(update, "❌ Ошибка распознавания текста. Попробуйте еще раз.")
            
            # Clean up
            try:
                os.remove(image_path)
            except Exception as cleanup_error:
                logger.warning(f"Failed to clean up image file for user {user_id}: {cleanup_error}")
                
        except Exception as e:
            logger.error(f"Error processing photo for user {user_id}: {e}")
            await self._safe_reply(update, "❌ Ошибка обработки фото. Попробуйте еще раз.")
    
    async def process_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Process voice messages with Whisper"""
        try:
            # Create downloads directory if needed
            os.makedirs(self.config.paths.downloads_dir, exist_ok=True)
            
            await self._safe_reply(update, "🎤 Голосовое получено! Распознаю речь...")
            
            if not update.message.voice:
                await self._safe_reply(update, "❌ Ошибка: голосовое не найдено")
                return
                
            # Download voice
            voice = update.message.voice
            voice_file = await context.bot.get_file(voice.file_id)
            
            user_id = update.effective_user.id
            audio_path = f"{self.config.paths.downloads_dir}/{user_id}_{voice.file_id}.ogg"
            await voice_file.download_to_drive(audio_path)
            
            # Try Whisper processing
            try:
                from utils.whisper_transcriber import WhisperTranscriber
                transcriber = WhisperTranscriber()
                result = await transcriber.transcribe_audio(audio_path)
                
                if result and result.get("text"):
                    recognized_text = result["text"]
                    await self._safe_reply(update, 
                        f"📝 **Распознанный текст:**\n\n```\n{recognized_text}\n```", 
                        parse_mode="Markdown"
                    )
                    logger.info(f"Voice processed successfully for user {user_id}")
                else:
                    await self._safe_reply(update, "❌ Речь не распознана. Говорите четче.")
                    
            except ImportError:
                await self._safe_reply(update, "⚠️ Модуль Whisper временно недоступен, но голосовое получено!")
            except Exception as whisper_error:
                logger.error(f"Whisper processing error for user {user_id}: {whisper_error}")
                await self._safe_reply(update, "❌ Ошибка распознавания речи. Попробуйте еще раз.")
            
            # Clean up
            try:
                os.remove(audio_path)
            except Exception as cleanup_error:
                logger.warning(f"Failed to clean up audio file for user {user_id}: {cleanup_error}")
                
        except Exception as e:
            logger.error(f"Error processing voice for user {user_id}: {e}")
            await self._safe_reply(update, "❌ Ошибка обработки голоса. Попробуйте еще раз.")
    
    async def process_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Process text messages with Text-to-Speech (TTS)"""
        try:
            # Create downloads directory if needed
            os.makedirs(self.config.paths.downloads_dir, exist_ok=True)
            
            text = update.message.text
            user_id = update.effective_user.id
            
            await self._safe_reply(update, "🔊 Создаю аудио из вашего текста...")
            
            # Generate unique audio file path
            audio_filename = f"{self.config.paths.downloads_dir}/{user_id}_{uuid.uuid4().hex}.mp3"
            
            try:
                # Try to use gTTS for text-to-speech
                from gtts import gTTS
                tts = gTTS(text=text, lang='ru', slow=False)
                tts.save(audio_filename)
                
                # Send audio file
                with open(audio_filename, 'rb') as audio_file:
                    await update.message.reply_voice(voice=audio_file)
                
                await self._safe_reply(update, "✅ Аудио успешно создано!")
                logger.info(f"TTS processed successfully for user {user_id}")
                
            except ImportError:
                await self._safe_reply(update, "⚠️ Модуль TTS временно недоступен, но текст получен!")
                await self._safe_reply(update, 
                    f"📝 **Ваш текст:**\n```\n{text}\n```", 
                    parse_mode="Markdown"
                )
            except Exception as tts_error:
                logger.error(f"TTS processing error for user {user_id}: {tts_error}")
                await self._safe_reply(update, "❌ Ошибка создания аудио. Попробуйте другой текст.")
            
            # Clean up
            try:
                os.remove(audio_filename)
            except Exception as cleanup_error:
                logger.warning(f"Failed to clean up audio file for user {user_id}: {cleanup_error}")
                
        except Exception as e:
            logger.error(f"Error processing text for user {user_id}: {e}")
            await self._safe_reply(update, "❌ Ошибка обработки текста. Попробуйте еще раз.")
    
    # Convenience methods for direct access
    async def photo_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler for photo messages"""
        await self.process_photo(update, context)
    
    async def voice_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler for voice messages"""
        await self.process_voice(update, context)
    
    async def text_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler for text messages"""
        await self.process_text(update, context)