import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

FONT_REGISTRATION_ATTEMPTED = False
USE_DEJAVU_FONTS = False


def _register_fonts():
    global FONT_REGISTRATION_ATTEMPTED, USE_DEJAVU_FONTS
    if FONT_REGISTRATION_ATTEMPTED:
        return
    FONT_REGISTRATION_ATTEMPTED = True

    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    ]

    for path in font_paths:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont("Helvetica", path))
                pdfmetrics.registerFont(TTFont("Helvetica-Bold", path.replace("Sans", "Sans-Bold")))
                USE_DEJAVU_FONTS = True
                logger.info(f"Registered DejaVu fonts from {path}")
                break
            except Exception as e:
                logger.warning(f"Failed to register DejaVu fonts: {e}")

    if not USE_DEJAVU_FONTS:
        logger.warning("DejaVu fonts not found, using Helvetica (Cyrillic may not display)")


logger = logging.getLogger(__name__)


class ReceiptGenerator:
    def __init__(self, output_dir: str = "/app/downloads/receipts"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        _register_fonts()

    def _font(self, bold=False):
        if USE_DEJAVU_FONTS:
            return "Helvetica-Bold" if bold else "Helvetica"
        return "Helvetica-Bold" if bold else "Helvetica"

    def generate_receipt_pdf(
        self,
        items: list[dict[str, Any]],
        output_path: str | None = None,
    ) -> str:
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"receipt_{uuid.uuid4().hex[:8]}_{timestamp}.pdf"
            output_path = str(self.output_dir / filename)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=15 * mm,
            leftMargin=15 * mm,
            topMargin=20 * mm,
            bottomMargin=20 * mm,
        )

        elements = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "Title",
            parent=styles["Heading1"],
            fontSize=18,
            alignment=1,
            spaceAfter=10,
        )
        elements.append(Paragraph("ТОВАРНЫЙ ЧЕК", title_style))
        elements.append(Spacer(1, 5 * mm))

        date_style = ParagraphStyle("Date", parent=styles["Normal"], fontSize=11, alignment=2)
        elements.append(Paragraph(datetime.now().strftime("%d.%m.%Y"), date_style))
        elements.append(Spacer(1, 15 * mm))

        table_data = [["№", "Наименование товара", "Кол-во", "Цена", "Сумма"]]

        total = 0.0
        for idx, item in enumerate(items, start=1):
            name = item.get("name", "Неизвестно")
            if len(name) > 40:
                name = name[:37] + "..."

            quantity = item.get("quantity", 1)
            price = item.get("price", 0.0)
            item_total = price * quantity
            total += item_total

            table_data.append(
                [
                    str(idx),
                    name,
                    str(quantity),
                    f"{price:.2f} BYN",
                    f"{item_total:.2f} BYN",
                ]
            )

        col_widths = [20 * mm, 85 * mm, 25 * mm, 30 * mm, 30 * mm]

        table = Table(table_data, colWidths=col_widths)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("ALIGN", (1, 1), (1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -1), 9),
                    ("TOPPADDING", (0, 1), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
                ]
            )
        )

        elements.append(table)
        elements.append(Spacer(1, 10 * mm))

        total_style = ParagraphStyle(
            "Total",
            parent=styles["Normal"],
            fontSize=14,
            alignment=2,
            fontName="Helvetica-Bold",
        )
        elements.append(Paragraph(f"ИТОГО: {total:.2f} BYN", total_style))

        doc.build(elements)
        logger.info(f"Receipt generated: {output_path}")

        return output_path

    def generate_receipt_with_unknown(
        self,
        items: list[dict[str, Any]],
        unknown_items: list[dict[str, Any]],
        output_path: str | None = None,
    ) -> str:
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"receipt_{uuid.uuid4().hex[:8]}_{timestamp}.pdf"
            output_path = str(self.output_dir / filename)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=15 * mm,
            leftMargin=15 * mm,
            topMargin=20 * mm,
            bottomMargin=20 * mm,
        )

        elements = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "Title",
            parent=styles["Heading1"],
            fontSize=18,
            alignment=1,
            spaceAfter=10,
        )
        elements.append(Paragraph("ТОВАРНЫЙ ЧЕК", title_style))
        elements.append(Spacer(1, 5 * mm))

        date_style = ParagraphStyle("Date", parent=styles["Normal"], fontSize=11, alignment=2)
        elements.append(Paragraph(datetime.now().strftime("%d.%m.%Y"), date_style))
        elements.append(Spacer(1, 15 * mm))

        table_data = [["№", "Наименование товара", "Кол-во", "Цена", "Сумма"]]

        total = 0.0
        idx = 1

        for item in items:
            name = item.get("name", "Неизвестно")
            if len(name) > 40:
                name = name[:37] + "..."

            quantity = item.get("quantity", 1)
            price = item.get("price", 0.0)
            item_total = price * quantity
            total += item_total

            table_data.append(
                [
                    str(idx),
                    name,
                    str(quantity),
                    f"{price:.2f} BYN",
                    f"{item_total:.2f} BYN",
                ]
            )
            idx += 1

        for item in unknown_items:
            name = item.get("name", "Неизвестно (введено вручную)")
            if len(name) > 40:
                name = name[:37] + "..."

            quantity = item.get("quantity", 1)
            price = item.get("price", 0.0)
            item_total = price * quantity
            total += item_total

            table_data.append(
                [
                    str(idx),
                    name,
                    str(quantity),
                    f"{price:.2f} BYN" if price > 0 else "-",
                    f"{item_total:.2f} BYN" if price > 0 else "-",
                ]
            )
            idx += 1

        col_widths = [20 * mm, 85 * mm, 25 * mm, 30 * mm, 30 * mm]

        table = Table(table_data, colWidths=col_widths)

        style_list = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("ALIGN", (1, 1), (1, -1), "LEFT"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("TOPPADDING", (0, 1), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
        ]

        if unknown_items:
            unknown_start = len(items) + 1
            style_list.append(("BACKGROUND", (0, unknown_start), (-1, -1), colors.lightyellow))

        table.setStyle(TableStyle(style_list))

        elements.append(table)
        elements.append(Spacer(1, 10 * mm))

        total_style = ParagraphStyle(
            "Total",
            parent=styles["Normal"],
            fontSize=14,
            alignment=2,
            fontName="Helvetica-Bold",
        )
        elements.append(Paragraph(f"ИТОГО: {total:.2f} BYN", total_style))

        doc.build(elements)
        logger.info(f"Receipt with unknown items generated: {output_path}")

        return output_path
