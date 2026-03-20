import logging
from typing import Any

from .receipt_generator import ReceiptGenerator
from .wb_client import WBClient, parse_items_input

logger = logging.getLogger(__name__)


class ReceiptProcessor:
    def __init__(self, output_dir: str | None = None):
        self.wb_client = WBClient()
        self.generator = (
            ReceiptGenerator(output_dir=output_dir) if output_dir else ReceiptGenerator()
        )

    async def process_receipt(self, items_text: str, user_id: int) -> dict[str, Any]:
        parsed_items = parse_items_input(items_text)

        if not parsed_items:
            return {
                "status": "error",
                "error": "no_valid_items",
                "message": "Не удалось распознать товары. Используйте формат: артикул x количество",
            }

        articles = [item["article"] for item in parsed_items]
        quantities = {item["article"]: item["quantity"] for item in parsed_items}

        logger.info(f"Processing receipt for user {user_id}: {len(articles)} items")

        product_results = self.wb_client.get_products_batch(articles)

        found_items: list[dict[str, Any]] = []
        missing_articles: list[str] = []

        for article, result in product_results.items():
            if result.get("error"):
                missing_articles.append(article)
            else:
                found_items.append(
                    {
                        "article": article,
                        "name": result.get("name", "Неизвестно"),
                        "brand": result.get("brand", ""),
                        "price": result.get("price", 0.0),
                        "quantity": quantities.get(article, 1),
                    }
                )

        if missing_articles:
            logger.warning(f"Missing articles for user {user_id}: {missing_articles}")

        total = sum(item["price"] * item["quantity"] for item in found_items)

        return {
            "status": "success",
            "items": found_items,
            "missing_articles": missing_articles,
            "total": total,
            "items_count": len(found_items),
            "missing_count": len(missing_articles),
        }

    async def generate_receipt_pdf(
        self,
        items: list[dict[str, Any]],
        unknown_items: list[dict[str, Any]] | None = None,
    ) -> str:
        if unknown_items:
            return self.generator.generate_receipt_with_unknown(items, unknown_items)
        return self.generator.generate_receipt_pdf(items)

    def validate_items_text_sync(self, text: str) -> dict[str, Any]:
        parsed = parse_items_input(text)

        if not parsed:
            return {
                "valid": False,
                "message": "Не удалось распознать товары. Используйте формат: артикул x количество",
                "count": 0,
            }

        return {
            "valid": True,
            "message": f"Распознано {len(parsed)} товаров",
            "count": len(parsed),
            "items": parsed,
        }

    async def validate_items_text(self, text: str) -> dict[str, Any]:
        return self.validate_items_text_sync(text)
