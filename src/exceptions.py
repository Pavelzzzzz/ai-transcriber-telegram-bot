"""Custom exceptions for AI Transcriber Bot"""

import logging
from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime

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
        context: Optional[Dict[str, Any]] = None,
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
            "timestamp": self.timestamp.isoformat(),
            "is_critical": self.is_critical
        }

class ValidationError(BotError):
    """Ошибка валидации данных"""
    
    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            severity=ErrorSeverity.LOW,
            field=field,
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
            file_path=file_path,
            **kwargs
        )
        self.file_path = file_path

class AudioProcessingError(FileProcessingError):
    """Ошибка обработки аудио"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="AUDIO_PROCESSING_ERROR",
            severity=ErrorSeverity.HIGH,
            **kwargs
        )

class ImageProcessingError(FileProcessingError):
    """Ошибка обработки изображений"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="IMAGE_PROCESSING_ERROR",
            severity=ErrorSeverity.HIGH,
            **kwargs
        )

class DatabaseError(BotError):
    """Ошибка базы данных"""
    
    def __init__(self, message: str, query: Optional[str] = None, **kwargs):
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            severity=ErrorSeverity.HIGH,
            is_critical=True,
            query=query,
            **kwargs
        )
        self.query = query

class ExternalServiceError(BotError):
    """Ошибка внешнего сервиса"""
    
    def __init__(self, message: str, service_name: Optional[str] = None, **kwargs):
        super().__init__(
            message=message,
            error_code="EXTERNAL_SERVICE_ERROR",
            severity=ErrorSeverity.MEDIUM,
            service_name=service_name,
            **kwargs
        )
        self.service_name = service_name

class RateLimitError(BotError):
    """Превышен лимит запросов"""
    
    def __init__(self, message: str, limit: Optional[int] = None, **kwargs):
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_ERROR",
            severity=ErrorSeverity.MEDIUM,
            limit=limit,
            **kwargs
        )
        self.limit = limit

class ConfigurationError(BotError):
    """Ошибка конфигурации"""
    
    def __init__(self, message: str, config_key: Optional[str] = None, **kwargs):
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            severity=ErrorSeverity.CRITICAL,
            is_critical=True,
            config_key=config_key,
            **kwargs
        )
        self.config_key = config_key

class ErrorHandler:
    """Универсальный обработчик ошибок"""
    
    @staticmethod
    def log_error(
        error: Exception,
        update: Optional[Any] = None,
        context: Optional[Any] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ):
        """Логирование ошибок с детализацией"""
        error_data = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'update_id': getattr(update, 'update_id', None),
            'timestamp': datetime.now().isoformat(),
            'additional_data': additional_context or {}
        }
        
        # Определение уровня логирования
        log_level = logging.ERROR
        if isinstance(error, BotError):
            log_level = logging.WARNING if error.is_critical else logging.ERROR
        
        # Форматируем сообщение с данными
        message = f"[{error_data['error_type']}] {error_data['error_message']}"
        if error_data['update_id']:
            message += f" (Update: {error_data['update_id']})"
        
        logger.log(log_level, message)
    
    @staticmethod
    def handle_telegram_error(
        error: Exception, 
        update, 
        context,
        user_message: str = "❌ Произошла ошибка. Попробуйте позже."
    ) -> None:
        """Обработка ошибок Telegram с уведомлением пользователя"""
        ErrorHandler.log_error(error, update, context)
        
        try:
            if hasattr(update, 'message') and update.message:
                update.message.reply_text(user_message)
            elif hasattr(update, 'callback_query') and update.callback_query:
                try:
                    update.callback_query.answer(user_message, show_alert=True)
                except Exception:
                    logger.warning("Failed to answer callback query")
        except Exception as e:
            logger.error(f"Error handling Telegram error: {e}")
    
    @staticmethod
    def handle_database_error(
        error: Exception, 
        operation: str,
        query: Optional[str] = None
    ):
        """Обработка ошибок базы данных"""
        error_message = f"Database error during {operation}"
        if query:
            error_message += f" (Query: {query[:50]}...)"
        
        logger.error(f"{error_message}: {error}")
    
    @staticmethod
    def handle_file_error(
        error: Exception, 
        operation: str,
        file_path: Optional[str] = None
    ):
        """Обработка файловых ошибок"""
        error_message = f"File {operation} failed"
        if file_path:
            error_message += f" (File: {file_path})"
        
        logger.error(f"{error_message}: {error}")
    
    @staticmethod
    def create_validation_error(
        field: str,
        value: Any,
        expected_type: str
    ) -> ValidationError:
        """Создание ошибки валидации"""
        message = f"Invalid {field}: {value} (expected {expected_type})"
        return ValidationError(message, field=field)
    
    @staticmethod
    def create_rate_limit_error(
        user_id: int,
        limit: int,
        window_minutes: int
    ) -> RateLimitError:
        """Создание ошибки превышения лимита"""
        message = f"Rate limit exceeded for user {user_id}"
        return RateLimitError(message, limit=limit)
    
    @staticmethod
    def log_transcription(
        user_id: int,
        operation: str,
        processing_time: int,
        input_text: str,
        output_audio_path: Optional[str] = None,
        error_message: Optional[str] = None
    ):
        """Логирование операций транскрибации"""
        if error_message:
            logger.error(f"Transcription failed for user {user_id}: {error_message}")
        else:
            logger.info(
                f"Transcription completed for user {user_id}: {operation} "
                f"in {processing_time}s (text length: {len(input_text)})"
            )
    
    @staticmethod
    def log_operation(
        operation: str,
        user_id: Optional[int] = None,
        status: str = "started",
        details: Optional[Dict[str, Any]] = None
    ):
        """Логирование операций"""
        message = f"Operation {operation} {status}"
        if user_id:
            message += f" (user: {user_id})"
        
        if details:
            message += f" - {details}"
        
        logger.info(message)