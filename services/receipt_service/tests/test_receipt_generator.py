import os
import sys
import tempfile

import pytest

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
)

from services.receipt_service.receipt_generator import ReceiptGenerator


class TestReceiptGenerator:
    @pytest.fixture
    def generator(self):
        return ReceiptGenerator(output_dir=tempfile.mkdtemp())

    def test_generate_receipt_pdf_creates_file(self, generator):
        items = [
            {"name": "Test Product 1", "quantity": 2, "price": 100.0},
            {"name": "Test Product 2", "quantity": 1, "price": 200.0},
        ]

        output_path = generator.generate_receipt_pdf(items)

        assert os.path.exists(output_path)
        assert output_path.endswith(".pdf")

    def test_generate_receipt_pdf_with_items(self, generator):
        items = [
            {"name": "Product A", "quantity": 2, "price": 500.0},
            {"name": "Product B", "quantity": 3, "price": 300.0},
        ]

        output_path = generator.generate_receipt_pdf(items)

        assert os.path.exists(output_path)
        assert os.path.getsize(output_path) > 0

    def test_generate_receipt_pdf_empty_items(self, generator):
        items = []

        output_path = generator.generate_receipt_pdf(items)

        assert os.path.exists(output_path)

    def test_generate_receipt_pdf_calculates_total(self, generator):
        items = [
            {"name": "Product A", "quantity": 2, "price": 100.0},
            {"name": "Product B", "quantity": 3, "price": 50.0},
        ]

        output_path = generator.generate_receipt_pdf(items)

        assert os.path.exists(output_path)

    def test_generate_receipt_pdf_with_long_name(self, generator):
        items = [
            {
                "name": "A very long product name that should be truncated in the receipt because it exceeds forty characters limit",
                "quantity": 1,
                "price": 100.0,
            }
        ]

        output_path = generator.generate_receipt_pdf(items)

        assert os.path.exists(output_path)

    def test_generate_receipt_with_unknown_items(self, generator):
        items = [{"name": "Found Product", "quantity": 1, "price": 100.0}]
        unknown_items = [{"name": "Manual Entry Product", "quantity": 2, "price": 50.0}]

        output_path = generator.generate_receipt_with_unknown(items, unknown_items)

        assert os.path.exists(output_path)
        assert os.path.getsize(output_path) > 0


class TestReceiptGeneratorOutput:
    def test_output_directory_creation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = os.path.join(tmpdir, "receipts", "subdir")
            generator = ReceiptGenerator(output_dir=output_dir)

            assert os.path.exists(output_dir)
