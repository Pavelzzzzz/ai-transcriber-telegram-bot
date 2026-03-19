from datetime import datetime

import pytest

from services.common.schemas import (
    ResultMessage,
    TaskMessage,
    TaskStatus,
    TaskType,
)


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
        assert task.file_path == "/path/to/image.jpg"

    def test_task_message_to_json(self):
        task = TaskMessage(
            task_id="test-456",
            task_type=TaskType.IMAGE_GEN,
            user_id=111,
            chat_id=222,
            timestamp=datetime.now(),
            file_path="a cat",
            metadata={"model": "sd15"},
        )

        json_str = task.to_json()
        assert "test-456" in json_str
        assert "image_gen" in json_str

    def test_task_message_from_json(self):
        json_str = '{"task_id": "test-789", "task_type": "transcribe", "user_id": 123, "chat_id": 456, "file_path": "/audio.ogg", "timestamp": "2024-01-01T12:00:00"}'

        task = TaskMessage.from_json(json_str)

        assert task.task_id == "test-789"
        assert task.task_type == TaskType.TRANSCRIBE


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


class TestTaskStatus:
    def test_task_status_values(self):
        assert TaskStatus.SUCCESS.value == "success"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.PENDING.value == "pending"

    def test_task_type_values(self):
        assert TaskType.OCR.value == "ocr"
        assert TaskType.TRANSCRIBE.value == "transcribe"
        assert TaskType.IMAGE_GEN.value == "image_gen"
