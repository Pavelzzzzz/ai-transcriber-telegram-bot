import logging
from datetime import datetime

from ..common import KafkaProducerError, TaskMessage, TaskType

logger = logging.getLogger(__name__)


class TaskProducer:
    def __init__(self, kafka_config):
        self.config = kafka_config
        self._producer = None

    def _get_producer(self):
        if self._producer is None:
            try:
                from kafka import KafkaProducer

                self._producer = KafkaProducer(
                    bootstrap_servers=self.config.bootstrap_servers,
                    client_id=self.config.client_id,
                    value_serializer=lambda v: v.encode("utf-8"),
                    key_serializer=lambda k: k.encode("utf-8") if k else None,
                )
            except Exception as e:
                raise KafkaProducerError(f"Failed to create Kafka producer: {e}", "bot_service")
        return self._producer

    def _get_topic_for_task_type(self, task_type: TaskType) -> str:
        topic_mapping = {
            TaskType.OCR: self.config.topics["tasks_ocr"],
            TaskType.TRANSCRIBE: self.config.topics["tasks_transcribe"],
            TaskType.IMAGE_GEN: self.config.topics["tasks_image_gen"],
            TaskType.RECEIPT: self.config.topics["tasks_receipt"],
        }
        return topic_mapping.get(task_type)

    def send_task(self, task: TaskMessage) -> bool:
        try:
            producer = self._get_producer()
            topic = self._get_topic_for_task_type(task.task_type)

            logger.info(f"Sending task {task.task_id} to topic {topic}")

            future = producer.send(topic, key=str(task.task_id), value=task.to_json())

            record_metadata = future.get(timeout=10)
            logger.info(
                f"Task {task.task_id} sent to {record_metadata.topic}:{record_metadata.partition}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send task {task.task_id}: {e}")
            raise KafkaProducerError(f"Failed to send task: {e}", "bot_service")

    def create_ocr_task(
        self, user_id: int, chat_id: int, file_path: str, metadata: dict = None
    ) -> TaskMessage:
        task = TaskMessage(
            task_id="",
            task_type=TaskType.OCR,
            user_id=user_id,
            chat_id=chat_id,
            timestamp=datetime.now(),
            file_path=file_path,
            metadata=metadata or {},
        )
        return task

    def create_transcribe_task(
        self, user_id: int, chat_id: int, file_path: str, metadata: dict = None
    ) -> TaskMessage:
        task = TaskMessage(
            task_id="",
            task_type=TaskType.TRANSCRIBE,
            user_id=user_id,
            chat_id=chat_id,
            timestamp=datetime.now(),
            file_path=file_path,
            metadata=metadata or {},
        )
        return task

    def create_image_gen_task(
        self, user_id: int, chat_id: int, prompt: str, metadata: dict = None
    ) -> TaskMessage:
        task = TaskMessage(
            task_id="",
            task_type=TaskType.IMAGE_GEN,
            user_id=user_id,
            chat_id=chat_id,
            timestamp=datetime.now(),
            file_path=prompt,
            metadata=metadata or {},
        )
        return task

    def create_receipt_task(
        self, user_id: int, chat_id: int, items_text: str, metadata: dict = None
    ) -> TaskMessage:
        task = TaskMessage(
            task_id="",
            task_type=TaskType.RECEIPT,
            user_id=user_id,
            chat_id=chat_id,
            timestamp=datetime.now(),
            file_path=items_text,
            metadata=metadata or {},
        )
        return task

    def close(self):
        if self._producer:
            self._producer.close()
            self._producer = None
