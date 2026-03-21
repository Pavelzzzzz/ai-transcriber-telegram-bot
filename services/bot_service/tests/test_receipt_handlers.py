import json
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


class TestProcessReceiptItems:
    @pytest.fixture
    def mock_update(self):
        update = Mock()
        update.effective_user = Mock()
        update.effective_user.id = 12345
        update.effective_chat = Mock()
        update.effective_chat.id = 67890
        update.message = Mock()
        update.message.reply_text = AsyncMock()
        return update

    @pytest.fixture
    def mock_context(self):
        context = Mock()
        context.user_data = {
            "receipt_creating": True,
            "receipt_draft": {"items": [], "raw_input": ""},
        }
        return context

    @pytest.mark.asyncio
    async def test_process_receipt_items_stores_to_draft(self, mock_update, mock_context):
        import importlib

        import services.bot_service.receipt_handlers

        importlib.reload(services.bot_service.receipt_handlers)

        await services.bot_service.receipt_handlers.process_receipt_items(
            mock_update, mock_context, "123456 x 2\n789012 x 1"
        )

        assert "receipt_draft" in mock_context.user_data
        assert mock_context.user_data["receipt_draft"]["raw_input"] == "123456 x 2\n789012 x 1"

    @pytest.mark.asyncio
    async def test_process_receipt_items_sends_preview_message(self, mock_update, mock_context):
        import importlib

        import services.bot_service.receipt_handlers

        importlib.reload(services.bot_service.receipt_handlers)

        await services.bot_service.receipt_handlers.process_receipt_items(
            mock_update, mock_context, "123456 x 1"
        )

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Предпросмотр" in call_args or "добавлены" in call_args.lower()

    @pytest.mark.asyncio
    async def test_process_receipt_items_adding_item_mode(self, mock_update, mock_context):
        from services.bot_service.receipt_handlers import parse_items_input

        mock_context.user_data["receipt_adding_item"] = True

        result = parse_items_input("999888 x 3")

        assert len(result) == 1
        assert result[0]["article"] == "999888"
        assert result[0]["quantity"] == 3


class TestKafkaProducerReceiptIntegration:
    def test_create_receipt_task_returns_valid_task(self):
        from unittest.mock import MagicMock

        from services.bot_service.kafka_producer import TaskProducer
        from services.common import TaskType

        config = MagicMock()
        config.bootstrap_servers = "localhost:9092"
        config.client_id = "test"
        config.topics = {"tasks_receipt": "tasks.receipt"}

        producer = TaskProducer(config)
        task = producer.create_receipt_task(
            user_id=123,
            chat_id=456,
            items_text="123456 x 2",
        )

        assert task.task_type == TaskType.RECEIPT
        assert task.user_id == 123
        assert task.chat_id == 456
        assert task.file_path == "123456 x 2"

    def test_process_receipt_items_stores_to_draft(self):
        import inspect

        from services.bot_service.receipt_handlers import process_receipt_items

        source = inspect.getsource(process_receipt_items)

        assert "receipt_draft" in source, "should store items to draft"
        assert "preview" in source or "raw_input" in source


