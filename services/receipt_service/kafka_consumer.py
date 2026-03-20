import asyncio
import json
import logging
import signal
import sys
from datetime import datetime

from confluent_kafka import Consumer, Producer

sys.path.insert(0, "/home/pavel/Documents/python/ai-transcriber-telegram-bot")

from services.common.kafka_config import KafkaConfig
from services.common.schemas import ResultMessage, TaskStatus, TaskType

from .processor import ReceiptProcessor

logger = logging.getLogger(__name__)


class ReceiptKafkaConsumer:
    def __init__(self, config: KafkaConfig | None = None):
        self.config = config or KafkaConfig.from_env()
        self.processor = ReceiptProcessor()
        self._running = False
        self._loop: asyncio.AbstractEventLoop | None = None

        self.consumer = Consumer(
            {
                "bootstrap.servers": self.config.bootstrap_servers,
                "group.id": f"{self.config.client_id}_receipt_group",
                "auto.offset.reset": "earliest",
                "enable.auto.commit": True,
                "session.timeout.ms": 30000,
                "heartbeat.interval.ms": 10000,
            }
        )

        self.producer = Producer({"bootstrap.servers": self.config.bootstrap_servers})

    def _get_async_loop(self) -> asyncio.AbstractEventLoop:
        if self._loop is None or self._loop.is_closed():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
        return self._loop

    def _send_result(self, result: ResultMessage):
        try:
            topic = self.config.topics.get("results_receipt", "results.receipt")
            self.producer.produce(
                topic,
                key=result.task_id.encode("utf-8"),
                value=result.to_json().encode("utf-8"),
                callback=self._delivery_callback,
            )
            self.producer.poll(0)
        except Exception as e:
            logger.error(f"Failed to send result: {e}")

    def _delivery_callback(self, err, msg):
        if err:
            logger.error(f"Message delivery failed: {err}")
        else:
            logger.debug(f"Message delivered to {msg.topic()}")

    async def _process_message(self, message_data: dict) -> ResultMessage:
        task_id = message_data.get("task_id", "")
        user_id = message_data.get("user_id", 0)
        chat_id = message_data.get("chat_id", 0)

        items_text = message_data.get("file_path", "")
        unknown_items_data = message_data.get("metadata", {}).get("unknown_items", [])

        try:
            logger.info(f"Processing receipt task {task_id} for user {user_id}")

            result = await self.processor.process_receipt(items_text, user_id)

            if result["status"] == "error":
                return ResultMessage(
                    task_id=task_id,
                    status=TaskStatus.FAILED,
                    result_type="receipt",
                    result_data={},
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

            pdf_path = await self.processor.generate_receipt_pdf(result["items"], unknown_items)

            return ResultMessage(
                task_id=task_id,
                status=TaskStatus.SUCCESS,
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
            logger.error(f"Error processing receipt {task_id}: {e}")
            return ResultMessage(
                task_id=task_id,
                status=TaskStatus.FAILED,
                result_type="receipt",
                result_data={},
                error=str(e),
            )

    def _handle_message(self, msg):
        try:
            message_data = json.loads(msg.value().decode("utf-8"))

            if message_data.get("task_type") != TaskType.RECEIPT.value:
                logger.warning(f"Received non-receipt message: {message_data.get('task_type')}")
                return

            loop = self._get_async_loop()
            result = loop.run_until_complete(self._process_message(message_data))
            self._send_result(result)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode message: {e}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")

    def start(self):
        self._running = True
        topic = self.config.topics.get("tasks_receipt", "tasks.receipt")
        self.consumer.subscribe([topic])
        logger.info(f"Subscribed to topic: {topic}")

        try:
            while self._running:
                msg = self.consumer.poll(timeout=1.0)
                if msg is not None and not msg.error():
                    self._handle_message(msg)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            self.stop()

    def stop(self):
        self._running = False
        if self._loop and not self._loop.is_closed():
            self._loop.close()
        self.consumer.close()
        logger.info("Consumer stopped")
