import asyncio
import logging
import os
import queue
import time
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from threading import Lock, Thread

from ..common import KafkaConsumerError, ResultMessage, TaskMessage, TaskStatus
from .processor import ImageGenerationProcessor

logger = logging.getLogger(__name__)

MAX_WORKERS = int(os.getenv("IMAGE_GEN_MAX_WORKERS", "1"))

SESSION_TIMEOUT_MS = 300000
HEARTBEAT_INTERVAL_MS = 60000
POLL_TIMEOUT_MS = 5000


class ImageGenKafkaConsumer:
    def __init__(self, config, result_sender: Callable[[ResultMessage], None], processor=None):
        self.config = config
        self.result_sender = result_sender
        self.processor = processor if processor else ImageGenerationProcessor()
        self._consumer = None
        self._running = False

        self._poll_thread: Thread | None = None
        self._process_thread: Thread | None = None

        self._task_queue: queue.Queue = queue.Queue()

        self._executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
        self._pending_tasks: dict[str, Future] = {}
        self._tasks_lock = Lock()
        self._notification_sender: Callable[[str, str], None] | None = None
        self._async_loop: asyncio.AbstractEventLoop | None = None

    def set_notification_sender(self, sender: Callable[[str, str], None]):
        self._notification_sender = sender

    def _get_consumer(self):
        if self._consumer is None:
            from kafka import KafkaConsumer

            self._consumer = KafkaConsumer(
                self.config.topics["tasks_image_gen"],
                bootstrap_servers=self.config.bootstrap_servers,
                client_id=f"{self.config.client_id}_image_gen_consumer",
                value_deserializer=lambda v: v.decode("utf-8"),
                auto_offset_reset="earliest",
                group_id=f"{self.config.client_id}_image_gen_group",
                max_poll_interval_ms=10800000,
                max_poll_records=1,
                session_timeout_ms=SESSION_TIMEOUT_MS,
                heartbeat_interval_ms=HEARTBEAT_INTERVAL_MS,
            )
        return self._consumer

    def _get_queue_status(self) -> dict:
        with self._tasks_lock:
            pending = len(self._pending_tasks)
            processing = sum(1 for f in self._pending_tasks.values() if not f.done())
            completed = sum(1 for f in self._pending_tasks.values() if f.done())

            tasks_detail = []
            for task_id, future in self._pending_tasks.items():
                status = (
                    "completed"
                    if future.done()
                    else ("processing" if future.running() else "queued")
                )
                tasks_detail.append({"task_id": task_id, "status": status})

        return {
            "pending": pending,
            "processing": processing,
            "completed": completed,
            "max_workers": MAX_WORKERS,
            "tasks": tasks_detail,
        }

    def _send_started_notification(self, task: TaskMessage):
        if self._notification_sender:
            try:
                user_id = str(task.user_id or task.metadata.get("user_id", "unknown"))
                self._notification_sender(
                    user_id,
                    f"Started processing: {task.task_id[:8]}...\nPrompt: {task.file_path[:50]}...",
                )
            except Exception as e:
                logger.warning(f"Failed to send started notification: {e}")

    def _poll_loop(self):
        consumer = self._get_consumer()

        while self._running:
            try:
                messages = consumer.poll(timeout_ms=POLL_TIMEOUT_MS)

                for topic_partition, records in messages.items():
                    for record in records:
                        try:
                            task = TaskMessage.from_json(record.value)
                            logger.debug(f"Polled task: {task.task_id}")
                            self._task_queue.put(task)
                        except Exception as e:
                            logger.error(f"Error parsing message: {e}")

            except Exception as e:
                logger.error(f"Error in poll loop: {e}")
                time.sleep(1)

    def _process_loop(self):
        self._async_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._async_loop)

        while self._running:
            try:
                task = self._task_queue.get(timeout=1)

                if task is None:
                    continue

                logger.info(f"Processing task: {task.task_id}")

                future = self._executor.submit(self._run_task_sync, task)

                with self._tasks_lock:
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
            with self._tasks_lock:
                if task_id in self._pending_tasks:
                    del self._pending_tasks[task_id]
            logger.info(f"Task {task_id} removed from pending queue")

    async def _process_task_async(self, task: TaskMessage) -> ResultMessage:
        try:
            prompt = task.file_path
            metadata = task.metadata or {}

            logger.info(f"Received image gen task {task.task_id}: metadata={metadata}")

            self._send_started_notification(task)

            result = await self.processor.generate_image(prompt, metadata)

            return ResultMessage(
                task_id=task.task_id,
                status=TaskStatus.SUCCESS,
                result_type="image",
                result_data=result,
            )
        except Exception as e:
            logger.error(f"Failed to process image generation task {task.task_id}: {e}")
            return ResultMessage(
                task_id=task.task_id,
                status=TaskStatus.FAILED,
                result_type="image",
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

        logger.info(f"Consumer started: poll_thread + process_thread + {MAX_WORKERS} workers")

    def stop(self):
        self._running = False

        self._task_queue.put(None)

        if self._poll_thread:
            self._poll_thread.join(timeout=5)
        if self._process_thread:
            self._process_thread.join(timeout=5)

        if self._async_loop and not self._async_loop.is_closed():
            self._async_loop.close()

        self._executor.shutdown(wait=True)
        if self._consumer:
            self._consumer.close()
            self._consumer = None

        logger.info("Consumer stopped")
