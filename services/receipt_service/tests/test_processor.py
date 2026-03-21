import json
import os
import sys
from unittest.mock import AsyncMock, Mock, patch

import pytest

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
)

from services.receipt_service.processor import ReceiptProcessor


class TestReceiptProcessor:
    @pytest.fixture
    def processor(self):
        with patch("services.receipt_service.processor.ReceiptGenerator") as MockGenerator:
            mock_gen = Mock()
            mock_gen.generate_receipt_pdf = Mock(return_value="/tmp/receipt.pdf")
            MockGenerator.return_value = mock_gen
            return ReceiptProcessor()

    def test_init(self, processor):
        assert processor is not None
        assert processor.generator is not None

    def test_process_receipt_sync_with_json_items(self, processor):
        items_json = json.dumps(
            [
                {"article": "123456", "name": "Товар 1", "price": 100.50, "quantity": 2},
                {"article": "654321", "name": "Товар 2", "price": 200.00, "quantity": 1},
            ]
        )

        result = processor.process_receipt_sync(items_json, user_id=12345)

        assert result["status"] == "success"
        assert result["items_count"] == 2
        assert result["missing_count"] == 0
        assert result["total"] == pytest.approx(401.00)
        assert len(result["items"]) == 2

    def test_process_receipt_sync_calculates_total_correctly(self, processor):
        items_json = json.dumps(
            [
                {"article": "111", "name": "Товар A", "price": 10.00, "quantity": 3},
                {"article": "222", "name": "Товар B", "price": 25.50, "quantity": 2},
                {"article": "333", "name": "Товар C", "price": 5.00, "quantity": 1},
            ]
        )

        result = processor.process_receipt_sync(items_json, user_id=1)

        assert result["total"] == pytest.approx(86.00)

    def test_process_receipt_sync_with_zero_price(self, processor):
        items_json = json.dumps(
            [
                {"article": "123", "name": "Товар", "price": 0, "quantity": 5},
            ]
        )

        result = processor.process_receipt_sync(items_json, user_id=1)

        assert result["status"] == "success"
        assert result["total"] == 0

    def test_process_receipt_sync_with_missing_price(self, processor):
        items_json = json.dumps(
            [
                {"article": "123", "name": "Товар", "quantity": 2},
            ]
        )

        result = processor.process_receipt_sync(items_json, user_id=1)

        assert result["status"] == "success"
        assert result["total"] == 0

    def test_process_receipt_sync_with_invalid_json(self, processor):
        result = processor.process_receipt_sync("not valid json", user_id=1)

        assert result["status"] == "error"
        assert result["error"] == "invalid_format"

    def test_process_receipt_sync_with_empty_json_array(self, processor):
        result = processor.process_receipt_sync("[]", user_id=1)

        assert result["status"] == "error"
        assert result["error"] == "invalid_format"

    def test_process_receipt_sync_with_non_list_json(self, processor):
        result = processor.process_receipt_sync('{"article": "123"}', user_id=1)

        assert result["status"] == "error"
        assert result["error"] == "invalid_format"

    def test_process_receipt_sync_single_item(self, processor):
        items_json = json.dumps(
            [
                {"article": "999", "name": "Один товар", "price": 150.75, "quantity": 1},
            ]
        )

        result = processor.process_receipt_sync(items_json, user_id=42)

        assert result["status"] == "success"
        assert result["items_count"] == 1
        assert result["total"] == 150.75
        assert result["items"][0]["article"] == "999"

    def test_process_receipt_sync_large_quantity(self, processor):
        items_json = json.dumps(
            [
                {"article": "123", "name": "Товар", "price": 10.00, "quantity": 100},
            ]
        )

        result = processor.process_receipt_sync(items_json, user_id=1)

        assert result["total"] == 1000.00


class TestReceiptProcessorAsync:
    @pytest.fixture
    def processor(self):
        with patch("services.receipt_service.processor.ReceiptGenerator") as MockGenerator:
            mock_gen = Mock()
            mock_gen.generate_receipt_pdf = Mock(return_value="/tmp/receipt.pdf")
            MockGenerator.return_value = mock_gen
            return ReceiptProcessor()

    @pytest.mark.asyncio
    async def test_process_receipt_async(self, processor):
        items_json = json.dumps(
            [
                {"article": "123", "name": "Товар", "price": 100, "quantity": 1},
            ]
        )

        result = await processor.process_receipt(items_json, user_id=1)

        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_generate_receipt_pdf_async(self, processor):
        items = [{"article": "123", "name": "Товар", "price": 100, "quantity": 1}]

        result = await processor.generate_receipt_pdf(items)

        assert result == "/tmp/receipt.pdf"
        processor.generator.generate_receipt_pdf.assert_called_once_with(items)


class TestReceiptProcessorTotalCalculation:
    @pytest.fixture
    def processor(self):
        with patch("services.receipt_service.processor.ReceiptGenerator") as MockGenerator:
            mock_gen = Mock()
            mock_gen.generate_receipt_pdf = Mock(return_value="/tmp/receipt.pdf")
            MockGenerator.return_value = mock_gen
            return ReceiptProcessor()

    def test_total_with_multiple_items_same_article(self, processor):
        items_json = json.dumps(
            [
                {"article": "123", "name": "Товар", "price": 50.00, "quantity": 3},
            ]
        )

        result = processor.process_receipt_sync(items_json, user_id=1)

        assert result["total"] == 150.00

    def test_total_precision(self, processor):
        items_json = json.dumps(
            [
                {"article": "1", "name": "A", "price": 33.33, "quantity": 3},
                {"article": "2", "name": "B", "price": 33.33, "quantity": 3},
                {"article": "3", "name": "C", "price": 33.34, "quantity": 3},
            ]
        )

        result = processor.process_receipt_sync(items_json, user_id=1)

        assert result["total"] == pytest.approx(300.00)
