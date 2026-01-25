"""
Custom exceptions for AI Transcriber Bot with type safety
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BotError(Exception):
    """
    Base class for all bot errors with proper typing and structured information
    """
    
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
        self.timestamp = datetime.now()
        self.is_critical = is_critical
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging/serialization"""
        return {
            'message': self.message,
            'error_code': self.error_code,
            'severity': self.severity.value,
            'user_id': self.user_id,
            'context': self.context,
            'timestamp': self.timestamp.isoformat(),
            'is_critical': self.is_critical
        }


class ValidationError(BotError):
    """Error in data validation with field information"""
    
    def __init__(
        self, 
        message: str, 
        field: Optional[str] = None,
        value: Optional[Any] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if field:
            context['field'] = field
        if value is not None:
            context['value'] = str(value)[:100]  # Limit value length
            
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            severity=ErrorSeverity.LOW,
            context=context,
            **kwargs
        )
        self.field = field
        self.value = value


class ProcessingError(BotError):
    """Error in data processing (OCR, transcription, TTS, etc.)"""
    
    def __init__(
        self, 
        message: str,
        processing_type: Optional[str] = None,
        file_path: Optional[str] = None,
        input_data: Optional[str] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if processing_type:
            context['processing_type'] = processing_type
        if file_path:
            context['file_path'] = file_path
        if input_data:
            context['input_data'] = input_data[:200]  # Limit input data length
            
        super().__init__(
            message=message,
            error_code="PROCESSING_ERROR",
            severity=ErrorSeverity.HIGH,
            context=context,
            **kwargs
        )
        self.processing_type = processing_type
        self.file_path = file_path
        self.input_data = input_data


class ExternalServiceError(BotError):
    """Error with external services (Telegram API, AI models, etc.)"""
    
    def __init__(
        self, 
        message: str,
        service_name: Optional[str] = None,
        status_code: Optional[int] = None,
        response_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if service_name:
            context['service_name'] = service_name
        if status_code:
            context['status_code'] = status_code
        if response_data:
            context['response_data'] = response_data
            
        severity = ErrorSeverity.HIGH if status_code and status_code >= 500 else ErrorSeverity.MEDIUM
        
        super().__init__(
            message=message,
            error_code="EXTERNAL_SERVICE_ERROR",
            severity=severity,
            context=context,
            **kwargs
        )
        self.service_name = service_name
        self.status_code = status_code
        self.response_data = response_data


class DatabaseError(BotError):
    """Database related errors"""
    
    def __init__(
        self, 
        message: str,
        operation: Optional[str] = None,
        table: Optional[str] = None,
        query: Optional[str] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if operation:
            context['operation'] = operation
        if table:
            context['table'] = table
        if query:
            context['query'] = query[:200]  # Limit query length
            
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            severity=ErrorSeverity.HIGH,
            is_critical=True,
            context=context,
            **kwargs
        )
        self.operation = operation
        self.table = table
        self.query = query


class ConfigurationError(BotError):
    """Configuration errors"""
    
    def __init__(
        self, 
        message: str,
        config_key: Optional[str] = None,
        config_value: Optional[Any] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if config_key:
            context['config_key'] = config_key
        if config_value is not None:
            context['config_value'] = str(config_value)
            
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            severity=ErrorSeverity.CRITICAL,
            is_critical=True,
            context=context,
            **kwargs
        )
        self.config_key = config_key
        self.config_value = config_value


class SecurityError(BotError):
    """Security-related errors"""
    
    def __init__(
        self, 
        message: str,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        action: Optional[str] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if ip_address:
            context['ip_address'] = ip_address
        if action:
            context['action'] = action
            
        super().__init__(
            message=message,
            error_code="SECURITY_ERROR",
            severity=ErrorSeverity.HIGH,
            user_id=user_id,
            context=context,
            **kwargs
        )
        self.ip_address = ip_address
        self.action = action


class RateLimitError(BotError):
    """Rate limiting errors"""
    
    def __init__(
        self, 
        message: str,
        user_id: Optional[int] = None,
        limit_type: Optional[str] = None,
        current_count: Optional[int] = None,
        limit: Optional[int] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if limit_type:
            context['limit_type'] = limit_type
        if current_count is not None:
            context['current_count'] = current_count
        if limit is not None:
            context['limit'] = limit
            
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_ERROR",
            severity=ErrorSeverity.MEDIUM,
            user_id=user_id,
            context=context,
            **kwargs
        )
        self.limit_type = limit_type
        self.current_count = current_count
        self.limit = limit


class ErrorHandler:
    """
    Centralized error handler with structured logging
    """
    
    def __init__(self, logger_name: str = __name__):
        self.logger = logging.getLogger(logger_name)
    
    def handle_error(
        self, 
        error: Exception, 
        user_id: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> BotError:
        """
        Convert any exception to a BotError with proper logging
        """
        if isinstance(error, BotError):
            # Already a structured error
            bot_error = error
        else:
            # Convert generic exception
            bot_error = BotError(
                message=str(error),
                error_code="UNKNOWN_ERROR",
                severity=ErrorSeverity.MEDIUM,
                user_id=user_id,
                context=context or {}
            )
        
        # Log the error with full details
        error_data = bot_error.to_dict()
        
        if bot_error.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(f"Critical error: {error_data}", exc_info=True)
        elif bot_error.severity == ErrorSeverity.HIGH:
            self.logger.error(f"High severity error: {error_data}", exc_info=True)
        elif bot_error.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(f"Medium severity error: {error_data}")
        else:
            self.logger.info(f"Low severity error: {error_data}")
        
        return bot_error
    
    def create_response_message(self, error: BotError) -> str:
        """
        Create user-friendly error message
        """
        if isinstance(error, ValidationError):
            return f"❌ Неверные данные: {error.message}"
        elif isinstance(error, ProcessingError):
            return f"❌ Ошибка обработки: {error.message}"
        elif isinstance(error, ExternalServiceError):
            return f"❌ Временная проблема с сервисом: {error.message}"
        elif isinstance(error, RateLimitError):
            return f"⏰ Слишком много запросов: {error.message}"
        elif isinstance(error, SecurityError):
            return f"🔒 Доступ запрещен: {error.message}"
        else:
            return f"❌ Произошла ошибка. Попробуйте позже."


# Global error handler instance
error_handler = ErrorHandler()