import json
import logging
from typing import Any

from .receipt_generator import ReceiptGenerator

logger = logging.getLogger(__name__)


class ReceiptProcessor:
    def __init__(self, output_dir: str | None = None):
        self.generator = (
            ReceiptGenerator(output_dir=output_dir) if output_dir else ReceiptGenerator()
        )

    def process_receipt_sync(self, items_text: str, user_id: int) -> dict[str, Any]:
        try:
            items = json.loads(items_text)
            if isinstance(items, list) and len(items) > 0:
                logger.info(f"Processing receipt for user {user_id}: {len(items)} items")

                total = sum(item.get("price", 0) * item.get("quantity", 1) for item in items)

                return {
                    "status": "success",
                    "items": items,
                    "total": total,
                    "items_count": len(items),
                    "missing_count": 0,
                }
        except json.JSONDecodeError:
            pass

        return {
            "status": "error",
            "error": "invalid_format",
            "message": "Неверный формат данных",
        }

    async def process_receipt(self, items_text: str, user_id: int) -> dict[str, Any]:
        return self.process_receipt_sync(items_text, user_id)

    def generate_receipt_pdf_sync(
        self,
        items: list[dict[str, Any]],
        unknown_items: list[dict[str, Any]] | None = None,
        user_id: int | None = None,
        company: str | None = None,
    ) -> str:
        final_company = company
        logger.info(f"Generating receipt with company from metadata: '{final_company}'")

        if unknown_items:
            return self.generator.generate_receipt_with_unknown(
                items, unknown_items, company=final_company
            )
        return self.generator.generate_receipt_pdf(items, company=final_company)

    async def generate_receipt_pdf(
        self,
        items: list[dict[str, Any]],
        unknown_items: list[dict[str, Any]] | None = None,
        user_id: int | None = None,
        company: str | None = None,
    ) -> str:
        return self.generate_receipt_pdf_sync(items, unknown_items, user_id, company)
