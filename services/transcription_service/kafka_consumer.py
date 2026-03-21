import logging
from typing import TYPE_CHECKING

from ..common import BaseKafkaConsumer, ResultMessage, TaskMessage

if TYPE_CHECKING:
    from collections.abc import Callable

from .processor import TranscriptionProcessor

logger = logging.getLogger(__name__)


class TranscriptionKafkaConsumer(BaseKafkaConsumer):
    """Kafka consumer for transcription processing."""

    def __init__(
        self,
        config,
        result_sender: "Callable[[ResultMessage], None]",
        model_name: str = "small",
    ):
        super().__init__(
            config=config,
            topic_key="tasks_transcribe",
            group_suffix="transcribe",
            result_sender=result_sender,
            max_workers=1,
            poll_timeout_ms=1000,
        )
        self.processor = TranscriptionProcessor(model_name)

    async def process_task(self, task: TaskMessage) -> ResultMessage:
        try:
            language = task.metadata.get("language", "ru")
            noise_reduction = task.metadata.get("noise_reduction", True)
            result = await self.processor.transcribe_audio(
                task.file_path, language, noise_reduction=noise_reduction
            )

            return ResultMessage.success(
                task_id=task.task_id,
                result_type="transcription",
                result_data=result,
            )
        except Exception as e:
            logger.error(f"Failed to process transcription task {task.task_id}: {e}")
            return ResultMessage.failure(
                task_id=task.task_id,
                result_type="transcription",
                error=str(e),
            )
