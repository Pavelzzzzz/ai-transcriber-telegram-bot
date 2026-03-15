import logging
import os
import sys
from gtts import gTTS

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logger = logging.getLogger(__name__)


class TTSProcessor:
    def __init__(self, language: str = "ru", slow: bool = False):
        self.language = language
        self.slow = slow
    
    def generate_speech(self, text: str, output_path: str = None) -> str:
        try:
            logger.info(f"Generating speech for text length: {len(text)}")
            
            if not text or not text.strip():
                raise ValueError("Text cannot be empty")
            
            if output_path is None:
                import uuid
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = f"downloads/tts_{uuid.uuid4().hex}_{timestamp}.mp3"
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            tts = gTTS(text=text, lang=self.language, slow=self.slow)
            tts.save(output_path)
            
            if not os.path.exists(output_path):
                raise RuntimeError("Failed to create audio file")
            
            logger.info(f"Audio file created: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"TTS generation failed: {e}")
            raise
    
    def generate_speech_async(self, text: str, output_path: str = None) -> dict:
        try:
            audio_path = self.generate_speech(text, output_path)
            
            return {
                "audio_path": audio_path,
                "language": self.language,
                "text_length": len(text)
            }
        except Exception as e:
            logger.error(f"TTS async generation failed: {e}")
            raise
