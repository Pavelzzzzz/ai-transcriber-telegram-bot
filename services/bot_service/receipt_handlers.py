import logging
import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from services.common.user_settings_repo import (
    create_receipt_history,
    delete_receipt_history,
    get_receipt_by_id,
    get_user_receipt_history,
    update_receipt_history,
)

logger = logging.getLogger(__name__)


def parse_items_input(text: str) -> list[dict[str, str | int]]:
    items: list[dict[str, str | int]] = []
    article_pattern = re.compile(r"^(.+?)\s*[xXхХ]\s*(\d+)$")

    for line in text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue

        match = article_pattern.match(line)
        if not match:
            continue

        raw = match.group(1).strip()
        quantity = int(match.group(2))

        if quantity <= 0:
            continue

        if "wildberries" in raw.lower():
            article = extract_article_from_url_static(raw)
        else:
            article = raw

        if article and article.isdigit():
            items.append({"article": article, "quantity": quantity})

    return items


def extract_article_from_url_static(url: str) -> str | None:
    match = re.search(r"/catalog/(\d+)", url)
    if match:
        return match.group(1)
    return None


async def _fetch_wb_products_async(articles: list[str]) -> dict:
    return {}


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


async def handle_create_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["receipt_creating"] = True
    context.user_data["receipt_draft"] = {"items": [], "raw_input": ""}

    help_text = """📝 Создание товарного чека

Введите товары в формате:
<b>Артикул</b> x <b>Количество</b>

Примеры:
• 178601980 x 2
• https://wildberries.ru/catalog/12345678/detail.aspx x 1

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
                "price": 0,
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
                item["price"] = result.get("price", 0)
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
                InlineKeyboardButton(f"❌", callback_data=f"receipt:remove:{idx}"),
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

    text = """➕ Добавление товара

Введите товар в формате:
<b>Артикул</b> x <b>Количество</b>

Пример: 178601980 x 2"""

    keyboard = [
        [InlineKeyboardButton("🔙 Назад к предпросмотру", callback_data="receipt:preview")],
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

    if 0 < idx <= len(items):
        removed = items.pop(idx - 1)
        context.user_data["receipt_draft"]["items"] = items
        await update.callback_query.answer(f"✅ Удален: {removed.get('name', 'Товар')[:30]}")
        await show_receipt_preview(update, context)
    else:
        await update.callback_query.answer("❌ Товар не найден", show_alert=True)


async def handle_edit_item_name(update: Update, context: ContextTypes.DEFAULT_TYPE, idx: int):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    draft = context.user_data.get("receipt_draft", {})
    items = draft.get("items", [])

    if 0 < idx <= len(items):
        item = items[idx - 1]
        context.user_data["receipt_editing_item_idx"] = idx - 1
        article = item.get("article", "-")
        current_name = item.get("name", f"Артикул {article}")

        text = f"""✏️ Изменение названия товара

Артикул: <code>{article}</code>
Текущее название: <b>{current_name}</b>

Введите новое название товара:"""

        keyboard = [
            [InlineKeyboardButton("🔙 Отмена", callback_data="receipt:preview")],
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
        metadata={"receipt_id": receipt.id if receipt else None, "is_json": True},
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


async def handle_view_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE, receipt_id: int):
    context.user_data.pop("receipt_creating", None)
    context.user_data.pop("receipt_items", None)

    user_id = update.effective_user.id
    receipt = get_receipt_by_id(receipt_id, user_id)

    if not receipt:
        await update.callback_query.edit_message_text(text="❌ Чек не найден")
        return

    date_str = receipt.created_at.strftime("%d.%m.%Y %H:%M") if receipt.created_at else "?"
    items = receipt.items or []
    total = float(receipt.total) if receipt.total else 0

    text = f"📋 Чек #{receipt.id}\n📅 {date_str}\n\n"
    text += "📦 Товары:\n"

    for idx, item in enumerate(items[:10], start=1):
        name = item.get("name", "Неизвестно")[:40]
        quantity = item.get("quantity", 1)
        price = item.get("price", 0)
        text += f"{idx}. {name}\n   x{quantity} × {price:.2f} BYN\n"

    if len(items) > 10:
        text += f"\n... и ещё {len(items) - 10} товаров"

    text += f"\n\n💰 ИТОГО: {total:.2f} BYN"

    keyboard = [
        [InlineKeyboardButton("🗑️ Удалить", callback_data=f"receipt:delete:{receipt_id}")],
        [InlineKeyboardButton("🔙 К списку", callback_data="receipt:list")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.edit_message_text(text=text, reply_markup=reply_markup)


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

    if context.user_data.get("receipt_adding_item"):
        parsed = parse_items_input(items_text)
        if parsed:
            draft = context.user_data.get("receipt_draft", {"items": [], "raw_input": ""})
            for p in parsed:
                draft["items"].append(
                    {
                        "article": p["article"],
                        "quantity": p["quantity"],
                        "name": f"Артикул {p['article']}",
                        "price": 0,
                    }
                )
            context.user_data["receipt_draft"] = draft
            context.user_data.pop("receipt_adding_item", None)
            await update.message.reply_text(f"✅ Добавлено: {len(parsed)} товар(ов)")
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

    articles = [item["article"] for item in items]
    not_found_articles = []

    if articles:
        product_results = await _fetch_wb_products_async(articles)

        for item in items:
            article = item["article"]
            if article in product_results:
                result = product_results[article]
                if not result.get("error"):
                    item["name"] = result.get("name", f"Артикул {article}")
                    item["price"] = result.get("price", 0)
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
                InlineKeyboardButton(f"❌", callback_data=f"receipt:remove:{idx}"),
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
    keyboard.append(
        [InlineKeyboardButton("✅ Подтвердить и создать", callback_data="receipt:confirm")]
    )
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="receipt:edit")])
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="receipt:cancel")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(text=text, reply_markup=reply_markup, parse_mode="HTML")
