import whisper
import torch
from gtts import gTTS
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class WhisperTranscriber:
    def __init__(self, model_name="base"):
        """Инициализация Whisper модели"""
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self._load_model()
        
    def _load_model(self):
        """Загрузка Whisper модели"""
        try:
            logger.info(f"Загрузка Whisper модели {self.model_name} на устройстве {self.device}...")
            self.model = whisper.load_model(self.model_name, device=self.device)
            logger.info("Whisper модель успешно загружена")
        except Exception as e:
            logger.error(f"Ошибка при загрузке Whisper модели: {e}")
            raise
            
    def text_to_speech(self, text: str, user_id: int) -> str:
        """Преобразование текста в речь с использованием gTTS"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            audio_path = f"downloads/audio_{user_id}_{timestamp}.mp3"

            logger.info(f"Создание аудио для пользователя {user_id} с текстом длиной {len(text)} символов")

            # Используем gTTS для генерации речи
            # lang='ru' - русский язык, slow=False - нормальная скорость
            tts = gTTS(text=text, lang='ru', slow=False)

            # Сохраняем в MP3 файл
            tts.save(audio_path)

            # Проверяем, что файл создан
            if not os.path.exists(audio_path):
                raise ValueError("Аудиофайл не был создан")

            logger.info(f"Аудио успешно создано: {audio_path}")
            return audio_path

        except Exception as e:
            logger.error(f"Ошибка при создании аудио: {e}")
            raise
            
    async def transcribe_audio(self, audio_path: str, language: str = "ru") -> dict:
        """Транскрибация аудио в текст"""
        try:
            logger.info(f"Транскрибация аудио: {audio_path}")

            result = self.model.transcribe(audio_path, language=language)

            transcribed_text = result["text"].strip()

            # Получение длительности аудио
            audio_duration = None
            if "segments" in result and result["segments"]:
                # Получаем длительность из последнего сегмента
                last_segment = result["segments"][-1]
                if "end" in last_segment:
                    audio_duration = float(last_segment["end"])

            logger.info(f"Транскрибация завершена, длина текста: {len(transcribed_text)}, длительность: {audio_duration}")

            return {
                "text": transcribed_text,
                "duration": audio_duration,
                "language": language
            }

        except Exception as e:
            logger.error(f"Ошибка при транскрибации аудио: {e}")
            raise

    async def transcribe_audio_to_text(self, audio_path: str, language: str = "ru") -> str:
        """Упрощенный метод для транскрибации аудио в текст (для совместимости)"""
        result = await self.transcribe_audio(audio_path, language)
        return result["text"]