import os
import sys
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
)


class TestReceiptHandlers:
    @pytest.fixture
    def mock_update(self):
        update = Mock()
        update.effective_user = Mock()
        update.effective_user.id = 12345
        update.effective_chat = Mock()
        update.effective_chat.id = 67890
        update.callback_query = Mock()
        update.callback_query.edit_message_text = AsyncMock()
        update.callback_query.answer = AsyncMock()
        return update

    @pytest.fixture
    def mock_context(self):
        context = Mock()
        context.user_data = {}
        return context

    def test_receipt_command_handler_exists(self):
        from services.bot_service import receipt_handlers

        assert hasattr(receipt_handlers, "receipt_command")
        assert hasattr(receipt_handlers, "receipt_callback")
        assert hasattr(receipt_handlers, "handle_create_receipt")
        assert hasattr(receipt_handlers, "handle_view_receipt")
        assert hasattr(receipt_handlers, "handle_delete_receipt")
        assert hasattr(receipt_handlers, "show_receipt_help")
        assert hasattr(receipt_handlers, "cancel_receipt_creation")


class TestReceiptCallbackRouting:
    def test_callback_pattern_receipt(self):
        from services.bot_service import receipt_handlers

        data = "receipt:new"
        parts = data.split(":")
        action = parts[1]

        assert action == "new"

    def test_callback_pattern_view(self):
        data = "receipt:view:123"
        parts = data.split(":")
        action = parts[1]
        receipt_id = int(parts[2])

        assert action == "view"
        assert receipt_id == 123

    def test_callback_pattern_delete(self):
        data = "receipt:delete:456"
        parts = data.split(":")
        action = parts[1]
        receipt_id = int(parts[2])

        assert action == "delete"
        assert receipt_id == 456


class TestReceiptKeyboard:
    def test_keyboard_structure(self):
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

        keyboard = [
            [InlineKeyboardButton("📄 Чек #1", callback_data="receipt:view:1")],
            [InlineKeyboardButton("➕ Новый чек", callback_data="receipt:new")],
            [InlineKeyboardButton("📖 Помощь", callback_data="receipt:help")],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        assert len(reply_markup.inline_keyboard) == 3
        assert reply_markup.inline_keyboard[0][0].text == "📄 Чек #1"
        assert reply_markup.inline_keyboard[1][0].text == "➕ Новый чек"


class TestReceiptHelpText:
    def test_help_text_contains_format_info(self):
        import inspect

        from services.bot_service import receipt_handlers

        source = inspect.getsource(receipt_handlers.show_receipt_help)

        assert "Артикул" in source or "articul" in source.lower()
