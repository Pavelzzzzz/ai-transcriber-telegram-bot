import os
import sys
from unittest.mock import Mock, patch

import pytest

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
)

from services.receipt_service.wb_client import (
    WBClient,
    extract_article_from_url_static,
    parse_items_input,
)


class TestWBClientParsing:
    def test_extract_article_from_url_wildberries_ru(self):
        url = "https://www.wildberries.ru/catalog/178601980/detail.aspx"
        article = WBClient().extract_article_from_url(url)
        assert article == "178601980"

    def test_extract_article_from_url_with_path(self):
        url = "https://wildberries.ru/catalog/12345678/product.aspx"
        article = WBClient().extract_article_from_url(url)
        assert article == "12345678"

    def test_extract_article_from_url_invalid(self):
        url = "https://example.com/product/123"
        article = WBClient().extract_article_from_url(url)
        assert article is None

    def test_extract_article_from_url_static(self):
        url = "https://www.wildberries.ru/catalog/999999/detail.aspx"
        article = extract_article_from_url_static(url)
        assert article == "999999"


class TestParseItemsInput:
    def test_parse_single_article(self):
        text = "178601980 x 2"
        items = parse_items_input(text)
        assert len(items) == 1
        assert items[0]["article"] == "178601980"
        assert items[0]["quantity"] == 2

    def test_parse_multiple_items(self):
        text = """178601980 x 2
12345678 x 1
99999999 x 3"""
        items = parse_items_input(text)
        assert len(items) == 3
        assert items[0]["article"] == "178601980"
        assert items[1]["article"] == "12345678"
        assert items[2]["article"] == "99999999"

    def test_parse_url(self):
        text = "https://wildberries.ru/catalog/12345678/detail.aspx x 1"
        items = parse_items_input(text)
        assert len(items) == 1
        assert items[0]["article"] == "12345678"
        assert items[0]["quantity"] == 1

    def test_parse_with_uppercase_x(self):
        text = "178601980 X 2"
        items = parse_items_input(text)
        assert len(items) == 1
        assert items[0]["quantity"] == 2

    def test_parse_with_cyrillic_x(self):
        text = "178601980 х 2"
        items = parse_items_input(text)
        assert len(items) == 1
        assert items[0]["quantity"] == 2

    def test_parse_empty_text(self):
        items = parse_items_input("")
        assert len(items) == 0

    def test_parse_invalid_format(self):
        text = "not a valid format"
        items = parse_items_input(text)
        assert len(items) == 0

    def test_parse_zero_quantity(self):
        text = "178601980 x 0"
        items = parse_items_input(text)
        assert len(items) == 0

    def test_parse_negative_quantity(self):
        text = "178601980 x -1"
        items = parse_items_input(text)
        assert len(items) == 0

    def test_parse_with_spaces(self):
        text = "  178601980  x  2  "
        items = parse_items_input(text)
        assert len(items) == 1
        assert items[0]["article"] == "178601980"


class TestWBClientGetProductInfo:
    @patch("services.receipt_service.wb_client.requests.Session.get")
    def test_get_product_info_success(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {
                "products": [
                    {
                        "name": "Test Product",
                        "brand": "TestBrand",
                        "priceU": 99900,
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        client = WBClient()
        result = client.get_product_info("178601980")

        assert result["article"] == "178601980"
        assert result["name"] == "Test Product"
        assert result["brand"] == "TestBrand"
        assert result["price"] == 999.0
        assert result["error"] is None

    @patch("services.receipt_service.wb_client.requests.Session.get")
    def test_get_product_info_not_found(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {"data": {"products": []}}
        mock_get.return_value = mock_response

        client = WBClient()
        result = client.get_product_info("99999999")

        assert result["article"] == "99999999"
        assert result["error"] == "not_found"


class TestWBClientBatch:
    @patch("services.receipt_service.wb_client.requests.Session.get")
    def test_get_products_batch_parallel(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {
                "products": [
                    {
                        "name": "Test Product",
                        "brand": "TestBrand",
                        "priceU": 50000,
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        client = WBClient()
        articles = ["12345678", "87654321", "11111111"]
        results = client.get_products_batch(articles)

        assert len(results) == 3
        for article in articles:
            assert article in results
            assert results[article]["error"] is None
