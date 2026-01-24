"""Custom exceptions for the AI Transcriber Bot"""

import logging
from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime

# Импорты для Telegram типов
try:
    from telegram import Update, ContextTypes
except ImportError:
    Update = None
    ContextTypes = None

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Уровни серьезности ошибок"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BotError(Exception):
    """Базовый класс для всех ошибок бота"""
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        user_id: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
        is_critical: bool = False
    ):
        super().__init__(message)

        self.message = message
        self.error_code = error_code
        self.severity = severity
        self.user_id = user_id
        self.context = context or {}
        self.timestamp = datetime.utcnow()
        self.is_critical = is_critical
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование ошибки в словарь для логирования"""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "severity": self.severity.value,
            "user_id": self.user_id,
            "context": self.context,
            "timestamp": self.timestamp.isoformat()
        }


class ValidationError(BotError):
    """Ошибка валидации данных"""
    
    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            severity=ErrorSeverity.LOW,
            **kwargs
        )
        self.field = field


class FileProcessingError(BotError):
    """Ошибка обработки файлов"""
    
    def __init__(self, message: str, file_path: Optional[str] = None, **kwargs):
        super().__init__(
            message=message,
            error_code="FILE_PROCESSING_ERROR",
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )
        self.file_path = file_path


class AudioProcessingError(BotError):
    """Ошибка обработки аудио"""
    
    def __init__(self, message: str, audio_path: Optional[str] = None, **kwargs):
        super().__init__(
            message=message,
            error_code="AUDIO_PROCESSING_ERROR",
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )
        self.audio_path = audio_path


class ImageProcessingError(BotError):
    """Ошибка обработки изображений"""
    
    def __init__(self, message: str, image_path: Optional[str] = None, **kwargs):
        super().__init__(
            message=message,
            error_code="IMAGE_PROCESSING_ERROR",
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )
        self.image_path = image_path


class DatabaseError(BotError):
    """Ошибка базы данных"""
    
    def __init__(self, message: str, query: Optional[str] = None, **kwargs):
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            severity=ErrorSeverity.HIGH,
            **kwargs
        )
        self.query = query


class ConfigurationError(BotError):
    """Ошибка конфигурации"""
    
    def __init__(self, message: str, config_key: Optional[str] = None, **kwargs):
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            severity=ErrorSeverity.CRITICAL,
            **kwargs
        )
        self.config_key = config_key


class ExternalServiceError(BotError):
    """Ошибка внешнего сервиса (Whisper, Tesseract, TTS)"""
    
    def __init__(self, message: str, service_name: Optional[str] = None, **kwargs):
        super().__init__(
            message=message,
            error_code="EXTERNAL_SERVICE_ERROR",
            severity=ErrorSeverity.HIGH,
            **kwargs
        )
        self.service_name = service_name


class PermissionError(BotError):
    """Ошибка прав доступа"""
    
    def __init__(self, message: str, required_permission: Optional[str] = None, **kwargs):
        super().__init__(
            message=message,
            error_code="PERMISSION_ERROR",
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )
        self.required_permission = required_permission


class ErrorHandler:
    """Централизованный обработчик ошибок"""
    
    @staticmethod
    def log_error(
        error: Exception, 
        update: Optional[Update] = None,
        context: Optional[ContextTypes.DEFAULT_TYPE] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ):
        """Логирование ошибок с детализацией"""
        error_data = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'user_id': update.effective_user.id if update and update.effective_user else None,
            'chat_id': update.effective_chat.id if update and update.effective_chat else None,
            'timestamp': datetime.now().isoformat(),
            'additional_data': additional_data or {}
        }
        
        # Определение уровня логирования
        log_level = logging.ERROR
        if isinstance(error, BotError):
            log_level = logging.WARNING if error.is_critical else logging.ERROR
        
        # Форматируем сообщение с данными
        message = f"[{error_data['error_type']}] {error_data['error_message']}"
        if error_data['user_id']:
            message += f" (User: {error_data['user_id']})"
        
        logger.log(log_level, message)
        else:
            logger.error(
                f"Unhandled exception: {str(error)}",
                extra={
                    "exception_type": error.__class__.__name__,
                    "additional_context": additional_context or {}
                },
                exc_info=True
            )
    
    @staticmethod
    def handle_telegram_error(
        error: Exception, 
        update, 
        context,
        user_message: str = "❌ Произошла ошибка. Попробуйте позже."
    ) -> None:
        """Обработка ошибок Telegram с уведомлением пользователя"""
        ErrorHandler.log_error(error, {"update_id": getattr(update, 'update_id', None)})
        
        try:
            if hasattr(update, 'message') and update.message:
                update.message.reply_text(user_message)
            elif hasattr(update, 'callback_query') and update.callback_query:
                try:
                    update.callback_query.answer(user_message, show_alert=True)
                except Exception as answer_error:
                    logger.error(f"Error answering callback: {answer_error}")
        except Exception as reply_error:
            logger.error(f"Failed to send error message to user: {reply_error}")
    
    @staticmethod
    def get_user_friendly_message(error: BotError) -> str:
        """Получение дружелюбного сообщения об ошибке для пользователя"""
        messages = {
            ValidationError: "❌ Некорректные данные. Проверьте формат и попробуйте снова.",
            FileProcessingError: "❌ Не удалось обработать файл. Убедитесь, что файл не поврежден.",
            AudioProcessingError: "❌ Не удалось обработать аудио. Попробуйте записать сообщение четче.",
            ImageProcessingError: "❌ Не удалось обработать изображение. Убедитесь, что текст хорошо виден.",
            DatabaseError: "❌ Временная проблема с базой данных. Попробуйте позже.",
            ConfigurationError: "❌ Внутренняя ошибка конфигурации. Сообщите администратору.",
            ExternalServiceError: "❌ Временная проблема с сервисом распознавания. Попробуйте позже.",
            PermissionError: "❌ У вас недостаточно прав для выполнения этой операции.",
        }
        
        return messages.get(type(error), "❌ Произошла ошибка. Попробуйте позже.")