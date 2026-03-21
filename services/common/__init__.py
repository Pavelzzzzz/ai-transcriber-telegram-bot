from .base_kafka_consumer import BaseKafkaConsumer
from .base_service import BaseService, HealthCheckHandler, setup_logging
from .database import check_db_health, get_db, init_db
from .exceptions import (
    KafkaConsumerError,
    KafkaProducerError,
    ProcessingError,
    ServiceError,
    ValidationError,
)
from .hardware import (
    ASPECT_RATIO_SIZES,
    MODELS_CONFIG,
    STYLES_CONFIG,
    get_available_models,
    is_model_available,
)
from .kafka_config import KafkaConfig, kafka_config
from .metrics import (
    get_metrics_collector,
    set_active_workers,
    set_queue_size,
    track_error,
    track_task_duration,
    track_task_processed,
)
from .schemas import (
    AspectRatio,
    ImageModel,
    ImageStyle,
    ResultMessage,
    TaskMessage,
    TaskStatus,
    TaskType,
)
from .utils import calculate_receipt_total, format_receipt_table

__all__ = [
    "TaskMessage",
    "ResultMessage",
    "TaskType",
    "TaskStatus",
    "ImageModel",
    "ImageStyle",
    "AspectRatio",
    "kafka_config",
    "KafkaConfig",
    "ServiceError",
    "KafkaProducerError",
    "KafkaConsumerError",
    "ProcessingError",
    "ValidationError",
    "get_db",
    "check_db_health",
    "init_db",
    "BaseService",
    "BaseKafkaConsumer",
    "setup_logging",
    "HealthCheckHandler",
    "get_available_models",
    "is_model_available",
    "MODELS_CONFIG",
    "STYLES_CONFIG",
    "ASPECT_RATIO_SIZES",
    "get_metrics_collector",
    "track_task_processed",
    "track_task_duration",
    "track_error",
    "set_queue_size",
    "set_active_workers",
    "format_receipt_table",
    "calculate_receipt_total",
]
