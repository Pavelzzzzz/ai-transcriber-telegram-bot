import os
import sys
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
)

from services.common.schemas import ResultMessage, TaskMessage, TaskStatus, TaskType


class TestOCRServiceIntegration:
    """Integration tests for OCR service"""

    @pytest.mark.integration
    def test_ocr_task_message_creation(self):
        """Test creating OCR task message"""
        task = TaskMessage(
            task_id="ocr-test-123",
            task_type=TaskType.OCR,
            user_id=12345,
            chat_id=67890,
            timestamp=datetime.now(),
            file_path="/test/image.jpg",
            metadata={"language": "ru"},
        )

        assert task.task_type == TaskType.OCR
        assert task.file_path == "/test/image.jpg"
        assert task.metadata["language"] == "ru"

    @pytest.mark.integration
    def test_ocr_result_message_creation(self):
        """Test creating OCR result message"""
        result = ResultMessage(
            task_id="ocr-test-123",
            status=TaskStatus.SUCCESS,
            result_type="ocr",
            result_data={"text": "Extracted text from image", "confidence": 0.95},
        )

        assert result.status == TaskStatus.SUCCESS
        assert result.result_data["text"] == "Extracted text from image"

    @pytest.mark.integration
    def test_ocr_result_with_error(self):
        """Test OCR result with error"""
        result = ResultMessage(
            task_id="ocr-test-456",
            status=TaskStatus.FAILED,
            result_type="ocr",
            result_data={},
            error="Image file not found",
        )

        assert result.status == TaskStatus.FAILED
        assert result.error == "Image file not found"


class TestOCRProcessor:
    """Test OCR processor logic"""

    @pytest.mark.integration
    def test_processor_init(self):
        """Test OCR processor initialization"""
        from services.ocr_service.processor import OCRProcessor

        processor = OCRProcessor()
        assert processor is not None
        assert processor._reader is None

    @pytest.mark.integration
    def test_processor_gpu_detection(self):
        """Test GPU detection"""
        from services.ocr_service.processor import OCRProcessor

        processor = OCRProcessor()
        gpu = processor._detect_gpu()
        assert isinstance(gpu, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
