import logging
import queue
import time
from abc import ABC, abstractmethod
from concurrent.futures import Future
from threading import Lock, Thread

from .schemas import ResultMessage, TaskMessage, TaskStatus

logger = logging.getLogger(__name__)

POLL_TIMEOUT_MS = 5000
SESSION_TIMEOUT_MS = 30000
HEARTBEAT_INTERVAL_MS = 10000


class BaseKafkaConsumer(ABC):
    """Base class for Kafka consumers with common polling and processing logic."""

    def __init__(
        self,
        config,
        topic_key: str,
        group_suffix: str,
        result_sender=None,
    ):
        self.config = config
        self.topic_key = topic_key
        self.topic = config.topics.get(topic_key)
        self.group_id = f"{config.client_id}_{group_suffix}_group"
        self.client_id = f"{config.client_id}_{group_suffix}_consumer"
        self.result_sender = result_sender
        self._consumer = None
        self._running = False
        self._poll_thread: Thread | None = None
        self._process_thread: Thread | None = None
        self._task_queue: queue.Queue = queue.Queue()
        self._pending_tasks: dict[str, Future] = {}
        self._tasks_lock = Lock()

    def _get_consumer(self):
        if self._consumer is None:
            from kafka import KafkaConsumer

            self._consumer = KafkaConsumer(
                self.topic,
                bootstrap_servers=self.config.bootstrap_servers,
                client_id=self.client_id,
                value_deserializer=lambda v: v.decode("utf-8"),
                auto_offset_reset="earliest",
                group_id=self.group_id,
                session_timeout_ms=SESSION_TIMEOUT_MS,
                heartbeat_interval_ms=HEARTBEAT_INTERVAL_MS,
            )
        return self._consumer

    def _poll_loop(self) -> None:
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

    def _process_loop(self) -> None:
        while self._running:
            try:
                task = self._task_queue.get(timeout=1)

                if task is None:
                    continue

                logger.info(f"Processing task: {task.task_id}")

                result = self.process_task(task)

                if result and self.result_sender:
                    self.result_sender(result)
                    logger.info(f"Result sent for task {task.task_id}")

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in process loop: {e}")

    @abstractmethod
    def process_task(self, task: TaskMessage) -> ResultMessage | None:
        """Process a task - must be implemented by subclasses."""
        pass

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

        if self._consumer:
            self._consumer.close()
            self._consumer = None

        logger.info(f"{self.__class__.__name__} stopped")
