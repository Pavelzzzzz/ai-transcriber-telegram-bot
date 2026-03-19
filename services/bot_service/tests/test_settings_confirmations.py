from unittest.mock import AsyncMock, Mock, patch

import pytest


class TestSettingsHandlersConfirmations:
    """Tests that all settings handlers send confirmation messages to users"""

    @pytest.fixture
    def mock_query(self):
        query = AsyncMock()
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        return query

    @pytest.fixture
    def mock_update(self, mock_query):
        update = Mock()
        update.callback_query = mock_query
        update.effective_user.id = 12345
        return update

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_model_callback_sends_confirmation(self, mock_update, mock_query):
        """Test that model callback sends confirmation message"""
        from services.bot_service.settings_handlers import handle_settings_model_callback

        mock_update.callback_query.data = "settings:model:sdxl"

        with patch(
            "services.bot_service.settings_handlers.get_available_models",
            return_value=["sd15", "sdxl"],
        ):
            with patch("services.bot_service.settings_handlers.update_user_settings"):
                await handle_settings_model_callback(mock_update, None)

        mock_query.edit_message_text.assert_called_once()
        call_args = mock_query.edit_message_text.call_args[0][0]
        assert "Модель изменена" in call_args
        assert "Stable Diffusion XL" in call_args

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_style_callback_sends_confirmation(self, mock_update, mock_query):
        """Test that style callback sends confirmation message"""
        from services.bot_service.settings_handlers import handle_settings_style_callback

        mock_update.callback_query.data = "settings:style:photorealistic"

        with patch("services.bot_service.settings_handlers.update_user_settings"):
            await handle_settings_style_callback(mock_update, None)

        mock_query.edit_message_text.assert_called_once()
        call_args = mock_query.edit_message_text.call_args[0][0]
        assert "Стиль изменен" in call_args

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_aspect_callback_sends_confirmation(self, mock_update, mock_query):
        """Test that aspect callback sends confirmation message"""
        from services.bot_service.settings_handlers import handle_settings_aspect_callback

        mock_update.callback_query.data = "settings:aspect:16:9"

        with patch("services.bot_service.settings_handlers.update_user_settings"):
            await handle_settings_aspect_callback(mock_update, None)

        mock_query.edit_message_text.assert_called_once()
        call_args = mock_query.edit_message_text.call_args[0][0]
        assert "Соотношение сторон изменено" in call_args
        assert "9" in call_args

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_variations_callback_sends_confirmation(self, mock_update, mock_query):
        """Test that variations callback sends confirmation message"""
        from services.bot_service.settings_handlers import handle_settings_variations_callback

        mock_update.callback_query.data = "settings:variations:3"

        with patch("services.bot_service.settings_handlers.update_user_settings"):
            await handle_settings_variations_callback(mock_update, None)

        mock_query.edit_message_text.assert_called_once()
        call_args = mock_query.edit_message_text.call_args[0][0]
        assert "Количество вариаций изменено" in call_args
        assert "3" in call_args

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_model_callback_handles_unavailable_model(self, mock_update, mock_query):
        """Test that model callback handles unavailable model with warning"""
        from services.bot_service.settings_handlers import handle_settings_model_callback

        mock_update.callback_query.data = "settings:model:flux"

        with patch(
            "services.bot_service.settings_handlers.get_available_models", return_value=["sd15"]
        ):
            with patch("services.bot_service.settings_handlers.update_user_settings"):
                await handle_settings_model_callback(mock_update, None)

        mock_query.edit_message_text.assert_called_once()
        call_args = mock_query.edit_message_text.call_args[0][0]
        assert "⚠️" in call_args or "Внимание" in call_args

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_callback_handles_db_error(self, mock_update, mock_query):
        """Test that callbacks handle database errors gracefully"""
        from services.bot_service.settings_handlers import handle_settings_style_callback

        mock_update.callback_query.data = "settings:style:photorealistic"

        with patch(
            "services.bot_service.settings_handlers.update_user_settings",
            side_effect=Exception("DB Error"),
        ):
            await handle_settings_style_callback(mock_update, None)

        mock_query.edit_message_text.assert_called_once()
        call_args = mock_query.edit_message_text.call_args[0][0]
        assert "❌" in call_args or "Не удалось" in call_args

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_callback_ignores_wrong_data(self, mock_update, mock_query):
        """Test that callbacks ignore data that doesn't start with expected prefix"""
        from services.bot_service.settings_handlers import handle_settings_style_callback

        mock_update.callback_query.data = "wrong:data"

        await handle_settings_style_callback(mock_update, None)

        mock_query.edit_message_text.assert_not_called()
        mock_query.answer.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_callback_ignores_empty_query(self, mock_update, mock_query):
        """Test that callbacks ignore empty queries"""
        from services.bot_service.settings_handlers import handle_settings_style_callback

        mock_update.callback_query = None

        await handle_settings_style_callback(mock_update, None)

        mock_query.edit_message_text.assert_not_called()
