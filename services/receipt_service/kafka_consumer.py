import logging
from typing import TYPE_CHECKING

from ..common import BaseKafkaConsumer, ResultMessage, TaskMessage

if TYPE_CHECKING:
    from collections.abc import Callable

from .processor import ReceiptProcessor

logger = logging.getLogger(__name__)


class ReceiptKafkaConsumer(BaseKafkaConsumer):
    """Kafka consumer for receipt processing."""

    def __init__(
        self,
        config,
        result_sender: "Callable[[ResultMessage], None] | None" = None,
        processor=None,
    ):
        super().__init__(
            config=config,
            topic_key="tasks_receipt",
            group_suffix="receipt",
            result_sender=result_sender,
            max_workers=1,
            poll_timeout_ms=5000,
        )
        self.processor = processor if processor else ReceiptProcessor()

    def process_task(self, task: TaskMessage) -> ResultMessage:
        try:
            items_text = task.file_path or ""
            unknown_items_data = task.metadata.get("unknown_items", []) if task.metadata else []

            logger.info(f"Processing receipt task {task.task_id} for user {task.user_id}")

            result = self.processor.process_receipt_sync(items_text, task.user_id)

            if result["status"] == "error":
                return ResultMessage.failure(
                    task_id=task.task_id,
                    result_type="receipt",
                    error=result.get("message", "Processing failed"),
                )

            unknown_items = [
                {
                    "article": item["article"],
                    "name": item["name"],
                    "quantity": item["quantity"],
                    "price": item.get("price", 0.0),
                }
                for item in unknown_items_data
            ]

            if result.get("missing_items"):
                for item in result["missing_items"]:
                    unknown_items.append(
                        {
                            "article": item["article"],
                            "name": item.get("name", f"Товар {item['article']}"),
                            "quantity": item.get("quantity", 1),
                            "price": 0.0,
                        }
                    )

            company_from_metadata = task.metadata.get("company") if task.metadata else None
            if company_from_metadata and company_from_metadata.strip():
                company_value = company_from_metadata
            else:
                company_value = None
            logger.info(
                f"kafka_consumer: company from metadata='{company_from_metadata}', user_id={task.user_id}, using='{company_value}'"
            )

            pdf_path = self.processor.generate_receipt_pdf_sync(
                result["items"], unknown_items, user_id=task.user_id, company=company_value
            )

            logger.info(f"Receipt generated: {pdf_path}")

            return ResultMessage.success(
                task_id=task.task_id,
                result_type="receipt",
                result_data={
                    "file_path": pdf_path,
                    "items_count": result["items_count"],
                    "missing_count": result["missing_count"],
                    "missing_articles": result.get("missing_articles", []),
                    "total": result["total"],
                },
            )

        except Exception as e:
            logger.error(f"Error processing receipt {task.task_id}: {e}")
            return ResultMessage.failure(
                task_id=task.task_id,
                result_type="receipt",
                error=str(e),
            )
