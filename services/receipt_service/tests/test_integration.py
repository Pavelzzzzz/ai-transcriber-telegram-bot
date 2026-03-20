import os
import sys
from datetime import datetime
from unittest.mock import patch

import pytest

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
)

from services.common.schemas import ResultMessage, TaskMessage, TaskStatus, TaskType


class TestReceiptTaskMessage:
    """Integration tests for receipt task message"""

    @pytest.mark.integration
    def test_receipt_task_message_creation(self):
        """Test creating receipt task message"""
        task = TaskMessage(
            task_id="receipt-test-123",
            task_type=TaskType.RECEIPT,
            user_id=12345,
            chat_id=67890,
            timestamp=datetime.now(),
            file_path="123456 x 2\n789012 x 1",
            metadata={
                "unknown_items": [
                    {"article": "123456", "name": "Test Item", "quantity": 1, "price": 100.0}
                ]
            },
        )

        assert task.task_type == TaskType.RECEIPT
        assert task.file_path == "123456 x 2\n789012 x 1"
        assert task.metadata["unknown_items"][0]["article"] == "123456"

    @pytest.mark.integration
    def test_receipt_task_message_to_json(self):
        """Test receipt task message serialization"""
        task = TaskMessage(
            task_id="receipt-test-456",
            task_type=TaskType.RECEIPT,
            user_id=12345,
            chat_id=67890,
            timestamp=datetime.now(),
            file_path="111222 x 1",
        )

        json_str = task.to_json()
        assert "receipt" in json_str
        assert "receipt-test-456" in json_str

    @pytest.mark.integration
    def test_receipt_task_message_from_json(self):
        """Test receipt task message deserialization"""
        json_str = '{"task_id":"receipt-test-789","task_type":"receipt","user_id":999,"chat_id":888,"timestamp":"2024-01-01T12:00:00","file_path":"333444 x 3","metadata":{}}'

        task = TaskMessage.from_json(json_str)

        assert task.task_id == "receipt-test-789"
        assert task.task_type == TaskType.RECEIPT
        assert task.user_id == 999
        assert task.file_path == "333444 x 3"


class TestReceiptResultMessage:
    """Integration tests for receipt result message"""

    @pytest.mark.integration
    def test_receipt_result_message_success(self):
        """Test creating successful receipt result"""
        result = ResultMessage(
            task_id="receipt-result-123",
            status=TaskStatus.SUCCESS,
            result_type="receipt",
            result_data={
                "file_path": "/tmp/receipt_123.pdf",
                "items_count": 3,
                "missing_count": 1,
                "missing_articles": ["999888"],
                "total": 1500.50,
            },
        )

        assert result.status == TaskStatus.SUCCESS
        assert result.result_type == "receipt"
        assert result.result_data["items_count"] == 3
        assert result.result_data["total"] == 1500.50

    @pytest.mark.integration
    def test_receipt_result_message_failure(self):
        """Test creating failed receipt result"""
        result = ResultMessage(
            task_id="receipt-result-456",
            status=TaskStatus.FAILED,
            result_type="receipt",
            result_data={},
            error="WB API unavailable",
        )

        assert result.status == TaskStatus.FAILED
        assert result.error == "WB API unavailable"


class TestTaskTypeEnum:
    """Test TaskType enum includes RECEIPT"""

    @pytest.mark.integration
    def test_task_type_receipt_exists(self):
        assert TaskType.RECEIPT.value == "receipt"

    @pytest.mark.integration
    def test_task_type_members(self):
        task_types = list(TaskType)
        assert TaskType.RECEIPT in task_types
        assert len(task_types) >= 4


class TestReceiptProcessorIntegration:
    """Integration tests for receipt processor"""

    @pytest.mark.integration
    def test_processor_init(self, tmp_path):
        from services.receipt_service.processor import ReceiptProcessor

        processor = ReceiptProcessor(output_dir=str(tmp_path))
        assert processor is not None
        assert processor.wb_client is not None
        assert processor.generator is not None

    @pytest.mark.integration
    def test_processor_validate_items_text_valid(self, tmp_path):
        from services.receipt_service.processor import ReceiptProcessor

        processor = ReceiptProcessor(output_dir=str(tmp_path))

        result = processor.validate_items_text_sync("123456 x 2\n789012 x 1")
        assert result["valid"] is True
        assert result["count"] == 2

    @pytest.mark.integration
    def test_processor_validate_items_text_invalid(self, tmp_path):
        from services.receipt_service.processor import ReceiptProcessor

        processor = ReceiptProcessor(output_dir=str(tmp_path))

        result = processor.validate_items_text_sync("invalid text")
        assert result["valid"] is False
        assert result["count"] == 0

    @pytest.mark.integration
    def test_processor_validate_items_text_empty(self, tmp_path):
        from services.receipt_service.processor import ReceiptProcessor

        processor = ReceiptProcessor(output_dir=str(tmp_path))

        result = processor.validate_items_text_sync("")
        assert result["valid"] is False


