import asyncio
import os
import sys
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
)

from services.common.schemas import ResultMessage, TaskMessage, TaskStatus, TaskType


@pytest.fixture
def mock_env_token():
    with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test_token_123"}):
        yield


class TestTextToImageHandler:
    """Test text_to_image handler in bot service"""

    @pytest.fixture
    def mock_update(self):
        update = Mock()
        update.effective_user = Mock()
        update.effective_user.id = 12345
        update.effective_chat = Mock()
        update.effective_chat.id = 67890
        update.message = Mock()
        update.message.message_id = 111
        update.message.text = "A beautiful sunset over the ocean"
        update.message.reply_text = AsyncMock()
        return update

    @pytest.fixture
    def mock_context(self):
        context = Mock()
        context.user_data = {}
        return context

    @pytest.fixture
    def mock_producer(self):
        producer = Mock()
        producer.create_image_gen_task = Mock(
            return_value=TaskMessage(
                task_id="test-task-123",
                task_type=TaskType.IMAGE_GEN,
                user_id=12345,
                chat_id=67890,
                timestamp=datetime.now(),
                file_path="A beautiful sunset over the ocean",
                metadata={"message_id": 111},
            )
        )
        producer.send_task = Mock()
        return producer

    @pytest.mark.asyncio
    async def test_text_to_image_handler_calls_producer(
        self, mock_update, mock_context, mock_producer
    ):
        """Test that text_to_image handler creates and sends task to Kafka"""
        with patch("services.bot_service.main.get_or_create_user_settings") as mock_settings:
            mock_settings.return_value = Mock(
                image_model="sd15",
                image_style="",
                aspect_ratio="1:1",
                num_variations=1,
                negative_prompt="",
            )

            from services.bot_service.main import SimpleSafeProcessor

            processor = SimpleSafeProcessor()

            result = await processor.safe_reply(mock_update, "test message")
            assert result is True
            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            assert call_args[0][0] == "test message"

    @pytest.mark.asyncio
    async def test_text_message_handler_text_to_image_mode(
        self, mock_update, mock_context, mock_producer, mock_env_token
    ):
        """Test that text_message_handler routes to text_to_image when mode is set"""
        from services.bot_service.main import TelegramBotService

        bot = TelegramBotService()
        bot.user_modes[12345] = "text_to_image"
        bot.producer = mock_producer
        bot.pending_tasks = {}
        bot.chat_id_to_user_id = {}

        with patch("services.bot_service.main.get_or_create_user_settings") as mock_settings:
            mock_settings.return_value = Mock(
                image_model="sd15",
                image_style="",
                aspect_ratio="1:1",
                num_variations=1,
                negative_prompt="",
            )

            await bot.text_message_handler(mock_update, mock_context)

            mock_producer.create_image_gen_task.assert_called_once()
            call_args = mock_producer.create_image_gen_task.call_args
            assert call_args[1]["prompt"] == "A beautiful sunset over the ocean"
            assert call_args[1]["user_id"] == 12345
            assert call_args[1]["chat_id"] == 67890

            mock_producer.send_task.assert_called_once()
            assert "test-task-123" in bot.pending_tasks
            assert bot.pending_tasks["test-task-123"]["task_type"] == "image_gen"

    @pytest.mark.asyncio
    async def test_text_message_handler_default_mode_ignores_text(
        self, mock_update, mock_context, mock_env_token
    ):
        """Test that text_message_handler ignores text in img_to_text mode (default)"""
        from services.bot_service.main import TelegramBotService

        bot = TelegramBotService()
        bot.user_modes[12345] = "img_to_text"  # default mode
        bot.pending_tasks = {}
        bot.chat_id_to_user_id = {}

        await bot.text_message_handler(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        reply_text = mock_update.message.reply_text.call_args[0][0]
        assert "Отправьте фото или голос" in reply_text

    @pytest.mark.asyncio
    async def test_text_to_image_sends_correct_metadata(
        self, mock_update, mock_context, mock_producer, mock_env_token
    ):
        """Test that text_to_image sends correct metadata to Kafka"""
        from services.bot_service.main import TelegramBotService

        bot = TelegramBotService()
        bot.user_modes[12345] = "text_to_image"
        bot.producer = mock_producer
        bot.pending_tasks = {}
        bot.chat_id_to_user_id = {}

        with patch("services.bot_service.main.get_or_create_user_settings") as mock_settings:
            mock_settings.return_value = Mock(
                image_model="sdxl",
                image_style="photorealistic",
                aspect_ratio="16:9",
                num_variations=2,
                negative_prompt="blurry",
            )

            await bot.text_message_handler(mock_update, mock_context)

            call_args = mock_producer.create_image_gen_task.call_args
            metadata = call_args[1]
            assert metadata["prompt"] == "A beautiful sunset over the ocean"


class TestResultConsumer:
    """Test result consumer for image generation"""

    def test_handle_result_image_gen(self, mock_env_token, tmp_path):
        """Test that handle_result correctly handles image generation results"""
        from services.bot_service.main import TelegramBotService

        bot = TelegramBotService()
        bot.pending_tasks = {
            "test-task-123": {
                "chat_id": 67890,
                "task_type": "image_gen",
            }
        }

        mock_bot = Mock()
        bot.application = Mock()
        bot.application.bot = mock_bot
        bot._async_loop = asyncio.new_event_loop()

        test_image = tmp_path / "test_image.png"
        test_image.write_bytes(b"fake png data")

        result = ResultMessage(
            task_id="test-task-123",
            status=TaskStatus.SUCCESS,
            result_type="image",
            result_data={
                "file_path": str(test_image),
                "prompt": "A beautiful sunset",
            },
        )

        with patch.object(bot, "_get_async_loop", return_value=bot._async_loop):
            bot.handle_result(result)

        mock_bot.send_photo.assert_called_once()
        call_kwargs = mock_bot.send_photo.call_args[1]
        assert call_kwargs["chat_id"] == 67890
        assert "caption" in call_kwargs

    def test_handle_result_removes_pending_task(self, mock_env_token):
        """Test that handle_result removes task from pending_tasks after processing"""
        from services.bot_service.main import TelegramBotService

        bot = TelegramBotService()
        bot.pending_tasks = {
            "test-task-123": {
                "chat_id": 67890,
                "task_type": "image_gen",
            }
        }

        mock_bot = Mock()
        bot.application = Mock()
        bot.application.bot = mock_bot
        bot._async_loop = asyncio.new_event_loop()

        result = ResultMessage(
            task_id="test-task-123",
            status=TaskStatus.SUCCESS,
            result_type="image",
            result_data={
                "file_path": "/tmp/test_image.png",
            },
        )

        with patch.object(bot, "_get_async_loop", return_value=bot._async_loop):
            bot.handle_result(result)

        assert "test-task-123" not in bot.pending_tasks

    def test_handle_result_unknown_task_logs_warning(self, mock_env_token):
        """Test that handle_result handles unknown task gracefully"""
        from services.bot_service.main import TelegramBotService

        bot = TelegramBotService()
        bot.pending_tasks = {}  # No pending task
        bot.application = None

        result = ResultMessage(
            task_id="unknown-task",
            status=TaskStatus.SUCCESS,
            result_type="image",
            result_data={},
        )

        bot.handle_result(result)  # Should not raise


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
