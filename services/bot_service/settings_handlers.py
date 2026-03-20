import logging
import os
import sys

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.common.hardware import (
    ASPECT_RATIO_NAMES,
    ASPECT_RATIO_SIZES,
    MODELS_CONFIG,
    STYLES_CONFIG,
    VARIATION_LABELS,
    get_available_models,
    get_model_display_name,
    get_style_display_name,
)
from services.common.user_settings_repo import (
    get_or_create_user_settings,
    reset_user_settings,
    update_user_settings,
)

logger = logging.getLogger(__name__)

PENDING_NEGATIVE_PROMPT = {}


def get_settings_keyboard(user_id: int) -> InlineKeyboardMarkup:
    settings = get_or_create_user_settings(user_id)

    current_model = settings.image_model or "sd15"
    current_style = settings.image_style or ""
    current_aspect = settings.aspect_ratio or "1:1"
    current_variations = settings.num_variations or 1
    current_noise = settings.noise_reduction if settings else True

    model_name = get_model_display_name(current_model)
    style_name = get_style_display_name(current_style) if current_style else "Без стиля"
    aspect_name = ASPECT_RATIO_NAMES.get(current_aspect, current_aspect)

    keyboard = [
        [
            InlineKeyboardButton(f"🎨 Модель: {model_name}", callback_data="settings:model"),
            InlineKeyboardButton(f"🎭 Стиль: {style_name}", callback_data="settings:style"),
        ],
        [
            InlineKeyboardButton(f"📐 Размер: {aspect_name}", callback_data="settings:aspect"),
            InlineKeyboardButton(
                f"🔢 Вариаций: {current_variations}", callback_data="settings:variations"
            ),
        ],
        [
            InlineKeyboardButton(
                f"📝 Негативный промпт: {'Задан' if settings.negative_prompt else 'Не задан'}",
                callback_data="settings:negative",
            ),
        ],
        [
            InlineKeyboardButton(
                f"🔊 Шумоподавление: {'Вкл' if current_noise else 'Выкл'}",
                callback_data="settings:noise",
            ),
        ],
        [
            InlineKeyboardButton("🔄 Сбросить настройки", callback_data="settings:reset"),
        ],
        [
            InlineKeyboardButton("⬅️ Назад в меню", callback_data="settings:back"),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return

    user_id = update.effective_user.id

    try:
        settings = get_or_create_user_settings(user_id)
    except Exception as e:
        logger.warning(f"DB not available, using defaults: {e}")
        settings = None

    current_model = settings.image_model if settings else "sdxl"
    current_style = settings.image_style if settings else ""
    current_aspect = settings.aspect_ratio if settings else "1:1"
    current_variations = settings.num_variations if settings else 1
    current_negative = settings.negative_prompt if settings else ""
    current_noise = settings.noise_reduction if settings else True

    available_models = get_available_models()
    model_name = (
        get_model_display_name(current_model)
        if current_model in available_models
        else f"{current_model} ⚠️"
    )
    style_name = get_style_display_name(current_style) if current_style else "Без стиля"
    aspect_name = ASPECT_RATIO_NAMES.get(current_aspect, current_aspect)

    text = f"""
🎨 **Настройки генерации изображений**

━━━━━━━━━━━━━━━━━━━━━━━

**Текущие настройки:**
• 🎯 Модель: {model_name}
• 🎭 Стиль: {style_name}
• 📐 Размер: {aspect_name}
• 🔢 Вариаций: {current_variations}
• 📝 Негативный промпт: {"Задан" if current_negative else "Не задан"}
• 🔊 Шумоподавление: {"Включено" if current_noise else "Выключено"}

━━━━━━━━━━━━━━━━━━━━━━━

Выберите параметр для изменения:
"""

    keyboard = get_settings_keyboard(user_id)

    await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")


async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query or not update.effective_user:
        return

    await query.answer()
    user_id = update.effective_user.id
    data = query.data

    if data == "settings:back":
        await query.edit_message_text("✅ Настройки сохранены")
        return

    if data == "settings:reset":
        try:
            reset_user_settings(user_id)
            PENDING_NEGATIVE_PROMPT.pop(user_id, None)
        except Exception as e:
            logger.warning(f"DB not available: {e}")
        await query.edit_message_text("🔄 Настройки сброшены к значениям по умолчанию")
        return

    if data == "settings:model":
        await show_model_selection(query, user_id)
        return

    if data == "settings:style":
        await show_style_selection(query, user_id)
        return

    if data == "settings:aspect":
        await show_aspect_selection(query, user_id)
        return

    if data == "settings:variations":
        await show_variations_selection(query, user_id)
        return

    if data == "settings:negative":
        await ask_negative_prompt(query, user_id)
        return

    if data == "settings:noise":
        await handle_settings_noise_callback(query, user_id)
        return


async def show_model_selection(query, user_id: int):
    settings = get_or_create_user_settings(user_id)
    current_model = settings.image_model if settings else "sd15"
    available_models = get_available_models()

    keyboard = []
    for model_id, config in MODELS_CONFIG.items():
        is_selected = model_id == current_model
        is_available = model_id in available_models

        prefix = "✅ " if is_selected else ""
        status = " ⚠️" if not is_available else ""

        button_text = f"{prefix}{config['name']}{status}"
        keyboard.append(
            [InlineKeyboardButton(button_text, callback_data=f"settings:model:{model_id}")]
        )

    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="settings:back")])

    text = "**Выберите модель:**\n\n"
    text += "ℹ️ Модель будет сохранена и использована для генерации\n"

    await query.edit_message_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )


