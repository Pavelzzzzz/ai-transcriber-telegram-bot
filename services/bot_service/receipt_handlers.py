import logging
import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from services.common.user_settings_repo import (
    create_receipt_history,
    delete_receipt_history,
    get_or_create_user_settings,
    get_receipt_by_id,
    get_user_receipt_history,
    update_receipt_history,
    update_user_settings,
)

logger = logging.getLogger(__name__)


def parse_items_input(text: str) -> list[dict[str, str | int | float]]:
    items: list[dict[str, str | int | float]] = []
    article_pattern = re.compile(r"^(.+?)\s*[xXхХ]\s*(\d+)(?:\s*[xXхХ]\s*(\d+(?:[.,]\d+)?))?$")

    for line in text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue

        match = article_pattern.match(line)
        if not match:
            continue

        raw = match.group(1).strip()
        quantity = int(match.group(2))
        price_str = match.group(3)
        price = float(price_str.replace(",", ".")) if price_str else 0.0

        if quantity <= 0:
            continue

        if "wildberries" in raw.lower():
            article = extract_article_from_url_static(raw)
        else:
            article = raw

        if article and article.isdigit():
            items.append({"article": article, "quantity": quantity, "price": price})

    return items


def extract_article_from_url_static(url: str) -> str | None:
    match = re.search(r"/catalog/(\d+)", url)
    if match:
        return match.group(1)
    return None


def get_wb_product_info_from_article(article: str) -> dict | None:
    """Get product name and price from wildberries.by by article number.

    Args:
        article: Product article number (e.g., '178601980')

    Returns:
        Dict with 'name' and 'price' keys, or None if not found
    """
    try:
        from playwright.sync_api import sync_playwright

        wb_url = f"https://www.wildberries.by/catalog/{article}/detail.aspx"

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = context.new_page()
            page.goto(wb_url, wait_until="load", timeout=15000)
            page.wait_for_timeout(2000)

            product_name = None
            product_price = 0.0

            name_selectors = [
                "h1.product-page__product-name",
                ".product-page__title",
                "[data-link='product-name']",
                "h1",
                ".product-title",
            ]

            for selector in name_selectors:
                try:
                    element = page.locator(selector).first
                    if element.count() > 0:
                        product_name = element.inner_text().strip()
                        if product_name:
                            break
                except Exception:
                    continue

            if not product_name:
                title = page.title()
                if title and "Wildberries" in title:
                    product_name = title.split(" купить")[0].strip()
                    if article and product_name.endswith(article):
                        product_name = product_name[: -len(article) - 1].strip()

            price_selectors = [
                "[class*='price']",
                ".product-price",
                ".price-block",
                "[data-widget='webPrice']",
            ]

            for selector in price_selectors:
                try:
                    element = page.locator(selector).first
                    if element.count() > 0:
                        price_text = element.inner_text().strip()
                        import re

                        price_match = re.search(
                            r"([\d\s]+[,.]\d+)\s*руб",
                            price_text.replace(" ", "").replace("\xa0", ""),
                        )
                        if price_match:
                            price_str = price_match.group(1).replace(",", ".")
                            product_price = float(price_str)
                            break
                        price_match = re.search(
                            r"([\d\s]+[,.]\d+)", price_text.replace(" ", "").replace("\xa0", "")
                        )
                        if price_match:
                            price_str = price_match.group(1).replace(",", ".").replace(" ", "")
                            product_price = float(price_str)
                            break
                except Exception:
                    continue

            browser.close()

            if product_name:
                product_name = product_name[:200]

            if product_name and (
                "не найдено" in product_name.lower() or "по вашему запросу" in product_name.lower()
            ):
                return None

            return {"name": product_name, "price": product_price}

    except Exception as e:
        logger.warning(f"Failed to get product info for article {article}: {e}")
        return None


def get_wb_product_name_from_article(article: str) -> str | None:
    """Get product name from wildberries.by by article number.

    Args:
        article: Product article number (e.g., '178601980')

    Returns:
        Product name or None if not found
    """
    info = get_wb_product_info_from_article(article)
    return info.get("name") if info else None


