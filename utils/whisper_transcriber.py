import logging
import os
from datetime import datetime
from typing import Any

import torch
import whisper
from gtts import gTTS

logger = logging.getLogger(__name__)


class ExternalServiceError(Exception):
    def __init__(self, message: str, service_name: str = None):
        self.message = message
        self.service_name = service_name
        super().__init__(self.message)

class WhisperTranscriber:
    def __init__(self, model_name="base"):
        """Инициализация Whisper модели"""
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model: Any | None = None
        self._load_model()

    def _load_model(self) -> None:
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

            if not self.model:
                self._load_model()

            if not self.model:
                raise ExternalServiceError("Не удалось загрузить Whisper модель", service_name="Whisper")

            result = self.model.transcribe(audio_path, language=language)

            transcribed_text = result.get("text", "")
            if isinstance(transcribed_text, str):
                transcribed_text = transcribed_text.strip()

            # Получение длительности аудио
            audio_duration = 0.0
            if "segments" in result and result["segments"]:
                # Получаем длительность из последнего сегмента
                last_segment = result["segments"][-1]
                if isinstance(last_segment, dict) and last_segment.get("end"):
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
