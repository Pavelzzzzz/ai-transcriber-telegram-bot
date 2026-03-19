import queue
import threading
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from services.common.schemas import TaskMessage, TaskType


@pytest.fixture
def mock_config():
    config = Mock()
    config.topics = {"tasks_image_gen": "tasks.image_gen"}
    config.bootstrap_servers = "localhost:9092"
    config.client_id = "test"
    return config


@pytest.fixture
def mock_sender():
    return Mock()


@pytest.fixture
def mock_processor():
    processor = Mock()
    processor.generate_image = Mock()
    return processor


class TestKafkaConsumerTimeout:
    """Tests for Kafka consumer timeout settings"""

    def test_consumer_uses_correct_timeout(self, mock_config, mock_sender):
        from services.image_gen_service.kafka_consumer import (
            HEARTBEAT_INTERVAL_MS,
            SESSION_TIMEOUT_MS,
            ImageGenKafkaConsumer,
        )

        consumer = ImageGenKafkaConsumer(mock_config, mock_sender)

        with patch("kafka.KafkaConsumer") as mock_kafka:
            mock_kafka.return_value = Mock()
            consumer._get_consumer()

            mock_kafka.assert_called_once()
            call_kwargs = mock_kafka.call_args[1]

            assert call_kwargs["session_timeout_ms"] == SESSION_TIMEOUT_MS
            assert call_kwargs["heartbeat_interval_ms"] == HEARTBEAT_INTERVAL_MS
            assert call_kwargs["max_poll_records"] == 1
            assert call_kwargs["max_poll_interval_ms"] == 10800000


class TestKafkaConsumerThreads:
    """Tests for separate poll/process threads"""

    def test_separate_threads_created(self, mock_config, mock_sender, mock_processor):
        from services.image_gen_service.kafka_consumer import ImageGenKafkaConsumer

        consumer = ImageGenKafkaConsumer(mock_config, mock_sender, processor=mock_processor)

        with patch.object(consumer, "_poll_loop"):
            with patch.object(consumer, "_process_loop"):
                consumer.start()

                assert consumer._poll_thread is not None
                assert consumer._process_thread is not None
                assert isinstance(consumer._poll_thread, threading.Thread)
                assert isinstance(consumer._process_thread, threading.Thread)

                consumer.stop()

    def test_task_queue_created(self, mock_config, mock_sender):
        from services.image_gen_service.kafka_consumer import ImageGenKafkaConsumer

        consumer = ImageGenKafkaConsumer(mock_config, mock_sender)

        assert isinstance(consumer._task_queue, queue.Queue)

    def test_executor_created_with_one_worker(self, mock_config, mock_sender):
        from services.image_gen_service.kafka_consumer import ImageGenKafkaConsumer

        consumer = ImageGenKafkaConsumer(mock_config, mock_sender)

        assert consumer._executor is not None
        assert consumer._executor._max_workers == 1

    def test_stop_sets_running_false(self, mock_config, mock_sender):
        from services.image_gen_service.kafka_consumer import ImageGenKafkaConsumer

        consumer = ImageGenKafkaConsumer(mock_config, mock_sender)
        consumer._running = True

        with patch.object(consumer, "_poll_loop"):
            with patch.object(consumer, "_process_loop"):
                consumer.start()
                assert consumer._running is True

                consumer.stop()
                assert consumer._running is False


class TestKafkaConsumerQueue:
    """Tests for thread-safe task queue"""

    def test_task_queued(self, mock_config, mock_sender):
        from services.image_gen_service.kafka_consumer import ImageGenKafkaConsumer

        consumer = ImageGenKafkaConsumer(mock_config, mock_sender)

        task = TaskMessage(
            task_id="test-123",
            task_type=TaskType.IMAGE_GEN,
            user_id=123,
            chat_id=456,
            timestamp=datetime.now(),
            file_path="test prompt",
        )

        consumer._task_queue.put(task)

        assert consumer._task_queue.qsize() == 1
        retrieved_task = consumer._task_queue.get_nowait()
        assert retrieved_task.task_id == "test-123"

    def test_stop_signal_sent_to_queue(self, mock_config, mock_sender):
        from services.image_gen_service.kafka_consumer import ImageGenKafkaConsumer

        consumer = ImageGenKafkaConsumer(mock_config, mock_sender)

        consumer._task_queue.put(None)

        assert consumer._task_queue.qsize() == 1
        signal = consumer._task_queue.get_nowait()
        assert signal is None


class TestKafkaConsumerProcessing:
    """Tests for task processing"""

    def test_pending_tasks_tracked(self, mock_config, mock_sender, mock_processor):
        from services.image_gen_service.kafka_consumer import ImageGenKafkaConsumer

        consumer = ImageGenKafkaConsumer(mock_config, mock_sender, processor=mock_processor)

        task = TaskMessage(
            task_id="test-456",
            task_type=TaskType.IMAGE_GEN,
            user_id=123,
            chat_id=456,
            timestamp=datetime.now(),
            file_path="test prompt",
        )

        future = Mock()
        future.done.return_value = True
        future.cancelled.return_value = False
        future.result.return_value = Mock()

        with consumer._tasks_lock:
            consumer._pending_tasks[task.task_id] = future

        status = consumer._get_queue_status()
        assert status["pending"] == 1
        assert status["max_workers"] == 1


class TestKafkaConsumerNotification:
    """Tests for notification sender"""

    def test_notification_sender_setter(self, mock_config, mock_sender):
        from services.image_gen_service.kafka_consumer import ImageGenKafkaConsumer

        consumer = ImageGenKafkaConsumer(mock_config, mock_sender)
        notif_sender = Mock()

        consumer.set_notification_sender(notif_sender)

        assert consumer._notification_sender is notif_sender

    def test_send_notification_uses_sender(self, mock_config, mock_sender):
        from services.image_gen_service.kafka_consumer import ImageGenKafkaConsumer

        consumer = ImageGenKafkaConsumer(mock_config, mock_sender)

        notif_sender = Mock()
        consumer._notification_sender = notif_sender

        task = TaskMessage(
            task_id="test-789",
            task_type=TaskType.IMAGE_GEN,
            user_id=123,
            chat_id=456,
            timestamp=datetime.now(),
            file_path="test prompt",
        )

        consumer._send_started_notification(task)

        notif_sender.assert_called_once()
        call_args = notif_sender.call_args[0]
        assert "123" in call_args[0]
        assert "test-789" in call_args[1]