def get_wb_product_name_async(article: str) -> str | None:
    """Async wrapper for get_wb_product_name_from_article.

    Runs Playwright in a thread pool to avoid blocking asyncio loop.
    """
    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            executor = ThreadPoolExecutor(max_workers=1)
            future = executor.submit(get_wb_product_name_from_article, article)
            return future.result(timeout=20)
        else:
            return get_wb_product_name_from_article(article)
    except Exception:
        return get_wb_product_name_from_article(article)


def get_wb_product_info_async(article: str) -> dict | None:
    """Async wrapper for get_wb_product_info_from_article.

    Runs Playwright in a thread pool to avoid blocking asyncio loop.
    Returns dict with 'name' and 'price' keys.
    """
    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            executor = ThreadPoolExecutor(max_workers=1)
            future = executor.submit(get_wb_product_info_from_article, article)
            return future.result(timeout=20)
        else:
            return get_wb_product_info_from_article(article)
    except Exception:
        return get_wb_product_info_from_article(article)


def get_wb_product_name_from_url(url: str) -> str | None:
    """Scrape product name from wildberries.by URL using Playwright.

    Args:
        url: URL like https://www.wildberries.by/catalog/12345678/detail.aspx

    Returns:
        Product name or None if not found
    """
    article = extract_article_from_url_static(url)
    if not article:
        return None
    return get_wb_product_name_from_article(article)


async def _fetch_wb_products_async(articles: list[str]) -> dict:
    """Fetch product info from Wildberries for multiple articles."""
    from concurrent.futures import ThreadPoolExecutor

    results = {}
    if not articles:
        return results

    def fetch_single(article: str) -> tuple[str, dict | None]:
        try:
            info = get_wb_product_info_from_article(article)
            return article, info
        except Exception as e:
            logger.warning(f"Failed to fetch article {article}: {e}")
            return article, None

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = list(executor.map(fetch_single, articles))

    for article, info in futures:
        if info:
            results[article] = info
        else:
            results[article] = {"error": "not found"}

    return results


async def receipt_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_receipt_menu(update, context)


