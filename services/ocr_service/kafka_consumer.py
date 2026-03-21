import logging
from typing import TYPE_CHECKING

from ..common import BaseKafkaConsumer, ResultMessage, TaskMessage

if TYPE_CHECKING:
    from collections.abc import Callable

from .processor import OCRProcessor

logger = logging.getLogger(__name__)


class OCRKafkaConsumer(BaseKafkaConsumer):
    """Kafka consumer for OCR processing."""

    def __init__(
        self,
        config,
        result_sender: "Callable[[ResultMessage], None]",
    ):
        super().__init__(
            config=config,
            topic_key="tasks_ocr",
            group_suffix="ocr",
            result_sender=result_sender,
            max_workers=1,
            poll_timeout_ms=1000,
            session_timeout_ms=300000,
            heartbeat_interval_ms=60000,
        )
        self.processor = OCRProcessor()

    async def process_task(self, task: TaskMessage) -> ResultMessage:
        try:
            languages = task.metadata.get("languages", ["ru", "eng"])
            result = await self.processor.process_image(task.file_path, languages)

            return ResultMessage.success(
                task_id=task.task_id,
                result_type="text",
                result_data=result,
            )
        except Exception as e:
            logger.error(f"Failed to process OCR task {task.task_id}: {e}")
            return ResultMessage.failure(
                task_id=task.task_id,
                result_type="text",
                error=str(e),
            )