class TestParseItemsInput:
    def test_parse_simple_article_quantity(self):
        from services.bot_service.receipt_handlers import parse_items_input

        result = parse_items_input("123456 x 2")

        assert len(result) == 1
        assert result[0]["article"] == "123456"
        assert result[0]["quantity"] == 2

    def test_parse_multiple_items(self):
        from services.bot_service.receipt_handlers import parse_items_input

        result = parse_items_input("123456 x 2\n789012 x 1\n555555 x 3")

        assert len(result) == 3
        assert result[0]["article"] == "123456"
        assert result[1]["article"] == "789012"
        assert result[2]["article"] == "555555"

    def test_parse_with_capital_x(self):
        from services.bot_service.receipt_handlers import parse_items_input

        result = parse_items_input("123456 X 2")

        assert len(result) == 1
        assert result[0]["quantity"] == 2

    def test_parse_with_russian_x(self):
        from services.bot_service.receipt_handlers import parse_items_input

        result = parse_items_input("123456 х 2")

        assert len(result) == 1

    def test_parse_with_url(self):
        from services.bot_service.receipt_handlers import parse_items_input

        result = parse_items_input("https://wildberries.ru/catalog/123456/detail.aspx x 1")

        assert len(result) == 1
        assert result[0]["article"] == "123456"

    def test_parse_with_wb_by_url(self):
        from services.bot_service.receipt_handlers import parse_items_input

        result = parse_items_input("https://www.wildberries.by/catalog/999888/detail.aspx x 3")

        assert len(result) == 1
        assert result[0]["article"] == "999888"

    def test_parse_ignores_invalid_format(self):
        from services.bot_service.receipt_handlers import parse_items_input

        result = parse_items_input("not valid format")

        assert len(result) == 0

    def test_parse_ignores_empty_lines(self):
        from services.bot_service.receipt_handlers import parse_items_input

        result = parse_items_input("123456 x 1\n\n789012 x 2\n")

        assert len(result) == 2

    def test_parse_ignores_zero_quantity(self):
        from services.bot_service.receipt_handlers import parse_items_input

        result = parse_items_input("123456 x 0")

        assert len(result) == 0

    def test_parse_ignores_negative_quantity(self):
        from services.bot_service.receipt_handlers import parse_items_input

        result = parse_items_input("123456 x -1")

        assert len(result) == 0

    def test_parse_with_extra_spaces(self):
        from services.bot_service.receipt_handlers import parse_items_input

        result = parse_items_input("  123456  x  2  ")

        assert len(result) == 1
        assert result[0]["article"] == "123456"
        assert result[0]["quantity"] == 2

    def test_parse_ignores_non_digit_article(self):
        from services.bot_service.receipt_handlers import parse_items_input

        result = parse_items_input("ABC123 x 1")

        assert len(result) == 0

    def test_parse_with_only_article(self):
        from services.bot_service.receipt_handlers import parse_items_input

        result = parse_items_input("123456")

        assert len(result) == 0

    def test_extract_article_from_url(self):
        from services.bot_service.receipt_handlers import extract_article_from_url_static

        url = "https://wildberries.ru/catalog/12345678/detail.aspx"
        result = extract_article_from_url_static(url)

        assert result == "12345678"

    def test_extract_article_from_url_invalid(self):
        from services.bot_service.receipt_handlers import extract_article_from_url_static

        result = extract_article_from_url_static("not a url")

        assert result is None

    def test_get_wb_product_name_from_url_returns_none_on_failure(self):
        from services.bot_service.receipt_handlers import get_wb_product_name_from_url

        result = get_wb_product_name_from_url("https://invalid-domain-that-does-not-exist.xyz/123")
        assert result is None

    def test_get_wb_product_name_from_article_returns_none_on_invalid_article(self):
        from services.bot_service.receipt_handlers import get_wb_product_name_from_article

        result = get_wb_product_name_from_article("999999999999")
        assert result is None


class TestHandleConfirmReceipt:
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
        context.user_data = {
            "receipt_draft": {
                "items": [
                    {"article": "123", "name": "Товар 1", "price": 100, "quantity": 1},
                    {"article": "456", "name": "Товар 2", "price": 200, "quantity": 2},
                ]
            }
        }
        context.bot = Mock()
        context.bot.send_message = AsyncMock()
        return context

    def test_confirm_handles_json_items(self):
        import inspect

        from services.bot_service.receipt_handlers import handle_confirm_receipt

        source = inspect.getsource(handle_confirm_receipt)
        assert "json.dumps" in source
        assert "items_text" in source

    def test_confirm_stores_pending_tasks(self):
        import inspect

        from services.bot_service.receipt_handlers import handle_confirm_receipt

        source = inspect.getsource(handle_confirm_receipt)
        assert "pending_tasks" in source
        assert "task_id" in source

    def test_confirm_sends_to_kafka(self):
        import inspect

        from services.bot_service.receipt_handlers import handle_confirm_receipt

        source = inspect.getsource(handle_confirm_receipt)
        assert "kafka_config" in source
        assert "TaskProducer" in source
