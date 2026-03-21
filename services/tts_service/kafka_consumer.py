import logging
from typing import TYPE_CHECKING

from ..common import BaseKafkaConsumer, ResultMessage, TaskMessage

if TYPE_CHECKING:
    from collections.abc import Callable

from .processor import TTSProcessor

logger = logging.getLogger(__name__)


class TTSKafkaConsumer(BaseKafkaConsumer):
    """Kafka consumer for TTS processing."""

    def __init__(
        self,
        config,
        result_sender: "Callable[[ResultMessage], None]",
        language: str = "ru",
    ):
        super().__init__(
            config=config,
            topic_key="tasks_tts",
            group_suffix="tts",
            result_sender=result_sender,
            max_workers=1,
            poll_timeout_ms=1000,
        )
        self.processor = TTSProcessor(language)

    def process_task(self, task: TaskMessage) -> ResultMessage:
        try:
            language = task.metadata.get("language", self.processor.language)
            self.processor.language = language

            result = self.processor.generate_speech_async(task.file_path)

            return ResultMessage.success(
                task_id=task.task_id,
                result_type="audio",
                result_data=result,
            )
        except Exception as e:
            logger.error(f"Failed to process TTS task {task.task_id}: {e}")
            return ResultMessage.failure(
                task_id=task.task_id,
                result_type="audio",
                error=str(e),
            )
