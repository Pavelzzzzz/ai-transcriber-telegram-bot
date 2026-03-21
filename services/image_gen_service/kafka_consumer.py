import logging
import os
from typing import TYPE_CHECKING

from ..common import BaseKafkaConsumer, ResultMessage, TaskMessage

if TYPE_CHECKING:
    from collections.abc import Callable

from .processor import ImageGenerationProcessor

logger = logging.getLogger(__name__)

MAX_WORKERS = int(os.getenv("IMAGE_GEN_MAX_WORKERS", "1"))


class ImageGenKafkaConsumer(BaseKafkaConsumer):
    """Kafka consumer for image generation processing."""

    def __init__(
        self,
        config,
        result_sender: "Callable[[ResultMessage], None] | None" = None,
        processor=None,
    ):
        super().__init__(
            config=config,
            topic_key="tasks_image_gen",
            group_suffix="image_gen",
            result_sender=result_sender,
            max_workers=MAX_WORKERS,
            poll_timeout_ms=5000,
            session_timeout_ms=300000,
            heartbeat_interval_ms=60000,
        )
        self.processor = processor if processor else ImageGenerationProcessor()
        self._notification_sender: Callable[[str, str], None] | None = None

    def set_notification_sender(self, sender: "Callable[[str, str], None]") -> None:
        self._notification_sender = sender

    def _send_started_notification(self, task: TaskMessage) -> None:
        if self._notification_sender:
            try:
                user_id = str(task.user_id or task.metadata.get("user_id", "unknown"))
                self._notification_sender(
                    user_id,
                    f"Started processing: {task.task_id[:8]}...\nPrompt: {task.file_path[:50]}...",
                )
            except Exception as e:
                logger.warning(f"Failed to send started notification: {e}")

    async def process_task(self, task: TaskMessage) -> ResultMessage:
        try:
            prompt = task.file_path
            metadata = task.metadata or {}

            logger.info(f"Received image gen task {task.task_id}: metadata={metadata}")

            self._send_started_notification(task)

            result = await self.processor.generate_image(prompt, metadata)

            return ResultMessage.success(
                task_id=task.task_id,
                result_type="image",
                result_data=result,
            )
        except Exception as e:
            logger.error(f"Failed to process image generation task {task.task_id}: {e}")
            return ResultMessage.failure(
                task_id=task.task_id,
                result_type="image",
                error=str(e),
            )

    def get_queue_status(self) -> dict:
        return super().get_queue_status()

    def start(self) -> None:
        super().start()
        logger.info(f"Consumer started: poll_thread + process_thread + {MAX_WORKERS} workers")
