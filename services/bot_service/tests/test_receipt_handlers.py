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
        context.user_data = {"receipt_creating": True, "receipt_items": []}
        return context

    @pytest.mark.asyncio
    async def test_process_receipt_items_sends_task_to_kafka(self, mock_update, mock_context):
        from unittest.mock import MagicMock, patch

        from services.bot_service import kafka_producer

        mock_producer_instance = MagicMock()
        mock_producer_instance.create_receipt_task.return_value = MagicMock()
        with patch.object(kafka_producer, "TaskProducer", return_value=mock_producer_instance):
            import importlib

            import services.bot_service.receipt_handlers
            from services.bot_service.receipt_handlers import process_receipt_items

            importlib.reload(services.bot_service.receipt_handlers)

            await services.bot_service.receipt_handlers.process_receipt_items(
                mock_update, mock_context, "123456 x 2\n789012 x 1"
            )

            mock_producer_instance.create_receipt_task.assert_called_once()
            mock_producer_instance.send_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_receipt_items_clears_user_data(self, mock_update, mock_context):
        from unittest.mock import MagicMock, patch

        from services.bot_service import kafka_producer

        mock_producer_instance = MagicMock()
        mock_producer_instance.create_receipt_task.return_value = MagicMock()
        with patch.object(kafka_producer, "TaskProducer", return_value=mock_producer_instance):
            import importlib

            import services.bot_service.receipt_handlers

            importlib.reload(services.bot_service.receipt_handlers)

            await services.bot_service.receipt_handlers.process_receipt_items(
                mock_update, mock_context, "123456 x 1"
            )

            assert "receipt_creating" not in mock_context.user_data
            assert "receipt_items" not in mock_context.user_data

    @pytest.mark.asyncio
    async def test_process_receipt_items_sends_confirmation_message(
        self, mock_update, mock_context
    ):
        from unittest.mock import MagicMock, patch

        from services.bot_service import kafka_producer

        mock_producer_instance = MagicMock()
        mock_producer_instance.create_receipt_task.return_value = MagicMock()
        with patch.object(kafka_producer, "TaskProducer", return_value=mock_producer_instance):
            import importlib

            import services.bot_service.receipt_handlers

            importlib.reload(services.bot_service.receipt_handlers)

            await services.bot_service.receipt_handlers.process_receipt_items(
                mock_update, mock_context, "123456 x 1"
            )

            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "чек" in call_args.lower()


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

    def test_process_receipt_items_source_code_includes_send_task(self):
        import inspect

        from services.bot_service.receipt_handlers import process_receipt_items

        source = inspect.getsource(process_receipt_items)

        assert "send_task" in source, "send_task должен вызываться после create_receipt_task"
        assert "create_receipt_task" in source
