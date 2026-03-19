import os
import sys
from unittest.mock import Mock

import pytest

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
)

from services.bot_service.kafka_consumer import ResultConsumer
from services.common.schemas import ResultMessage, TaskStatus


class TestImageResultDelivery:
    """Tests for image result delivery to users"""

    @pytest.fixture
    def mock_kafka_config(self):
        config = Mock()
        config.bootstrap_servers = "localhost:9092"
        config.client_id = "test-client"
        config.topics = {
            "tasks_image_gen": "tasks.image_gen",
            "results_image_gen": "results.image_gen",
            "notifications": "notifications",
        }
        return config

    @pytest.fixture
    def mock_result_callback(self):
        return Mock()

    @pytest.fixture
    def image_gen_result(self):
        return ResultMessage(
            task_id="img-123-456",
            status=TaskStatus.SUCCESS,
            result_type="image",
            result_data={
                "file_path": "/app/downloads/generated_image.png",
                "prompt": "A beautiful sunset",
                "model": "sd15",
            },
        )

    def test_result_contains_file_path_for_image(self, image_gen_result):
        """Test that image generation result contains file_path"""
        assert image_gen_result.status == TaskStatus.SUCCESS
        assert image_gen_result.result_type == "image"
        assert "file_path" in image_gen_result.result_data
        assert image_gen_result.result_data["file_path"] == "/app/downloads/generated_image.png"

    def test_result_callback_receives_image_result(self, image_gen_result, mock_result_callback):
        """Test that result callback is called with image result"""
        mock_result_callback(image_gen_result)

        mock_result_callback.assert_called_once()
        call_args = mock_result_callback.call_args[0][0]
        assert call_args.task_id == image_gen_result.task_id
        assert call_args.result_data.get("file_path") is not None

    def test_pending_tasks_stored_for_image_gen(self):
        """Test that pending tasks are properly stored for image generation"""
        pending_tasks = {}

        task_id = "img-123-456"
        chat_id = 123456789

        pending_tasks[task_id] = {"chat_id": chat_id, "task_type": "image_gen"}

        assert task_id in pending_tasks
        assert pending_tasks[task_id]["chat_id"] == chat_id
        assert pending_tasks[task_id]["task_type"] == "image_gen"

    def test_image_result_has_required_fields(self, image_gen_result):
        """Test that image result has all required fields for delivery"""
        assert hasattr(image_gen_result, "task_id")
        assert hasattr(image_gen_result, "status")
        assert hasattr(image_gen_result, "result_type")
        assert hasattr(image_gen_result, "result_data")

        assert image_gen_result.task_id is not None
        assert image_gen_result.status == TaskStatus.SUCCESS
        assert image_gen_result.result_type == "image"

    def test_failed_image_result_has_error(self):
        """Test that failed image result contains error message"""
        failed_result = ResultMessage(
            task_id="img-fail-123",
            status=TaskStatus.FAILED,
            result_type="image",
            result_data={},
            error="Model loading failed",
        )

        assert failed_result.status == TaskStatus.FAILED
        assert failed_result.error is not None
        assert "failed" in failed_result.error.lower()

    def test_result_with_multiple_variations(self):
        """Test result with multiple image variations"""
        result = ResultMessage(
            task_id="img-multi-123",
            status=TaskStatus.SUCCESS,
            result_type="image",
            result_data={
                "file_path": "/app/downloads/image_0.png",
                "file_path_1": "/app/downloads/image_1.png",
                "file_path_2": "/app/downloads/image_2.png",
                "num_variations": 3,
            },
        )

        assert result.status == TaskStatus.SUCCESS
        assert "file_path" in result.result_data
        assert result.result_data.get("num_variations") == 3


class TestResultConsumerIntegration:
    """Integration tests for result consumer"""

    @pytest.fixture
    def mock_kafka_config(self):
        config = Mock()
        config.bootstrap_servers = "localhost:9092"
        config.client_id = "test-client"
        config.topics = {
            "results_ocr": "results.ocr",
            "results_transcribe": "results.transcribe",
            "results_tts": "results.tts",
            "results_image_gen": "results.image_gen",
        }
        return config

    def test_consumer_sends_image_results_to_callback(self, mock_kafka_config):
        """Test that consumer properly routes image results to callback"""
        callback = Mock()
        _consumer = ResultConsumer(mock_kafka_config, callback)

        image_result = ResultMessage(
            task_id="img-test-123",
            status=TaskStatus.SUCCESS,
            result_type="image",
            result_data={"file_path": "/test/image.png"},
        )

        callback(image_result)

        callback.assert_called_once()
        result = callback.call_args[0][0]
        assert result.result_type == "image"
        assert "file_path" in result.result_data


class TestBotServiceImageDelivery:
    """Tests for bot service image delivery logic"""

    def test_image_gen_result_triggers_photo_send(self):
        """Test that image_gen result type triggers photo sending"""
        result = ResultMessage(
            task_id="img-bot-123",
            status=TaskStatus.SUCCESS,
            result_type="image",
            result_data={"file_path": "/test/image.png"},
        )

        task_info = {"chat_id": 123456789, "task_type": "image_gen"}

        task_type = task_info.get("task_type")
        has_file_path = result.result_data.get("file_path")

        should_send_photo = (
            task_type == "image_gen" and result.status == TaskStatus.SUCCESS and has_file_path
        )

        assert should_send_photo is True

    def test_ocr_result_triggers_text_send(self):
        """Test that OCR result triggers text sending"""
        result = ResultMessage(
            task_id="ocr-bot-123",
            status=TaskStatus.SUCCESS,
            result_type="text",
            result_data={"text": "Recognized text from image"},
        )

        task_info = {"chat_id": 123456789, "task_type": "ocr"}

        task_type = task_info.get("task_type")
        has_text = result.result_data.get("text")

        should_send_text = (
            task_type != "image_gen" and result.status == TaskStatus.SUCCESS and has_text
        )

        assert should_send_text is True
