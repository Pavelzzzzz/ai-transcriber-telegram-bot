import logging
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from services.common.user_settings_repo import (
    delete_receipt_history,
    get_receipt_by_id,
    get_user_receipt_history,
)

logger = logging.getLogger(__name__)


async def receipt_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_receipt_menu(update, context)


async def show_receipt_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
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


async def handle_create_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["receipt_creating"] = True

    help_text = """📝 Создание товарного чека

Введите товары в одном из форматов:

🔢 <b>Артикул</b> x <b>Количество</b>
   Пример: 178601980 x 2

🔗 <b>Ссылка WB</b> x <b>Количество</b>
   Пример: https://wildberries.ru/catalog/12345678/detail.aspx x 1

💡 Можно указать несколько товаров - каждый с новой строки.

⏹️ Отправьте "готово" когда закончите
❌ Отправьте "отмена" для отмены"""

    keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="receipt:cancel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.edit_message_text(text=help_text, reply_markup=reply_markup)


async def handle_view_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE, receipt_id: int):
    user_id = update.effective_user.id
    receipt = get_receipt_by_id(receipt_id, user_id)

    if not receipt:
        await update.callback_query.edit_message_text(text="❌ Чек не найден")
        return

    date_str = receipt.created_at.strftime("%d.%m.%Y %H:%M") if receipt.created_at else "?"
    items = receipt.items or []
    total = float(receipt.total) if receipt.total else 0

    text = f"📋 Чек #{receipt.id}\n📅 {date_str}\n\n"

    for idx, item in enumerate(items[:10], start=1):
        name = item.get("name", "Неизвестно")[:40]
        quantity = item.get("quantity", 1)
        price = item.get("price", 0)
        text += f"{idx}. {name}\n   x{quantity} × {price:.2f} ₽\n"

    if len(items) > 10:
        text += f"\n... и ещё {len(items) - 10} товаров"

    text += f"\n\n💰 ИТОГО: {total:.2f} ₽"

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
• Если товар не найден по артикулу, можно ввести название вручную
• PDF генерируется в формате товарного чека РБ"""

    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="receipt:list")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.edit_message_text(text=help_text, reply_markup=reply_markup)


async def cancel_receipt_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("receipt_creating", None)
    context.user_data.pop("receipt_items", None)
    await update.callback_query.answer("❌ Отменено")
    await show_receipt_menu(update, context)


async def process_receipt_items(
    update: Update, context: ContextTypes.DEFAULT_TYPE, items_text: str
):
    from services.common.kafka_config import kafka_config

    from .kafka_producer import TaskProducer

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    producer = TaskProducer(kafka_config)
    producer.create_receipt_task(
        user_id=user_id,
        chat_id=chat_id,
        items_text=items_text,
    )

    context.user_data.pop("receipt_creating", None)
    context.user_data.pop("receipt_items", None)

    await update.message.reply_text(
        "🔄 Ищу товары на Wildberries и генерирую чек...\nЭто может занять несколько секунд."
    )