class TestWBClientIntegration:
    """Integration tests for Wildberries client"""

    @pytest.mark.integration
    def test_wb_client_init(self):
        from services.receipt_service.wb_client import WBClient

        client = WBClient()
        assert client is not None

    @pytest.mark.integration
    def test_extract_article_from_url(self):
        from services.receipt_service.wb_client import WBClient

        client = WBClient()

        article = client.extract_article_from_url(
            "https://www.wildberries.ru/catalog/12345678/detail.aspx"
        )
        assert article == "12345678"

    @pytest.mark.integration
    def test_extract_article_from_short_url(self):
        from services.receipt_service.wb_client import WBClient

        client = WBClient()

        article = client.extract_article_from_url("https://wb.ru/catalog/87654321")
        assert article == "87654321"


class TestParseItemsInputIntegration:
    """Integration tests for items input parsing"""

    @pytest.mark.integration
    def test_parse_single_article(self):
        from services.receipt_service.wb_client import parse_items_input

        result = parse_items_input("123456 x 1")
        assert len(result) == 1
        assert result[0]["article"] == "123456"
        assert result[0]["quantity"] == 1

    @pytest.mark.integration
    def test_parse_multiple_items(self):
        from services.receipt_service.wb_client import parse_items_input

        result = parse_items_input("123456 x 2\n789012 x 3")
        assert len(result) == 2
        assert result[0]["article"] == "123456"
        assert result[0]["quantity"] == 2
        assert result[1]["article"] == "789012"
        assert result[1]["quantity"] == 3

    @pytest.mark.integration
    def test_parse_with_spaces(self):
        from services.receipt_service.wb_client import parse_items_input

        result = parse_items_input("  123456  x  2  ")
        assert len(result) == 1
        assert result[0]["article"] == "123456"
        assert result[0]["quantity"] == 2

    @pytest.mark.integration
    def test_parse_empty_text(self):
        from services.receipt_service.wb_client import parse_items_input

        result = parse_items_input("")
        assert len(result) == 0

    @pytest.mark.integration
    def test_parse_with_cyrillic_x(self):
        from services.receipt_service.wb_client import parse_items_input

        result = parse_items_input("123456 х 2")
        assert len(result) == 1
        assert result[0]["quantity"] == 2


class TestReceiptGeneratorIntegration:
    """Integration tests for receipt generator"""

    @pytest.mark.integration
    def test_generator_init(self, tmp_path):
        from services.receipt_service.receipt_generator import ReceiptGenerator

        generator = ReceiptGenerator(output_dir=str(tmp_path))
        assert generator is not None

    @pytest.mark.integration
    def test_generate_receipt_pdf_with_items(self, tmp_path):
        from services.receipt_service.receipt_generator import ReceiptGenerator

        generator = ReceiptGenerator(output_dir=str(tmp_path))
        items = [
            {
                "article": "123456",
                "name": "Test Item 1",
                "brand": "Brand1",
                "price": 100.0,
                "quantity": 2,
            },
            {
                "article": "789012",
                "name": "Test Item 2",
                "brand": "Brand2",
                "price": 200.0,
                "quantity": 1,
            },
        ]

        pdf_path = generator.generate_receipt_pdf(items)

        assert pdf_path is not None
        assert os.path.exists(pdf_path)
        assert pdf_path.endswith(".pdf")

        os.remove(pdf_path)

    @pytest.mark.integration
    def test_generate_receipt_pdf_empty_items(self, tmp_path):
        from services.receipt_service.receipt_generator import ReceiptGenerator

        generator = ReceiptGenerator(output_dir=str(tmp_path))
        items = []

        pdf_path = generator.generate_receipt_pdf(items)

        assert pdf_path is not None
        assert os.path.exists(pdf_path)

        os.remove(pdf_path)


