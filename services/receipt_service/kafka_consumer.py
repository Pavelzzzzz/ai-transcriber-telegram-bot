import asyncio
import json
import logging
import queue
import time
from concurrent.futures import Future
from threading import Thread

from ..common import ResultMessage, TaskMessage, TaskStatus, TaskType
from .processor import ReceiptProcessor

logger = logging.getLogger(__name__)

MAX_WORKERS = 2
POLL_TIMEOUT_MS = 5000


class ReceiptKafkaConsumer:
    def __init__(self, config, result_sender=None, processor=None):
        self.config = config
        self.result_sender = result_sender
        self.processor = processor if processor else ReceiptProcessor()
        self._consumer = None
        self._running = False
        self._poll_thread: Thread | None = None
        self._process_thread: Thread | None = None
        self._task_queue: queue.Queue = queue.Queue()
        self._executor = None
        self._pending_tasks: dict[str, Future] = {}
        self._async_loop: asyncio.AbstractEventLoop | None = None

    def _get_consumer(self):
        if self._consumer is None:
            from kafka import KafkaConsumer

            self._consumer = KafkaConsumer(
                self.config.topics["tasks_receipt"],
                bootstrap_servers=self.config.bootstrap_servers,
                client_id=f"{self.config.client_id}_receipt_consumer",
                value_deserializer=lambda v: v.decode("utf-8"),
                auto_offset_reset="earliest",
                group_id=f"{self.config.client_id}_receipt_group",
                session_timeout_ms=30000,
                heartbeat_interval_ms=10000,
            )
        return self._consumer

    def _poll_loop(self):
        consumer = self._get_consumer()

        while self._running:
            try:
                messages = consumer.poll(timeout_ms=POLL_TIMEOUT_MS)

                for topic_partition, records in messages.items():
                    for record in records:
                        try:
                            task = TaskMessage.from_json(record.value)
                            if task.task_type == TaskType.RECEIPT:
                                logger.debug(f"Polled task: {task.task_id}")
                                self._task_queue.put(task)
                        except Exception as e:
                            logger.error(f"Error parsing message: {e}")

            except Exception as e:
                logger.error(f"Error in poll loop: {e}")
                time.sleep(1)

    def _process_loop(self):
        self._executor = asyncio.new_event_loop()
        self._async_loop = self._executor
        asyncio.set_event_loop(self._executor)

        while self._running:
            try:
                task = self._task_queue.get(timeout=1)

                if task is None:
                    continue

                logger.info(f"Processing receipt task: {task.task_id}")

                future = self._executor.run_in_executor(None, self._run_task_sync, task)
                self._pending_tasks[task.task_id] = future

                future.add_done_callback(lambda f, tid=task.task_id: self._cleanup_task(tid, f))

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in process loop: {e}")

    def _run_task_sync(self, task: TaskMessage) -> ResultMessage:
        return self._async_loop.run_until_complete(self._process_task_async(task))

    def _cleanup_task(self, task_id: str, future: Future):
        try:
            if future.done() and not future.cancelled():
                result = future.result()
                if result and self.result_sender:
                    self.result_sender(result)
                    logger.info(f"Result sent for task {task_id}")
        except Exception as e:
            logger.error(f"Error sending result for task {task_id}: {e}")
        finally:
            if task_id in self._pending_tasks:
                del self._pending_tasks[task_id]
            logger.info(f"Task {task_id} removed from pending queue")

    async def _process_task_async(self, task: TaskMessage) -> ResultMessage:
        try:
            items_text = task.file_path or ""
            unknown_items_data = task.metadata.get("unknown_items", []) if task.metadata else []

            logger.info(f"Processing receipt task {task.task_id} for user {task.user_id}")

            result = await self.processor.process_receipt(items_text, task.user_id)

            if result["status"] == "error":
                return ResultMessage(
                    task_id=task.task_id,
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
                task_id=task.task_id,
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
            logger.error(f"Error processing receipt {task.task_id}: {e}")
            return ResultMessage(
                task_id=task.task_id,
                status=TaskStatus.FAILED,
                result_type="receipt",
                result_data={},
                error=str(e),
            )

    def start(self):
        if self._running:
            return

        self._running = True

        self._poll_thread = Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

        self._process_thread = Thread(target=self._process_loop, daemon=True)
        self._process_thread.start()

        logger.info("Receipt consumer started")

    def stop(self):
        self._running = False

        self._task_queue.put(None)

        if self._poll_thread:
            self._poll_thread.join(timeout=5)
        if self._process_thread:
            self._process_thread.join(timeout=5)

        if self._executor and not self._executor.is_closed():
            self._executor.close()

        if self._async_loop and not self._async_loop.is_closed():
            self._async_loop.close()

        if self._consumer:
            self._consumer.close()
            self._consumer = None

        logger.info("Receipt consumer stopped")
