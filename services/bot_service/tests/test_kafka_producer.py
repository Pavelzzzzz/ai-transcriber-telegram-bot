import os
import sys
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
)

from services.bot_service.kafka_consumer import ResultConsumer
from services.bot_service.kafka_producer import TaskProducer
from services.common.schemas import ResultMessage, TaskMessage, TaskStatus, TaskType


class TestTaskMessage:
    def test_create_task_message(self):
        task = TaskMessage(
            task_id="test-123",
            task_type=TaskType.OCR,
            user_id=12345,
            chat_id=67890,
            timestamp=datetime.now(),
            file_path="/path/to/image.jpg",
        )

        assert task.task_id == "test-123"
        assert task.task_type == TaskType.OCR
        assert task.user_id == 12345
        assert task.chat_id == 67890

    def test_task_message_to_json(self):
        task = TaskMessage(
            task_id="test-123",
            task_type=TaskType.TRANSCRIBE,
            user_id=12345,
            chat_id=67890,
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            file_path="/path/to/audio.ogg",
        )

        json_str = task.to_json()
        assert "test-123" in json_str
        assert "transcribe" in json_str
        assert "12345" in json_str

    def test_task_message_from_json(self):
        json_str = '{"task_id": "test-456", "task_type": "ocr", "user_id": 111, "chat_id": 222, "timestamp": "2024-01-01T12:00:00", "file_path": "/test.jpg", "metadata": {}}'

        task = TaskMessage.from_json(json_str)

        assert task.task_id == "test-456"
        assert task.task_type == TaskType.OCR
        assert task.user_id == 111
        assert task.chat_id == 222


class TestResultMessage:
    def test_create_result_message(self):
        result = ResultMessage(
            task_id="test-123",
            status=TaskStatus.SUCCESS,
            result_type="text",
            result_data={"text": "Hello World"},
        )

        assert result.task_id == "test-123"
        assert result.status == TaskStatus.SUCCESS
        assert result.result_data["text"] == "Hello World"

    def test_result_message_to_json(self):
        result = ResultMessage(
            task_id="test-123",
            status=TaskStatus.FAILED,
            result_type="text",
            error="Processing failed",
        )

        json_str = result.to_json()
        assert "test-123" in json_str
        assert "failed" in json_str
        assert "Processing failed" in json_str

    def test_result_message_from_json(self):
        json_str = '{"task_id": "test-789", "status": "success", "result_type": "transcription", "result_data": {"text": "Test"}, "error": null, "timestamp": "2024-01-01T12:00:00"}'

        result = ResultMessage.from_json(json_str)

        assert result.task_id == "test-789"
        assert result.status == TaskStatus.SUCCESS


class TestTaskProducer:
    @pytest.fixture
    def mock_kafka_config(self):
        config = Mock()
        config.bootstrap_servers = "localhost:9092"
        config.client_id = "test-client"
        config.topics = {
            "tasks_ocr": "tasks.ocr",
            "tasks_transcribe": "tasks.transcribe",
            "tasks_image_gen": "tasks.image_gen",
            "results_ocr": "results.ocr",
            "results_transcribe": "results.transcribe",
            "results_image_gen": "results.image_gen",
        }
        return config

    @pytest.fixture
    def producer(self, mock_kafka_config):
        return TaskProducer(mock_kafka_config)

    def test_get_topic_for_task_type_ocr(self, producer):
        topic = producer._get_topic_for_task_type(TaskType.OCR)
        assert topic == "tasks.ocr"

    def test_get_topic_for_task_type_transcribe(self, producer):
        topic = producer._get_topic_for_task_type(TaskType.TRANSCRIBE)
        assert topic == "tasks.transcribe"

    def test_get_topic_for_task_type_image_gen(self, producer):
        topic = producer._get_topic_for_task_type(TaskType.IMAGE_GEN)
        assert topic == "tasks.image_gen"

    def test_create_ocr_task(self, producer):
        task = producer.create_ocr_task(
            user_id=12345, chat_id=67890, file_path="/path/to/image.jpg"
        )

        assert task.task_type == TaskType.OCR
        assert task.user_id == 12345
        assert task.chat_id == 67890
        assert task.file_path == "/path/to/image.jpg"

    def test_create_transcribe_task(self, producer):
        task = producer.create_transcribe_task(
            user_id=12345, chat_id=67890, file_path="/path/to/audio.ogg"
        )

        assert task.task_type == TaskType.TRANSCRIBE
        assert task.user_id == 12345
        assert task.file_path == "/path/to/audio.ogg"

    def test_create_image_gen_task(self, producer):
        task = producer.create_image_gen_task(
            user_id=12345, chat_id=67890, prompt="A beautiful sunset"
        )

        assert task.task_type == TaskType.IMAGE_GEN
        assert task.file_path == "A beautiful sunset"

    def test_create_task_with_metadata(self, producer):
        task = producer.create_ocr_task(
            user_id=12345,
            chat_id=67890,
            file_path="/path/to/image.jpg",
            metadata={"language": "ru"},
        )

        assert task.metadata["language"] == "ru"

    @patch("services.bot_service.kafka_producer.KafkaProducer")
    def test_send_task_success(self, mock_kafka_class, producer):
        mock_producer = Mock()
        mock_future = Mock()
        mock_future.get.return_value = Mock(topic="tasks.ocr", partition=0)
        mock_producer.send.return_value = mock_future
        mock_kafka_class.return_value = mock_producer

        task = TaskMessage(
            task_id="test-123",
            task_type=TaskType.OCR,
            user_id=12345,
            chat_id=67890,
            timestamp=datetime.now(),
            file_path="/path/to/image.jpg",
        )

        result = producer.send_task(task)

        assert result is True
        mock_producer.send.assert_called_once()


class TestResultConsumer:
    @pytest.fixture
    def mock_kafka_config(self):
        config = Mock()
        config.bootstrap_servers = "localhost:9092"
        config.client_id = "test-client"
        config.topics = {
            "results_ocr": "results.ocr",
            "results_transcribe": "results.transcribe",
            "results_image_gen": "results.image_gen",
        }
        return config

    @pytest.fixture
    def callback(self):
        return Mock()

    def test_init(self, mock_kafka_config, callback):
        consumer = ResultConsumer(mock_kafka_config, callback)

        assert consumer.config == mock_kafka_config
        assert consumer.result_callback == callback
        assert consumer._running is False
