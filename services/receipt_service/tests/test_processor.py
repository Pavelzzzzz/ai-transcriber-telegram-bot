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
            mock_gen.generate_receipt_pdf = AsyncMock(return_value="/tmp/receipt.pdf")
            mock_gen.generate_receipt_with_unknown = AsyncMock(return_value="/tmp/receipt.pdf")
            MockGenerator.return_value = mock_gen
            return ReceiptProcessor()

    def test_init(self, processor):
        assert processor is not None
        assert processor.wb_client is not None
        assert processor.generator is not None

    @pytest.mark.asyncio
    async def test_validate_items_text_valid(self, processor):
        text = "178601980 x 2\n12345678 x 1"
        result = await processor.validate_items_text(text)

        assert result["valid"] is True
        assert result["count"] == 2

    @pytest.mark.asyncio
    async def test_validate_items_text_invalid(self, processor):
        text = "not valid format"
        result = await processor.validate_items_text(text)

        assert result["valid"] is False
        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_validate_items_text_empty(self, processor):
        result = await processor.validate_items_text("")

        assert result["valid"] is False
        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_process_receipt_success(self):
        mock_wb_client = Mock()
        mock_wb_client.get_products_batch.return_value = {
            "178601980": {
                "article": "178601980",
                "name": "Test Product",
                "brand": "TestBrand",
                "price": 999.0,
                "error": None,
            }
        }

        with patch("services.receipt_service.processor.ReceiptGenerator") as MockGen:
            mock_gen = Mock()
            mock_gen.generate_receipt_pdf = AsyncMock(return_value="/tmp/receipt.pdf")
            mock_gen.generate_receipt_with_unknown = AsyncMock(return_value="/tmp/receipt.pdf")
            MockGen.return_value = mock_gen

            processor = ReceiptProcessor()
            processor.wb_client = mock_wb_client

            result = await processor.process_receipt("178601980 x 2", user_id=12345)

        assert result["status"] == "success"
        assert result["items_count"] == 1
        assert result["missing_count"] == 0
        assert len(result["items"]) == 1
        assert result["items"][0]["name"] == "Test Product"

    @pytest.mark.asyncio
    async def test_process_receipt_with_missing_products(self):
        mock_wb_client = Mock()
        mock_wb_client.get_products_batch.return_value = {
            "178601980": {
                "article": "178601980",
                "name": "Test Product",
                "brand": "TestBrand",
                "price": 999.0,
                "error": None,
            },
            "99999999": {"article": "99999999", "error": "not_found"},
        }

        with patch("services.receipt_service.processor.ReceiptGenerator") as MockGen:
            mock_gen = Mock()
            mock_gen.generate_receipt_pdf = AsyncMock(return_value="/tmp/receipt.pdf")
            mock_gen.generate_receipt_with_unknown = AsyncMock(return_value="/tmp/receipt.pdf")
            MockGen.return_value = mock_gen

            processor = ReceiptProcessor()
            processor.wb_client = mock_wb_client

            result = await processor.process_receipt("178601980 x 2\n99999999 x 1", user_id=12345)

        assert result["status"] == "success"
        assert result["items_count"] == 1
        assert result["missing_count"] == 1
        assert "99999999" in result["missing_articles"]

    @pytest.mark.asyncio
    async def test_process_receipt_no_valid_items(self, processor):
        result = await processor.process_receipt("invalid format", user_id=12345)

        assert result["status"] == "error"
        assert result["error"] == "no_valid_items"


class TestReceiptProcessorValidation:
    @pytest.fixture
    def processor(self):
        with patch("services.receipt_service.processor.ReceiptGenerator") as MockGenerator:
            mock_gen = Mock()
            mock_gen.generate_receipt_pdf = AsyncMock(return_value="/tmp/receipt.pdf")
            mock_gen.generate_receipt_with_unknown = AsyncMock(return_value="/tmp/receipt.pdf")
            MockGenerator.return_value = mock_gen
            return ReceiptProcessor()

    @pytest.mark.asyncio
    async def test_validate_url_format(self, processor):
        text = "https://wildberries.ru/catalog/12345678/detail.aspx x 1"
        result = await processor.validate_items_text(text)

        assert result["valid"] is True
        assert result["count"] == 1