async def show_style_selection(query, user_id: int):
    settings = get_or_create_user_settings(user_id)
    current_style = settings.image_style if settings else ""

    keyboard = []
    for style_id, config in STYLES_CONFIG.items():
        is_selected = style_id == current_style
        prefix = "✅ " if is_selected else ""
        button_text = f"{prefix}{config['name']}"
        keyboard.append(
            [InlineKeyboardButton(button_text, callback_data=f"settings:style:{style_id}")]
        )

    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="settings:back")])

    await query.edit_message_text(
        "**Выберите стиль:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )


async def show_aspect_selection(query, user_id: int):
    settings = get_or_create_user_settings(user_id)
    current_aspect = settings.aspect_ratio if settings else "1:1"

    keyboard = []
    for aspect_id, name in ASPECT_RATIO_NAMES.items():
        is_selected = aspect_id == current_aspect
        prefix = "✅ " if is_selected else ""
        size = ASPECT_RATIO_SIZES.get(aspect_id, (1024, 1024))
        button_text = f"{prefix}{name} ({size[0]}×{size[1]})"
        keyboard.append(
            [InlineKeyboardButton(button_text, callback_data=f"settings:aspect:{aspect_id}")]
        )

    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="settings:back")])

    await query.edit_message_text(
        "**Выберите размер:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )


async def show_variations_selection(query, user_id: int):
    settings = get_or_create_user_settings(user_id)
    current_variations = settings.num_variations if settings else 1

    keyboard = []
    for num in [1, 2, 3, 4]:
        is_selected = num == current_variations
        prefix = "✅ " if is_selected else ""
        button_text = f"{prefix}{VARIATION_LABELS[num]}"
        keyboard.append(
            [InlineKeyboardButton(button_text, callback_data=f"settings:variations:{num}")]
        )

    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="settings:back")])

    await query.edit_message_text(
        "**Выберите количество вариаций:**",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def ask_negative_prompt(query, user_id: int):
    settings = get_or_create_user_settings(user_id)
    current_negative = settings.negative_prompt if settings else ""

    text = "**Негативный промпт**\n\n"
    text += f"Текущий: `{current_negative}`\n\n"
    text += "Введите новый негативный промпт (элементы, которые нужно исключить).\n"
    text += "Отправьте /skip чтобы убрать негативный промпт."

    PENDING_NEGATIVE_PROMPT[user_id] = True

    await query.edit_message_text(text, parse_mode="Markdown")


async def handle_negative_prompt_input(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int
) -> bool:
    if not PENDING_NEGATIVE_PROMPT.get(user_id):
        return False

    text = update.message.text
    negative_prompt = "" if text.lower() == "/skip" else text

    try:
        update_user_settings(user_id, negative_prompt=negative_prompt)
    except Exception as e:
        logger.warning(f"DB not available: {e}")

    PENDING_NEGATIVE_PROMPT.pop(user_id, None)

    await update.message.reply_text(
        f"✅ Негативный промпт сохранен: `{negative_prompt or 'Не задан'}`", parse_mode="Markdown"
    )
    return True


async def handle_settings_model_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query or not query.data or not query.data.startswith("settings:model:"):
        return

    await query.answer()
    user_id = update.effective_user.id
    model = query.data.split(":")[-1]

    available_models = get_available_models()
    model_info = MODELS_CONFIG.get(model, {})
    model_name = model_info.get("name", model)

    try:
        update_user_settings(user_id, image_model=model)

        if model in available_models:
            await query.edit_message_text(
                f"✅ **Модель изменена на:** {model_name}\n\n"
                f"Теперь используется для генерации изображений."
            )
        else:
            await query.edit_message_text(
                f"⚠️ **Модель изменена на:** {model_name}\n\n"
                f"Внимание: эта модель может требовать больше ресурсов."
            )
    except Exception as e:
        logger.warning(f"DB not available: {e}")
        await query.edit_message_text("❌ Не удалось сохранить настройку. Попробуйте позже.")


async def handle_settings_style_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query or not query.data or not query.data.startswith("settings:style:"):
        return

    await query.answer()
    user_id = update.effective_user.id
    style = query.data.split(":")[-1]

    style_info = STYLES_CONFIG.get(style, {})
    style_name = style_info.get("name", style)

    try:
        update_user_settings(user_id, image_style=style)
        await query.edit_message_text(
            f"✅ **Стиль изменен на:** {style_name}\n\n"
            f"Теперь используется для генерации изображений."
        )
    except Exception as e:
        logger.warning(f"DB not available: {e}")
        await query.edit_message_text("❌ Не удалось сохранить настройку. Попробуйте позже.")


async def handle_settings_aspect_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query or not query.data or not query.data.startswith("settings:aspect:"):
        return

    await query.answer()
    user_id = update.effective_user.id
    aspect = query.data.split(":")[-1]

    try:
        update_user_settings(user_id, aspect_ratio=aspect)
        await query.edit_message_text(
            f"✅ **Соотношение сторон изменено на:** {aspect}\n\n"
            f"Теперь используется для генерации изображений."
        )
    except Exception as e:
        logger.warning(f"DB not available: {e}")
        await query.edit_message_text("❌ Не удалось сохранить настройку. Попробуйте позже.")


async def handle_settings_variations_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query or not query.data or not query.data.startswith("settings:variations:"):
        return

    await query.answer()
    user_id = update.effective_user.id
    variations = int(query.data.split(":")[-1])

    try:
        update_user_settings(user_id, num_variations=variations)
        await query.edit_message_text(
            f"✅ **Количество вариаций изменено на:** {variations}\n\n"
            f"Теперь будет генерироваться {variations} изображений."
        )
    except Exception as e:
        logger.warning(f"DB not available: {e}")
        await query.edit_message_text("❌ Не удалось сохранить настройку. Попробуйте позже.")


async def handle_settings_noise_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query or not query.data or query.data != "settings:noise":
        return

    await query.answer()
    user_id = update.effective_user.id

    try:
        settings = get_or_create_user_settings(user_id)
        current_value = settings.noise_reduction if settings else True
        new_value = not current_value

        update_user_settings(user_id, noise_reduction=new_value)

        await query.edit_message_text(
            f"✅ **Шумоподавление:** {'Включено' if new_value else 'Выключено'}\n\n"
            f"Будет {'применяться' if new_value else 'пропускаться'} при транскрибации голоса."
        )
    except Exception as e:
        logger.warning(f"DB not available: {e}")
        await query.edit_message_text("❌ Не удалось сохранить настройку. Попробуйте позже.")
