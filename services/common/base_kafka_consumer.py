import asyncio
import logging
import queue
import time
from abc import ABC, abstractmethod
from concurrent.futures import Future
from threading import Lock, Thread
from typing import TYPE_CHECKING

from .schemas import ResultMessage, TaskMessage

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)

POLL_TIMEOUT_MS = 5000
DEFAULT_POLL_TIMEOUT_MS = 1000
SESSION_TIMEOUT_MS = 30000
HEARTBEAT_INTERVAL_MS = 10000


class BaseKafkaConsumer(ABC):
    """Base class for Kafka consumers with common polling and processing logic.

    Supports both synchronous and asynchronous task processing.
    Subclasses must implement the process_task method.
    """

    def __init__(
        self,
        config,
        topic_key: str,
        group_suffix: str,
        result_sender: "Callable[[ResultMessage], None] | None" = None,
        max_workers: int = 1,
        poll_timeout_ms: int = DEFAULT_POLL_TIMEOUT_MS,
        session_timeout_ms: int = SESSION_TIMEOUT_MS,
        heartbeat_interval_ms: int = HEARTBEAT_INTERVAL_MS,
    ):
        """Initialize the base Kafka consumer.

        Args:
            config: Kafka configuration object
            topic_key: Key to look up topic in config.topics dict
            group_suffix: Suffix for consumer group name
            result_sender: Callback to send results
            max_workers: Max parallel workers (1 = sync, >1 = thread pool)
            poll_timeout_ms: Timeout for polling messages
            session_timeout_ms: Kafka session timeout
            heartbeat_interval_ms: Kafka heartbeat interval
        """
        self.config = config
        self.topic_key = topic_key
        self.topic = config.topics.get(topic_key)
        self.group_id = f"{config.client_id}_{group_suffix}_group"
        self.client_id = f"{config.client_id}_{group_suffix}_consumer"
        self.result_sender = result_sender
        self.max_workers = max_workers
        self.poll_timeout_ms = poll_timeout_ms
        self.session_timeout_ms = session_timeout_ms
        self.heartbeat_interval_ms = heartbeat_interval_ms

        self._consumer = None
        self._running = False
        self._poll_thread: Thread | None = None
        self._process_thread: Thread | None = None
        self._task_queue: queue.Queue = queue.Queue()
        self._pending_tasks: dict[str, Future] = {}
        self._tasks_lock = Lock()
        self._async_loop: asyncio.AbstractEventLoop | None = None

        if max_workers > 1:
            from concurrent.futures import ThreadPoolExecutor

            self._executor = ThreadPoolExecutor(max_workers=max_workers)
        else:
            self._executor = None

    def _get_consumer(self):
        if self._consumer is None:
            from kafka import KafkaConsumer

            consumer_kwargs = {
                "bootstrap_servers": self.config.bootstrap_servers,
                "client_id": self.client_id,
                "value_deserializer": lambda v: v.decode("utf-8"),
                "auto_offset_reset": "earliest",
                "group_id": self.group_id,
                "session_timeout_ms": self.session_timeout_ms,
                "heartbeat_interval_ms": self.heartbeat_interval_ms,
            }

            self._consumer = KafkaConsumer(self.topic, **consumer_kwargs)
        return self._consumer

    def _poll_loop(self) -> None:
        consumer = self._get_consumer()

        while self._running:
            try:
                messages = consumer.poll(timeout_ms=self.poll_timeout_ms)

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

    def _process_loop(self) -> None:
        if self.max_workers > 1 or self._is_async():
            self._async_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._async_loop)

        while self._running:
            try:
                task = self._task_queue.get(timeout=1)

                if task is None:
                    continue

                logger.info(f"Processing task: {task.task_id}")

                if self._executor:
                    future = self._executor.submit(self._run_task_sync, task)
                    with self._tasks_lock:
                        self._pending_tasks[task.task_id] = future
                    future.add_done_callback(lambda f, tid=task.task_id: self._cleanup_task(tid, f))
                else:
                    result = self._run_task_sync(task)
                    if result and self.result_sender:
                        self.result_sender(result)
                        logger.info(f"Result sent for task {task.task_id}")

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in process loop: {e}")

    def _is_async(self) -> bool:
        """Check if process_task is async by examining the method."""
        import inspect

        return inspect.iscoroutinefunction(self.process_task)

    def _run_task_sync(self, task: TaskMessage) -> ResultMessage | None:
        if self._is_async() and self._async_loop:
            return self._async_loop.run_until_complete(self.process_task(task))
        return self.process_task(task)

    def _cleanup_task(self, task_id: str, future: Future) -> None:
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

    @abstractmethod
    def process_task(self, task: TaskMessage) -> ResultMessage | None:
        """Process a task - must be implemented by subclasses.

        Can be sync or async method.
        """
        pass

    def get_queue_status(self) -> dict:
        """Return current queue status. Override in subclass if needed."""
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
            "max_workers": self.max_workers,
            "tasks": tasks_detail,
        }

    def start(self) -> None:
        if self._running:
            return

        self._running = True

        self._poll_thread = Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

        self._process_thread = Thread(target=self._process_loop, daemon=True)
        self._process_thread.start()

        logger.info(f"{self.__class__.__name__} started")

    def stop(self) -> None:
        self._running = False

        self._task_queue.put(None)

        if self._poll_thread:
            self._poll_thread.join(timeout=5)
        if self._process_thread:
            self._process_thread.join(timeout=5)

        if self._async_loop and not self._async_loop.is_closed():
            self._async_loop.close()

        if self._executor:
            self._executor.shutdown(wait=True)

        if self._consumer:
            self._consumer.close()
            self._consumer = None

        logger.info(f"{self.__class__.__name__} stopped")