async def show_receipt_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("receipt_creating", None)
    context.user_data.pop("receipt_items", None)
    context.user_data.pop("receipt_draft", None)

    user_id = update.effective_user.id
    receipts = get_user_receipt_history(user_id, limit=10)

    keyboard = []

    for receipt in receipts:
        date_str = receipt.created_at.strftime("%d.%m.%Y") if receipt.created_at else "?"
        items_count = len(receipt.items) if receipt.items else 0
        keyboard.append(
            [
                InlineKeyboardButton(
                    f"📄 Чек #{receipt.id} - {date_str} ({items_count} тов.)",
                    callback_data=f"receipt:view:{receipt.id}",
                )
            ]
        )

    keyboard.append([InlineKeyboardButton("➕ Новый чек", callback_data="receipt:new")])
    keyboard.append([InlineKeyboardButton("📖 Помощь", callback_data="receipt:help")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="menu:main")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    if receipts:
        text = "📋 Ваши товарные чеки WB\n\nВыберите чек или создайте новый:"
    else:
        text = "📋 Товарные чеки WB\n\nУ вас пока нет сохраненных чеков.\nНажмите 'Новый чек' для создания."

    if update.callback_query:
        await update.callback_query.edit_message_text(text=text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text=text, reply_markup=reply_markup)


async def receipt_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if not data.startswith("receipt:"):
        return

    parts = data.split(":")
    action = parts[1]

    pending_tasks = context.bot_data.get("pending_tasks", {})
    chat_id_to_user_id = context.bot_data.get("chat_id_to_user_id", {})

    if action == "new":
        await handle_create_receipt(update, context)
    elif action == "list":
        await show_receipt_menu(update, context)
    elif action == "view":
        receipt_id = int(parts[2])
        await handle_view_receipt(update, context, receipt_id)
    elif action == "delete":
        receipt_id = int(parts[2])
        await handle_delete_receipt(update, context, receipt_id)
    elif action == "help":
        await show_receipt_help(update, context)
    elif action == "preview":
        await show_receipt_preview(update, context)
    elif action == "edit":
        await handle_edit_receipt(update, context)
    elif action == "add_item":
        await handle_add_item_to_draft(update, context)
    elif action == "remove":
        idx = int(parts[2])
        await handle_remove_item_from_draft(update, context, idx)
    elif action == "edititem":
        idx = int(parts[2])
        await handle_edit_item_name(update, context, idx)
    elif action == "confirm":
        await handle_confirm_receipt(update, context, pending_tasks, chat_id_to_user_id)
    elif action == "cancel":
        await handle_cancel_receipt(update, context)
    elif action == "company":
        await handle_set_company(update, context)
    elif action == "generate_pdf":
        await handle_generate_pdf(update, context)


async def handle_create_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["receipt_creating"] = True
    context.user_data["receipt_draft"] = {"items": [], "raw_input": ""}

    help_text = """📝 Создание товарного чека

Введите товары в формате:
<b>Артикул</b> x <b>Количество</b> x <b>Цена</b>

Примеры:
• 178601980 x 2 x 150.50
• 123456 x 1
• https://wildberries.by/catalog/12345678/detail.aspx x 2 x 200

💡 Цена опциональна (можно не указывать).
💡 Можно указать несколько товаров - каждый с новой строки.

📋 После ввода нажмите "Подтвердить" для создания чека."""

    keyboard = [
        [InlineKeyboardButton("❌ Отмена", callback_data="receipt:cancel")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.edit_message_text(text=help_text, reply_markup=reply_markup)


async def show_receipt_preview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    draft = context.user_data.get("receipt_draft", {})
    items = draft.get("items", [])
    raw_input = draft.get("raw_input", "")

    if not raw_input and not items:
        await update.callback_query.answer("⚠️ Сначала введите товары", show_alert=True)
        return

    if raw_input:
        parsed = parse_items_input(raw_input)
        if not parsed:
            await update.callback_query.answer("⚠️ Не удалось распознать товары", show_alert=True)
            return

        items = [
            {
                "article": p["article"],
                "quantity": p["quantity"],
                "name": f"Артикул {p['article']}",
                "price": p.get("price", 0),
            }
            for p in parsed
        ]
        context.user_data["receipt_draft"]["items"] = items
        context.user_data["receipt_draft"]["raw_input"] = ""

    articles = [item["article"] for item in items]
    not_found_articles = []

    await update.callback_query.answer("🔄 Загружаю данные с WB...")

    product_results = await _fetch_wb_products_async(articles)

    for item in items:
        article = item["article"]
        if article in product_results:
            result = product_results[article]
            if not result.get("error"):
                item["name"] = result.get("name", f"Артикул {article}")
                if item.get("price", 0) == 0:
                    item["price"] = result.get("price", 0)
            else:
                not_found_articles.append(article)
        else:
            if item.get("name", "").startswith("Артикул ") and article.isdigit():
                product_name = get_wb_product_name_async(article)
                if product_name:
                    item["name"] = product_name
                    if item.get("price", 0) == 0:
                        product_info = get_wb_product_info_async(article)
                        if product_info:
                            item["price"] = product_info.get("price", 0)
                else:
                    not_found_articles.append(article)
            else:
                not_found_articles.append(article)

    text = "👁️ <b>Предпросмотр чека</b>\n\n"
    text += "┌────────────────────────────────────────────────────────┐\n"
    text += "│  № │ Артикул     │ Наименование            │ Кол │ Цена      │ Сумма    │\n"
    text += "├────┼─────────────┼────────────────────────┼─────┼───────────┼──────────┤\n"

    keyboard = []
    total = 0.0

    for idx, item in enumerate(items, start=1):
        article = item.get("article", "-")
        name = item.get("name", f"Артикул {article}")[:22]
        quantity = item.get("quantity", 1)
        price = item.get("price", 0)
        item_sum = price * quantity
        total += item_sum

        price_str = f"{price:.2f}" if price > 0 else "-"
        sum_str = f"{item_sum:.2f}" if price > 0 else "-"

        text += f"│ {idx:2}. │ {article[:11]:11} │ {name:<22} │ {quantity:<4} │ {price_str:<9} │ {sum_str:<8} │\n"

        keyboard.append(
            [
                InlineKeyboardButton(f"✏️ {idx}", callback_data=f"receipt:edititem:{idx}"),
                InlineKeyboardButton("❌", callback_data=f"receipt:remove:{idx}"),
            ]
        )

    if not items:
        text += "│ (нет товаров)                                          │\n"

    if not_found_articles:
        text += "\n⚠️ Не найдено на WB:\n"
        for art in not_found_articles[:5]:
            text += f"• {art}\n"
        if len(not_found_articles) > 5:
            text += f"• ... и ещё {len(not_found_articles) - 5}\n"

    total_str = f"{total:.2f}"
    text += "├────┴─────────────┴────────────────────────┴─────┴───────────┴──────────┤\n"
    text += f"│ ИТОГО:                                              │ {total_str:<8} │\n"
    text += "└────────────────────────────────────────────────────────┘"

    keyboard.append([InlineKeyboardButton("➕ Добавить товар", callback_data="receipt:add_item")])
    keyboard.append([InlineKeyboardButton("🏢 Фирма", callback_data="receipt:company")])
    keyboard.append(
        [InlineKeyboardButton("✅ Подтвердить и создать", callback_data="receipt:confirm")]
    )
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="receipt:edit")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.edit_message_text(
        text=text, reply_markup=reply_markup, parse_mode="HTML"
    )


async def handle_edit_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """📝 Добавление товаров

Введите товары в формате:
<b>Артикул</b> x <b>Количество</b>

Примеры:
• 178601980 x 2
• https://wildberries.ru/catalog/12345678/detail.aspx x 1

💡 Можно указать несколько товаров - каждый с новой строки.

📋 После ввода нажмите "Предпросмотр" для проверки."""

    keyboard = [
        [InlineKeyboardButton("👁️ Предпросмотр", callback_data="receipt:preview")],
        [InlineKeyboardButton("❌ Отмена", callback_data="receipt:cancel")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.edit_message_text(text=help_text, reply_markup=reply_markup)


async def handle_add_item_to_draft(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["receipt_adding_item"] = True

    draft = context.user_data.get("receipt_draft", {})
    receipt_id = draft.get("receipt_id")

    text = """➕ Добавление товара

Введите товар в формате:
<b>Артикул</b> x <b>Количество</b> x <b>Цена</b>

Пример: 178601980 x 2 x 150.50"""

    back_callback = f"receipt:view:{receipt_id}" if receipt_id else "receipt:preview"
    keyboard = [
        [InlineKeyboardButton("🔙 Назад", callback_data=back_callback)],
        [InlineKeyboardButton("❌ Отмена", callback_data="receipt:cancel")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.edit_message_text(
        text=text, reply_markup=reply_markup, parse_mode="HTML"
    )


async def handle_remove_item_from_draft(
    update: Update, context: ContextTypes.DEFAULT_TYPE, idx: int
):
    draft = context.user_data.get("receipt_draft", {})
    items = draft.get("items", [])
    receipt_id = draft.get("receipt_id")
    user_id = update.effective_user.id

    if 0 < idx <= len(items):
        removed = items.pop(idx - 1)
        context.user_data["receipt_draft"]["items"] = items

        total = sum(item.get("price", 0) * item.get("quantity", 1) for item in items)

        if receipt_id:
            update_receipt_history(receipt_id, user_id, items=items, total=total)

        await update.callback_query.answer(f"✅ Удален: {removed.get('name', 'Товар')[:30]}")

        if receipt_id:
            await handle_view_receipt(update, context, receipt_id)
        else:
            await show_receipt_preview(update, context)
    else:
        await update.callback_query.answer("❌ Товар не найден", show_alert=True)


async def handle_edit_item_name(update: Update, context: ContextTypes.DEFAULT_TYPE, idx: int):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    draft = context.user_data.get("receipt_draft", {})
    items = draft.get("items", [])
    receipt_id = draft.get("receipt_id")

    if 0 < idx <= len(items):
        item = items[idx - 1]
        context.user_data["receipt_editing_item_idx"] = idx - 1
        article = item.get("article", "-")
        current_name = item.get("name", f"Артикул {article}")

        text = f"""✏️ Изменение названия товара

Артикул: <code>{article}</code>
Текущее название: <b>{current_name}</b>

Введите новое название товара:"""

        back_callback = f"receipt:view:{receipt_id}" if receipt_id else "receipt:preview"
        keyboard = [
            [InlineKeyboardButton("🔙 Отмена", callback_data=back_callback)],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.callback_query.edit_message_text(
            text=text, reply_markup=reply_markup, parse_mode="HTML"
        )
    else:
        await update.callback_query.answer("❌ Товар не найден", show_alert=True)


async def handle_confirm_receipt(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    pending_tasks: dict = None,
    chat_id_to_user_id: dict = None,
):
    import json

    from services.common.kafka_config import kafka_config

    from .kafka_producer import TaskProducer

    draft = context.user_data.get("receipt_draft", {})
    items = draft.get("items", [])
    company = draft.get("company")
    logger.info(f"handle_confirm_receipt: company from draft='{company}'")

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    keyboard = [
        [InlineKeyboardButton("🔙 К списку чеков", callback_data="receipt:list")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.edit_message_text(
        text="🔄 Загружаю данные о товарах с WB...",
        reply_markup=reply_markup,
    )

    articles = [item["article"] for item in items]
    if articles:
        product_results = await _fetch_wb_products_async(articles)
        for item in items:
            article = item["article"]
            if article in product_results and not product_results[article].get("error"):
                result = product_results[article]
                item["name"] = result.get("name", f"Артикул {article}")
                if item.get("price", 0) == 0:
                    item["price"] = result.get("price", 0)

    items_json = json.dumps(items, ensure_ascii=False)

    receipt = create_receipt_history(
        user_id=user_id,
        items=items,
        total=sum(item.get("price", 0) * item.get("quantity", 1) for item in items),
        file_path="",
    )

    await update.callback_query.edit_message_text(
        text="🔄 Создаю чек...",
        reply_markup=reply_markup,
    )

    producer = TaskProducer(kafka_config)
    task = producer.create_receipt_task(
        user_id=user_id,
        chat_id=chat_id,
        items_text=items_json,
        metadata={
            "receipt_id": receipt.id if receipt else None,
            "is_json": True,
            "company": company,
        },
    )
    producer.send_task(task)

    if pending_tasks is not None:
        pending_tasks[task.task_id] = {
            "chat_id": chat_id,
            "task_type": "receipt",
        }

    if chat_id_to_user_id is not None:
        chat_id_to_user_id[str(chat_id)] = str(user_id)

    context.user_data.pop("receipt_creating", None)
    context.user_data.pop("receipt_draft", None)
    context.user_data.pop("receipt_adding_item", None)

    await context.bot.send_message(
        chat_id=chat_id,
        text="✅ Чек создан!\n\nВы получите PDF файл в ближайшее время.",
        reply_markup=reply_markup,
    )


async def handle_cancel_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("receipt_creating", None)
    context.user_data.pop("receipt_draft", None)
    context.user_data.pop("receipt_adding_item", None)

    await update.callback_query.answer("❌ Отменено")
    await show_receipt_menu(update, context)


async def handle_set_company(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    draft = context.user_data.get("receipt_draft", {})
    receipt_id = draft.get("receipt_id")

    user_id = update.effective_user.id
    settings = get_or_create_user_settings(user_id)
    current_company = draft.get("company") or settings.company if settings else ""

    text = f"""🏢 **Название фирмы**

Текущее: `{current_company or "Не задано"}`

Введите название фирмы для товарного чека.
Отправьте /skip чтобы удалить название."""

    back_callback = f"receipt:view:{receipt_id}" if receipt_id else "receipt:preview"
    keyboard = [
        [InlineKeyboardButton("🔙 Назад", callback_data=back_callback)],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.user_data["receipt_setting_company"] = True

    await update.callback_query.edit_message_text(
        text=text, reply_markup=reply_markup, parse_mode="Markdown"
    )


async def handle_company_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not context.user_data.get("receipt_setting_company"):
        return False

    user_id = update.effective_user.id
    text = update.message.text

    if text.lower() == "/skip":
        company = None
    else:
        company = text

    try:
        update_user_settings(user_id, company=company)
    except Exception as e:
        logger.warning(f"Failed to save company to user_settings: {e}")

    draft = context.user_data.get("receipt_draft", {})
    receipt_id = draft.get("receipt_id")
    draft["company"] = company
    context.user_data["receipt_draft"] = draft
    logger.info(f"handle_company_input: company='{company}' saved to draft")

    context.user_data.pop("receipt_setting_company", None)

    await update.message.reply_text(
        f"✅ Фирма сохранена: `{company or 'Не задана'}`", parse_mode="Markdown"
    )

    if receipt_id:
        await handle_view_receipt(update, context, receipt_id)
    else:
        await show_receipt_preview_from_message(update, context)
    return True


async def handle_generate_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    import json

    from services.common.kafka_config import kafka_config

    from .kafka_producer import TaskProducer

    draft = context.user_data.get("receipt_draft", {})
    items = draft.get("items", [])
    receipt_id = draft.get("receipt_id")

    if not items:
        await update.callback_query.answer("⚠️ Нет товаров в чеке", show_alert=True)
        return

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    keyboard = [
        [InlineKeyboardButton("🔙 К чеку", callback_data=f"receipt:view:{receipt_id}")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.edit_message_text(
        text="🔄 Создаю PDF чек...",
        reply_markup=reply_markup,
    )

    items_json = json.dumps(items, ensure_ascii=False)

    settings = get_or_create_user_settings(user_id)
    company = settings.company if settings else None

    producer = TaskProducer(kafka_config)
    task = producer.create_receipt_task(
        user_id=user_id,
        chat_id=chat_id,
        items_text=items_json,
        metadata={"receipt_id": receipt_id, "is_json": True, "company": company},
    )
    producer.send_task(task)

    await context.bot.send_message(
        chat_id=chat_id,
        text="✅ PDF чек создан!\n\nВы получите файл в ближайшее время.",
        reply_markup=reply_markup,
    )


async def handle_view_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE, receipt_id: int):
    context.user_data.pop("receipt_creating", None)
    context.user_data.pop("receipt_items", None)

    user_id = update.effective_user.id
    receipt = get_receipt_by_id(receipt_id, user_id)

    if not receipt:
        await update.callback_query.edit_message_text(text="❌ Чек не найден")
        return

    settings = get_or_create_user_settings(user_id)
    company = settings.company if settings else None

    context.user_data["receipt_draft"] = {
        "items": receipt.items or [],
        "receipt_id": receipt_id,
        "company": company,
    }

    items = receipt.items or []
    total = float(receipt.total) if receipt.total else 0

    text = "👁️ <b>Предпросмотр чека</b>\n\n"
    if company:
        text += f"🏢 Фирма: {company}\n\n"

    text += "┌────────────────────────────────────────────────────────┐\n"
    text += "│  № │ Артикул     │ Наименование            │ Кол │ Цена      │ Сумма    │\n"
    text += "├────┼─────────────┼────────────────────────┼─────┼───────────┼──────────┤\n"

    keyboard = []
    for idx, item in enumerate(items, start=1):
        article = item.get("article", "-")
        name = item.get("name", f"Артикул {article}")[:22]
        quantity = item.get("quantity", 1)
        price = item.get("price", 0)
        item_sum = price * quantity

        price_str = f"{price:.2f}" if price > 0 else "-"
        sum_str = f"{item_sum:.2f}" if price > 0 else "-"

        text += f"│ {idx:2}. │ {article[:11]:11} │ {name:<22} │ {quantity:<4} │ {price_str:<9} │ {sum_str:<8} │\n"

        keyboard.append(
            [
                InlineKeyboardButton(f"✏️ {idx}", callback_data=f"receipt:edititem:{idx}"),
                InlineKeyboardButton("❌", callback_data=f"receipt:remove:{idx}"),
            ]
        )

    if not items:
        text += "│ (нет товаров)                                          │\n"

    total_str = f"{total:.2f}"
    text += "├────┴─────────────┴────────────────────────┴─────┴───────────┴──────────┤\n"
    text += f"│ ИТОГО:                                              │ {total_str:<8} │\n"
    text += "└────────────────────────────────────────────────────────┘"

    keyboard.append([InlineKeyboardButton("➕ Добавить товар", callback_data="receipt:add_item")])
    keyboard.append([InlineKeyboardButton("🏢 Фирма", callback_data="receipt:company")])
    keyboard.append([InlineKeyboardButton("📄 Создать PDF", callback_data="receipt:generate_pdf")])
    keyboard.append([InlineKeyboardButton("🔙 К списку чеков", callback_data="receipt:list")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.edit_message_text(
        text=text, reply_markup=reply_markup, parse_mode="HTML"
    )

    keyboard.append([InlineKeyboardButton("🔙 К списку чеков", callback_data="receipt:list")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.edit_message_text(
        text=text, reply_markup=reply_markup, parse_mode="HTML"
    )


async def handle_delete_receipt(
    update: Update, context: ContextTypes.DEFAULT_TYPE, receipt_id: int
):
    user_id = update.effective_user.id
    success = delete_receipt_history(receipt_id, user_id)

    if success:
        await update.callback_query.answer("✅ Чек удален")
    else:
        await update.callback_query.answer("❌ Не удалось удалить")

    await show_receipt_menu(update, context)


async def show_receipt_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """📖 Помощь по товарным чекам

Этот бот поможет вам создать товарный чек для Wildberries.

<b>Формат ввода:</b>
• Артикул: 178601980 x 2
• Ссылка: https://wildberries.ru/catalog/12345678/detail.aspx x 1

<b>Пример:</b>
178601980 x 2
99999999 x 1
https://wildberries.ru/catalog/11111111/detail.aspx x 3

<b>После создания:</b>
• PDF чек будет отправлен вам
• Чек сохраняется в истории

<b>Примечание:</b>
• PDF генерируется в формате товарного чека РБ
• Валюта: BYN (белорусские рубли)"""

    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="receipt:list")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.edit_message_text(
        text=help_text, reply_markup=reply_markup, parse_mode="HTML"
    )


async def cancel_receipt_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("receipt_creating", None)
    context.user_data.pop("receipt_items", None)
    context.user_data.pop("receipt_draft", None)

    await update.message.reply_text("❌ Создание чека отменено.")
    await show_receipt_menu(update, context)


async def process_receipt_items(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    items_text: str,
    pending_tasks: dict = None,
    chat_id_to_user_id: dict = None,
):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    from services.common.kafka_config import kafka_config

    from .kafka_producer import TaskProducer

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    editing_idx = context.user_data.pop("receipt_editing_item_idx", None)
    if editing_idx is not None:
        draft = context.user_data.get("receipt_draft", {"items": []})
        items = draft.get("items", [])
        if 0 <= editing_idx < len(items):
            items[editing_idx]["name"] = items_text.strip()
            items[editing_idx]["price"] = 0
            context.user_data["receipt_draft"]["items"] = items
            await update.message.reply_text(f"✅ Название изменено: {items_text.strip()[:50]}")
            await show_receipt_preview_from_message(update, context)
            return
        else:
            await update.message.reply_text("❌ Товар не найден")
            return

    if context.user_data.get("receipt_setting_company"):
        await handle_company_input(update, context)
        return

    if context.user_data.get("receipt_adding_item"):
        parsed = parse_items_input(items_text)
        if parsed:
            draft = context.user_data.get("receipt_draft", {"items": [], "raw_input": ""})
            for p in parsed:
                product_info = None
                product_name = None
                product_price = p.get("price", 0)

                if p["article"].isdigit():
                    logger.info(f"Fetching product info for article: {p['article']}")
                    product_info = get_wb_product_info_async(p["article"])
                    logger.info(f"Product info result: {product_info}")

                    if product_info:
                        product_name = product_info.get("name")
                        if product_price == 0 and product_info.get("price", 0) > 0:
                            product_price = product_info.get("price", 0)

                draft["items"].append(
                    {
                        "article": p["article"],
                        "quantity": p["quantity"],
                        "name": product_name or f"Артикул {p['article']}",
                        "price": product_price,
                    }
                )
            context.user_data["receipt_draft"] = draft
            context.user_data.pop("receipt_adding_item", None)
            added_count = len(parsed)
            await update.message.reply_text(f"✅ Добавлено: {added_count} товар(ов)")
            await show_receipt_preview_from_message(update, context)
            return
        else:
            await update.message.reply_text("⚠️ Не удалось распознать товар. Попробуйте еще раз.")
            return

    draft = context.user_data.get("receipt_draft", {})
    if draft.get("raw_input"):
        draft["raw_input"] = draft["raw_input"] + "\n" + items_text
    else:
        draft["raw_input"] = items_text

    context.user_data["receipt_draft"] = draft

    keyboard = [
        [InlineKeyboardButton("👁️ Предпросмотр", callback_data="receipt:preview")],
        [InlineKeyboardButton("❌ Отмена", callback_data="receipt:cancel")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "✅ Принято! Товары добавлены.\n\nНажмите 'Предпросмотр' для проверки или продолжайте вводить товары.",
        reply_markup=reply_markup,
    )


async def show_receipt_preview_from_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    draft = context.user_data.get("receipt_draft", {})
    items = draft.get("items", [])
    raw_input = draft.get("raw_input", "")

    if raw_input:
        parsed = parse_items_input(raw_input)
        if parsed:
            for p in parsed:
                items.append(
                    {
                        "article": p["article"],
                        "quantity": p["quantity"],
                        "name": f"Артикул {p['article']}",
                        "price": 0,
                    }
                )
            context.user_data["receipt_draft"]["items"] = items
            context.user_data["receipt_draft"]["raw_input"] = ""

    for item in items:
        if item.get("article", "").isdigit() and item.get("name", "").startswith("Артикул "):
            logger.info(f"[preview] Fetching product info for article: {item['article']}")
            product_info = get_wb_product_info_async(item["article"])
            logger.info(f"[preview] Product info result: {product_info}")
            if product_info:
                item["name"] = product_info.get("name", item["name"])
                if item.get("price", 0) == 0:
                    item["price"] = product_info.get("price", 0)

    articles = [item["article"] for item in items]
    not_found_articles = []

    await update.callback_query.answer("🔄 Загружаю данные с WB...")

    product_results = await _fetch_wb_products_async(articles)

    for item in items:
        article = item["article"]
        if article in product_results:
            result = product_results[article]
            if not result.get("error"):
                item["name"] = result.get("name", f"Артикул {article}")
                if item.get("price", 0) == 0:
                    item["price"] = result.get("price", 0)
            else:
                not_found_articles.append(article)
        else:
            if item.get("name", "").startswith("Артикул ") and article.isdigit():
                logger.info(f"[preview] Fetching product info for article: {article}")
                product_info = get_wb_product_info_async(article)
                logger.info(f"[preview] Product info result: {product_info}")
                if product_info:
                    item["name"] = product_info.get("name", item["name"])
                    if item.get("price", 0) == 0:
                        item["price"] = product_info.get("price", 0)
                else:
                    not_found_articles.append(article)
            else:
                not_found_articles.append(article)

    text = "👁️ <b>Предпросмотр чека</b>\n\n"
    text += "┌────────────────────────────────────────────────────────┐\n"
    text += "│  № │ Артикул     │ Наименование            │ Кол │ Цена      │ Сумма    │\n"
    text += "├────┼─────────────┼────────────────────────┼─────┼───────────┼──────────┤\n"

    keyboard = []
    total = 0.0

    for idx, item in enumerate(items, start=1):
        article = item.get("article", "-")
        name = item.get("name", f"Артикул {article}")[:22]
        quantity = item.get("quantity", 1)
        price = item.get("price", 0)
        item_sum = price * quantity
        total += item_sum

        price_str = f"{price:.2f}" if price > 0 else "-"
        sum_str = f"{item_sum:.2f}" if price > 0 else "-"

        text += f"│ {idx:2}. │ {article[:11]:11} │ {name:<22} │ {quantity:<4} │ {price_str:<9} │ {sum_str:<8} │\n"

        keyboard.append(
            [
                InlineKeyboardButton(f"✏️ {idx}", callback_data=f"receipt:edititem:{idx}"),
                InlineKeyboardButton("❌", callback_data=f"receipt:remove:{idx}"),
            ]
        )

    if not items:
        text += "│ (нет товаров)                                          │\n"

    if not_found_articles:
        text += "\n⚠️ Не найдено на WB:\n"
        for art in not_found_articles[:5]:
            text += f"• {art}\n"
        if len(not_found_articles) > 5:
            text += f"• ... и ещё {len(not_found_articles) - 5}\n"

    total_str = f"{total:.2f}"
    text += "├────┴─────────────┴────────────────────────┴─────┴───────────┴──────────┤\n"
    text += f"│ ИТОГО:                                              │ {total_str:<8} │\n"
    text += "└────────────────────────────────────────────────────────┘"

    keyboard.append([InlineKeyboardButton("➕ Добавить товар", callback_data="receipt:add_item")])
    keyboard.append([InlineKeyboardButton("🏢 Фирма", callback_data="receipt:company")])
    keyboard.append(
        [InlineKeyboardButton("✅ Подтвердить и создать", callback_data="receipt:confirm")]
    )
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="receipt:edit")])
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="receipt:cancel")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(text=text, reply_markup=reply_markup, parse_mode="HTML")
