import os
import sys
from concurrent.futures import Future
from unittest.mock import AsyncMock, Mock

import pytest

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
)

from services.common.schemas import ResultMessage, TaskMessage, TaskStatus, TaskType


class TestImageGenKafkaConsumerResultDelivery:
    """Tests for image generation result delivery"""

    @pytest.fixture
    def mock_processor(self):
        processor = Mock()
        processor.generate_image = AsyncMock(
            return_value={
                "file_path": "/app/downloads/test_image.png",
                "prompt": "test prompt",
                "model": "sd15",
            }
        )
        return processor

    @pytest.fixture
    def mock_result_sender(self):
        return Mock()

    @pytest.fixture
    def sample_task(self):
        return TaskMessage(
            task_id="img-test-123",
            task_type=TaskType.IMAGE_GEN,
            user_id=12345,
            chat_id=67890,
            file_path="A beautiful sunset",
            metadata={"model": "sd15", "style": "", "aspect_ratio": "1:1"},
        )

    def test_result_sender_is_called_on_task_completion(
        self, mock_processor, mock_result_sender, sample_task
    ):
        """Test that result_sender is called when task completes"""
        from services.image_gen_service.kafka_consumer import ImageGenKafkaConsumer

        config = Mock()
        consumer = ImageGenKafkaConsumer(
            config, result_sender=mock_result_sender, processor=mock_processor
        )

        future = Future()
        future.set_result(
            ResultMessage(
                task_id=sample_task.task_id,
                status=TaskStatus.SUCCESS,
                result_type="image",
                result_data={"file_path": "/test.png"},
            )
        )

        consumer._cleanup_task(sample_task.task_id, future)

        mock_result_sender.assert_called_once()
        call_args = mock_result_sender.call_args[0][0]
        assert call_args.task_id == sample_task.task_id
        assert call_args.status == TaskStatus.SUCCESS

    def test_result_sender_not_called_on_task_failure(self, mock_result_sender, sample_task):
        """Test that result_sender is called even on task failure"""
        from services.image_gen_service.kafka_consumer import ImageGenKafkaConsumer

        config = Mock()
        consumer = ImageGenKafkaConsumer(config, result_sender=mock_result_sender, processor=Mock())

        future = Future()
        future.set_result(
            ResultMessage(
                task_id=sample_task.task_id,
                status=TaskStatus.FAILED,
                result_type="image",
                result_data={},
                error="Generation failed",
            )
        )

        consumer._cleanup_task(sample_task.task_id, future)

        mock_result_sender.assert_called_once()

    def test_result_sender_not_called_if_future_cancelled(self, mock_result_sender, sample_task):
        """Test that result_sender is NOT called if future was cancelled"""
        from services.image_gen_service.kafka_consumer import ImageGenKafkaConsumer

        config = Mock()
        consumer = ImageGenKafkaConsumer(config, result_sender=mock_result_sender, processor=Mock())

        future = Future()
        future.cancel()

        consumer._cleanup_task(sample_task.task_id, future)

        mock_result_sender.assert_not_called()

    def test_result_sender_called_with_correct_data(self, mock_result_sender, sample_task):
        """Test that result_sender receives correct result data"""
        from services.image_gen_service.kafka_consumer import ImageGenKafkaConsumer

        config = Mock()
        consumer = ImageGenKafkaConsumer(config, result_sender=mock_result_sender, processor=Mock())

        expected_result = ResultMessage(
            task_id=sample_task.task_id,
            status=TaskStatus.SUCCESS,
            result_type="image",
            result_data={
                "file_path": "/app/downloads/generated.png",
                "prompt": "test prompt",
                "model": "sd15",
                "seed": 12345,
            },
        )

        future = Future()
        future.set_result(expected_result)

        consumer._cleanup_task(sample_task.task_id, future)

        mock_result_sender.assert_called_once()
        result = mock_result_sender.call_args[0][0]

        assert result.task_id == sample_task.task_id
        assert result.status == TaskStatus.SUCCESS
        assert result.result_type == "image"
        assert "file_path" in result.result_data
        assert result.result_data["file_path"] == "/app/downloads/generated.png"


class TestImageGenResultMessage:
    """Tests for image generation result message format"""

    def test_success_result_has_file_path(self):
        """Test that successful result has file_path"""
        result = ResultMessage(
            task_id="img-123",
            status=TaskStatus.SUCCESS,
            result_type="image",
            result_data={
                "file_path": "/app/downloads/image.png",
                "prompt": "test",
                "model": "sd15",
            },
        )

        assert result.status == TaskStatus.SUCCESS
        assert "file_path" in result.result_data

    def test_failed_result_has_error(self):
        """Test that failed result has error message"""
        result = ResultMessage(
            task_id="img-123",
            status=TaskStatus.FAILED,
            result_type="image",
            result_data={},
            error="Model not found",
        )

        assert result.status == TaskStatus.FAILED
        assert result.error is not None

    def test_result_contains_model_info(self):
        """Test that result contains model information"""
        result = ResultMessage(
            task_id="img-123",
            status=TaskStatus.SUCCESS,
            result_type="image",
            result_data={"file_path": "/test.png", "model": "sdxl", "steps": 50, "seed": 42},
        )

        assert result.result_data.get("model") == "sdxl"
        assert result.result_data.get("steps") == 50
        assert result.result_data.get("seed") == 42
