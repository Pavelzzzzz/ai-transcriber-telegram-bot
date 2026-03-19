import os
import sys
from unittest.mock import AsyncMock, Mock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestSettingsHandlers:
    """Test settings handlers functions"""

    @patch("services.bot_service.settings_handlers.get_available_models")
    @patch("services.bot_service.settings_handlers.get_or_create_user_settings")
    def test_get_settings_keyboard(self, mock_get_settings, mock_get_models):
        mock_settings = Mock()
        mock_settings.image_model = "sdxl"
        mock_settings.image_style = "photorealistic"
        mock_settings.aspect_ratio = "1:1"
        mock_settings.num_variations = 2
        mock_settings.negative_prompt = "blurry"
        mock_get_settings.return_value = mock_settings
        mock_get_models.return_value = ["sd15", "sdxl"]

        from services.bot_service.settings_handlers import get_settings_keyboard

        keyboard = get_settings_keyboard(12345)

        assert keyboard is not None
        assert hasattr(keyboard, "keyboard")

    @patch(
        "services.bot_service.settings_handlers.MODELS_CONFIG",
        {
            "sd15": {"name": "SD 1.5", "min_vram_gb": 0},
            "sdxl": {"name": "SDXL", "min_vram_gb": 8},
            "flux": {"name": "FLUX", "min_vram_gb": 16},
        },
    )
    @patch("services.bot_service.settings_handlers.get_available_models")
    @patch("services.bot_service.settings_handlers.get_or_create_user_settings")
    @patch("services.bot_service.settings_handlers.get_model_display_name")
    def test_get_settings_keyboard_content(self, mock_display, mock_get_settings, mock_get_models):
        mock_settings = Mock()
        mock_settings.image_model = "sdxl"
        mock_settings.image_style = ""
        mock_settings.aspect_ratio = "1:1"
        mock_settings.num_variations = 1
        mock_settings.negative_prompt = None
        mock_get_settings.return_value = mock_settings
        mock_get_models.return_value = ["sd15", "sdxl"]
        mock_display.return_value = "SDXL"

        from services.bot_service.settings_handlers import get_settings_keyboard

        keyboard = get_settings_keyboard(12345)

        keyboard_data = keyboard.to_dict()
        assert "inline_keyboard" in keyboard_data


class TestSettingsCallbacks:
    """Test settings callback handlers"""

    @pytest.mark.asyncio
    @patch("services.bot_service.settings_handlers.update_user_settings")
    async def test_handle_settings_model_callback(self, mock_update):
        from services.bot_service.settings_handlers import handle_settings_model_callback

        query = Mock()
        query.data = "settings:model:sdxl"
        query.edit_message_text = AsyncMock()

        update = Mock()
        update.callback_query = query
        update.effective_user = Mock()
        update.effective_user.id = 12345

        context = Mock()

        await handle_settings_model_callback(update, context)

        mock_update.assert_called_once_with(12345, image_model="sdxl")

    @pytest.mark.asyncio
    @patch("services.bot_service.settings_handlers.update_user_settings")
    async def test_handle_settings_style_callback(self, mock_update):
        from services.bot_service.settings_handlers import handle_settings_style_callback

        query = Mock()
        query.data = "settings:style:photorealistic"
        query.edit_message_text = AsyncMock()

        update = Mock()
        update.callback_query = query
        update.effective_user = Mock()
        update.effective_user.id = 12345

        context = Mock()

        await handle_settings_style_callback(update, context)

        mock_update.assert_called_once_with(12345, image_style="photorealistic")

    @pytest.mark.asyncio
    @patch("services.bot_service.settings_handlers.update_user_settings")
    async def test_handle_settings_aspect_callback(self, mock_update):
        from services.bot_service.settings_handlers import handle_settings_aspect_callback

        query = Mock()
        query.data = "settings:aspect:16:9"
        query.edit_message_text = AsyncMock()

        update = Mock()
        update.callback_query = query
        update.effective_user = Mock()
        update.effective_user.id = 12345

        context = Mock()

        await handle_settings_aspect_callback(update, context)

        mock_update.assert_called_once_with(12345, aspect_ratio="16:9")

    @pytest.mark.asyncio
    @patch("services.bot_service.settings_handlers.update_user_settings")
    async def test_handle_settings_variations_callback(self, mock_update):
        from services.bot_service.settings_handlers import handle_settings_variations_callback

        query = Mock()
        query.data = "settings:variations:3"
        query.edit_message_text = AsyncMock()

        update = Mock()
        update.callback_query = query
        update.effective_user = Mock()
        update.effective_user.id = 12345

        context = Mock()

        await handle_settings_variations_callback(update, context)

        mock_update.assert_called_once_with(12345, num_variations=3)