class TestReceiptCreationFlow:
    """Integration tests for complete receipt creation flow"""

    @pytest.mark.integration
    def test_full_receipt_creation_flow(self, tmp_path):
        from services.receipt_service.processor import ReceiptProcessor

        processor = ReceiptProcessor(output_dir=str(tmp_path))

        items_text = "123456 x 2\n789012 x 1"
        result = processor.validate_items_text_sync(items_text)

        assert result["valid"] is True
        assert result["count"] == 2
        assert "items" in result
        assert result["items"][0]["article"] == "123456"
        assert result["items"][0]["quantity"] == 2

    @pytest.mark.integration
    def test_receipt_creation_with_invalid_items(self, tmp_path):
        from services.receipt_service.processor import ReceiptProcessor

        processor = ReceiptProcessor(output_dir=str(tmp_path))

        result = processor.validate_items_text_sync("invalid text")

        assert result["valid"] is False
        assert result["count"] == 0

    @pytest.mark.integration
    def test_receipt_pdf_generation_with_items(self, tmp_path):
        from services.receipt_service.processor import ReceiptProcessor

        processor = ReceiptProcessor(output_dir=str(tmp_path))

        items = [
            {
                "article": "123456",
                "name": "Test Product 1",
                "brand": "Brand1",
                "price": 150.0,
                "quantity": 2,
            },
            {
                "article": "654321",
                "name": "Test Product 2",
                "brand": "Brand2",
                "price": 250.0,
                "quantity": 1,
            },
        ]

        pdf_path = processor.generator.generate_receipt_pdf(items)

        assert pdf_path is not None
        assert os.path.exists(pdf_path)
        assert pdf_path.endswith(".pdf")

        file_size = os.path.getsize(pdf_path)
        assert file_size > 0

        os.remove(pdf_path)

    @pytest.mark.integration
    def test_receipt_pdf_with_unknown_items(self, tmp_path):
        from services.receipt_service.processor import ReceiptProcessor

        processor = ReceiptProcessor(output_dir=str(tmp_path))

        items = [
            {
                "article": "123456",
                "name": "Known Product",
                "brand": "Brand",
                "price": 100.0,
                "quantity": 1,
            },
        ]
        unknown_items = [
            {"article": "999999", "name": "Unknown Product", "quantity": 1, "price": 50.0},
        ]

        pdf_path = processor.generator.generate_receipt_with_unknown(items, unknown_items)

        assert pdf_path is not None
        assert os.path.exists(pdf_path)
        assert pdf_path.endswith(".pdf")

        os.remove(pdf_path)

    @pytest.mark.integration
    def test_receipt_validation_valid_input(self, tmp_path):
        from services.receipt_service.processor import ReceiptProcessor

        processor = ReceiptProcessor(output_dir=str(tmp_path))

        result = processor.validate_items_text_sync("123456 x 2\n789012 x 3")

        assert result["valid"] is True
        assert result["count"] == 2
        assert "items" in result

    @pytest.mark.integration
    def test_receipt_validation_empty_input(self, tmp_path):
        from services.receipt_service.processor import ReceiptProcessor

        processor = ReceiptProcessor(output_dir=str(tmp_path))

        result = processor.validate_items_text_sync("")

        assert result["valid"] is False
        assert result["count"] == 0

    @pytest.mark.integration
    def test_receipt_total_calculation(self, tmp_path):
        from services.receipt_service.receipt_generator import ReceiptGenerator

        generator = ReceiptGenerator(output_dir=str(tmp_path))

        items = [
            {"article": "111", "name": "Product 1", "price": 100.0, "quantity": 2},
            {"article": "222", "name": "Product 2", "price": 50.0, "quantity": 3},
        ]

        pdf_path = generator.generate_receipt_pdf(items)

        assert pdf_path is not None
        assert os.path.exists(pdf_path)

        os.remove(pdf_path)


class TestKafkaConsumerIntegration:
    """Integration tests for Kafka consumer"""

    @pytest.mark.integration
    def test_consumer_init(self, tmp_path):
        from services.receipt_service.kafka_consumer import ReceiptKafkaConsumer
        from services.receipt_service.processor import ReceiptProcessor

        class MockConfig:
            topics = {"tasks_receipt": "tasks_receipt"}
            bootstrap_servers = ["localhost:9092"]
            client_id = "test"

        processor = ReceiptProcessor(output_dir=str(tmp_path))
        consumer = ReceiptKafkaConsumer(MockConfig(), processor=processor)

        assert consumer is not None
        assert consumer.config is not None
        assert consumer.processor is not None

    @pytest.mark.integration
    def test_consumer_task_queue_init(self, tmp_path):
        from services.receipt_service.kafka_consumer import ReceiptKafkaConsumer
        from services.receipt_service.processor import ReceiptProcessor

        class MockConfig:
            topics = {"tasks_receipt": "tasks_receipt"}
            bootstrap_servers = ["localhost:9092"]
            client_id = "test"

        processor = ReceiptProcessor(output_dir=str(tmp_path))
        consumer = ReceiptKafkaConsumer(MockConfig(), processor=processor)

        assert consumer._task_queue is not None
        assert consumer._pending_tasks == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
