"""Common utilities for formatting and display."""

from typing import Any


def format_receipt_table(items: list[dict[str, Any]], total: float) -> str:
    """Format receipt items as ASCII table.

    Args:
        items: List of item dicts with 'article', 'name', 'quantity', 'price' keys
        total: Total sum of all items

    Returns:
        Formatted ASCII table string
    """
    text = "👁️ <b>Предпросмотр чека</b>\n\n"
    text += "┌────────────────────────────────────────────────────────┐\n"
    text += "│  № │ Артикул     │ Наименование            │ Кол │ Цена      │ Сумма    │\n"
    text += "├────┼─────────────┼────────────────────────┼─────┼───────────┼──────────┤\n"

    if not items:
        text += "│ (нет товаров)                                          │\n"

    for idx, item in enumerate(items, start=1):
        article = item.get("article", "-")
        name = item.get("name", f"Артикул {article}")[:22]
        quantity = item.get("quantity", 1)
        price = item.get("price", 0)
        item_sum = price * quantity

        price_str = f"{price:.2f}" if price > 0 else "-"
        sum_str = f"{item_sum:.2f}" if price > 0 else "-"

        text += f"│ {idx:2}. │ {article[:11]:11} │ {name:<22} │ {quantity:<4} │ {price_str:<9} │ {sum_str:<8} │\n"

    total_str = f"{total:.2f}"
    text += "├────┴─────────────┴────────────────────────┴─────┴───────────┴──────────┤\n"
    text += f"│ ИТОГО:                                              │ {total_str:<8} │\n"
    text += "└────────────────────────────────────────────────────────┘"

    return text


def calculate_receipt_total(items: list[dict[str, Any]]) -> tuple[float, float]:
    """Calculate total and item sums for receipt.

    Args:
        items: List of item dicts with 'quantity' and 'price' keys

    Returns:
        Tuple of (item_sums_list, total)
    """
    total = 0.0
    item_sums = []

    for item in items:
        price = item.get("price", 0)
        quantity = item.get("quantity", 1)
        item_sum = price * quantity
        item_sums.append(item_sum)
        total += item_sum

    return item_sums, total