class TestNegativePromptHandlers:
    """Test negative prompt input handlers"""

    @pytest.mark.asyncio
    @patch("services.bot_service.settings_handlers.update_user_settings")
    async def test_handle_negative_prompt_input_skip(self, mock_update):
        from services.bot_service.settings_handlers import (
            PENDING_NEGATIVE_PROMPT,
            handle_negative_prompt_input,
        )

        PENDING_NEGATIVE_PROMPT[12345] = True

        update = Mock()
        update.message = Mock()
        update.message.text = "/skip"
        update.message.reply_text = AsyncMock()

        context = Mock()

        result = await handle_negative_prompt_input(update, context, 12345)

        assert result is True
        mock_update.assert_called_once_with(12345, negative_prompt="")
        assert 12345 not in PENDING_NEGATIVE_PROMPT

    @pytest.mark.asyncio
    @patch("services.bot_service.settings_handlers.update_user_settings")
    async def test_handle_negative_prompt_input_text(self, mock_update):
        from services.bot_service.settings_handlers import (
            PENDING_NEGATIVE_PROMPT,
            handle_negative_prompt_input,
        )

        PENDING_NEGATIVE_PROMPT[12345] = True

        update = Mock()
        update.message = Mock()
        update.message.text = "blurry, ugly"
        update.message.reply_text = AsyncMock()

        context = Mock()

        result = await handle_negative_prompt_input(update, context, 12345)

        assert result is True
        mock_update.assert_called_once_with(12345, negative_prompt="blurry, ugly")
        assert 12345 not in PENDING_NEGATIVE_PROMPT

    @pytest.mark.asyncio
    async def test_handle_negative_prompt_input_not_pending(self):
        from services.bot_service.settings_handlers import handle_negative_prompt_input

        update = Mock()

        context = Mock()

        result = await handle_negative_prompt_input(update, context, 99999)

        assert result is False


class TestSettingsCallbackQuery:
    """Test main settings callback handler"""

    @pytest.mark.asyncio
    async def test_settings_callback_back(self):
        from services.bot_service.settings_handlers import settings_callback

        query = Mock()
        query.data = "settings:back"
        query.edit_message_text = AsyncMock()

        update = Mock()
        update.callback_query = query
        update.effective_user = Mock()

        await settings_callback(update, Mock())

        query.edit_message_text.assert_called_once()

    @pytest.mark.asyncio
    @patch("services.bot_service.settings_handlers.reset_user_settings")
    async def test_settings_callback_reset(self, mock_reset):
        from services.bot_service.settings_handlers import (
            PENDING_NEGATIVE_PROMPT,
            settings_callback,
        )

        PENDING_NEGATIVE_PROMPT[12345] = True

        query = Mock()
        query.data = "settings:reset"
        query.edit_message_text = AsyncMock()

        update = Mock()
        update.callback_query = query
        update.effective_user = Mock()
        update.effective_user.id = 12345

        await settings_callback(update, Mock())

        mock_reset.assert_called_once()
        assert 12345 not in PENDING_NEGATIVE_PROMPT

    @pytest.mark.asyncio
    @patch("services.bot_service.settings_handlers.show_model_selection")
    async def test_settings_callback_model(self, mock_show):
        from services.bot_service.settings_handlers import settings_callback

        query = Mock()
        query.data = "settings:model"
        query.edit_message_text = AsyncMock()

        update = Mock()
        update.callback_query = query
        update.effective_user = Mock()
        update.effective_user.id = 12345

        await settings_callback(update, Mock())

        mock_show.assert_called_once()

    @pytest.mark.asyncio
    @patch("services.bot_service.settings_handlers.show_style_selection")
    async def test_settings_callback_style(self, mock_show):
        from services.bot_service.settings_handlers import settings_callback

        query = Mock()
        query.data = "settings:style"
        query.edit_message_text = AsyncMock()

        update = Mock()
        update.callback_query = query
        update.effective_user = Mock()

        await settings_callback(update, Mock())

        mock_show.assert_called_once()

    @pytest.mark.asyncio
    @patch("services.bot_service.settings_handlers.show_aspect_selection")
    async def test_settings_callback_aspect(self, mock_show):
        from services.bot_service.settings_handlers import settings_callback

        query = Mock()
        query.data = "settings:aspect"
        query.edit_message_text = AsyncMock()

        update = Mock()
        update.callback_query = query
        update.effective_user = Mock()

        await settings_callback(update, Mock())

        mock_show.assert_called_once()

    @pytest.mark.asyncio
    @patch("services.bot_service.settings_handlers.show_variations_selection")
    async def test_settings_callback_variations(self, mock_show):
        from services.bot_service.settings_handlers import settings_callback

        query = Mock()
        query.data = "settings:variations"
        query.edit_message_text = AsyncMock()

        update = Mock()
        update.callback_query = query
        update.effective_user = Mock()

        await settings_callback(update, Mock())

        mock_show.assert_called_once()

    @pytest.mark.asyncio
    @patch("services.bot_service.settings_handlers.ask_negative_prompt")
    async def test_settings_callback_negative(self, mock_ask):
        from services.bot_service.settings_handlers import settings_callback

        query = Mock()
        query.data = "settings:negative"
        query.edit_message_text = AsyncMock()

        update = Mock()
        update.callback_query = query
        update.effective_user = Mock()

        await settings_callback(update, Mock())

        mock_ask.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
