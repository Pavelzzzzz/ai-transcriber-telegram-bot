from unittest.mock import AsyncMock, Mock, patch

import pytest


class TestSettingsCallbackRouting:
    """Tests for settings_callback routing logic"""

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

    @pytest.mark.asyncio
    async def test_settings_callback_routes_to_model_selection(self, mock_update, mock_query):
        """Test that settings_callback routes to show_model_selection for settings:model"""
        from services.bot_service.settings_handlers import settings_callback

        mock_update.callback_query.data = "settings:model"

        with patch(
            "services.bot_service.settings_handlers.show_model_selection", new_callable=AsyncMock
        ) as mock_show:
            await settings_callback(mock_update, Mock())

        mock_show.assert_called_once_with(mock_query, 12345)

    @pytest.mark.asyncio
    async def test_settings_callback_routes_to_style_selection(self, mock_update, mock_query):
        """Test that settings_callback routes to show_style_selection for settings:style"""
        from services.bot_service.settings_handlers import settings_callback

        mock_update.callback_query.data = "settings:style"

        with patch(
            "services.bot_service.settings_handlers.show_style_selection", new_callable=AsyncMock
        ) as mock_show:
            await settings_callback(mock_update, Mock())

        mock_show.assert_called_once_with(mock_query, 12345)

    @pytest.mark.asyncio
    async def test_settings_callback_routes_to_aspect_selection(self, mock_update, mock_query):
        """Test that settings_callback routes to show_aspect_selection for settings:aspect"""
        from services.bot_service.settings_handlers import settings_callback

        mock_update.callback_query.data = "settings:aspect"

        with patch(
            "services.bot_service.settings_handlers.show_aspect_selection", new_callable=AsyncMock
        ) as mock_show:
            await settings_callback(mock_update, Mock())

        mock_show.assert_called_once_with(mock_query, 12345)

    @pytest.mark.asyncio
    async def test_settings_callback_routes_to_variations_selection(self, mock_update, mock_query):
        """Test that settings_callback routes to show_variations_selection for settings:variations"""
        from services.bot_service.settings_handlers import settings_callback

        mock_update.callback_query.data = "settings:variations"

        with patch(
            "services.bot_service.settings_handlers.show_variations_selection",
            new_callable=AsyncMock,
        ) as mock_show:
            await settings_callback(mock_update, Mock())

        mock_show.assert_called_once_with(mock_query, 12345)

    @pytest.mark.asyncio
    async def test_settings_callback_routes_to_negative_prompt(self, mock_update, mock_query):
        """Test that settings_callback routes to ask_negative_prompt for settings:negative"""
        from services.bot_service.settings_handlers import settings_callback

        mock_update.callback_query.data = "settings:negative"

        with patch(
            "services.bot_service.settings_handlers.ask_negative_prompt", new_callable=AsyncMock
        ) as mock_ask:
            await settings_callback(mock_update, Mock())

        mock_ask.assert_called_once_with(mock_query, 12345)

    @pytest.mark.asyncio
    async def test_settings_callback_handles_back(self, mock_update, mock_query):
        """Test that settings_callback handles settings:back"""
        from services.bot_service.settings_handlers import settings_callback

        mock_update.callback_query.data = "settings:back"

        await settings_callback(mock_update, Mock())

        mock_query.edit_message_text.assert_called_once()
        assert "сохранены" in mock_query.edit_message_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_settings_callback_handles_reset(self, mock_update, mock_query):
        """Test that settings_callback handles settings:reset"""
        from services.bot_service.settings_handlers import settings_callback

        mock_update.callback_query.data = "settings:reset"

        with patch("services.bot_service.settings_handlers.reset_user_settings"):
            await settings_callback(mock_update, Mock())

        mock_query.edit_message_text.assert_called_once()
        assert "сброшены" in mock_query.edit_message_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_settings_callback_routes_to_noise_toggle(self, mock_update, mock_query):
        """Test that settings_callback routes to handle_settings_noise_callback for settings:noise"""
        from services.bot_service.settings_handlers import settings_callback

        mock_update.callback_query.data = "settings:noise"

        with patch(
            "services.bot_service.settings_handlers.handle_settings_noise_callback",
            new_callable=AsyncMock,
        ) as mock_handler:
            await settings_callback(mock_update, Mock())

        mock_handler.assert_called_once_with(mock_query, 12345)


class TestSettingsSubHandlerPatterns:
    """Tests that sub-handlers correctly process their specific patterns"""

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

    @pytest.mark.asyncio
    async def test_model_subhandler_processes_model_choice(self, mock_update, mock_query):
        """Test that model sub-handler processes settings:model:sdxl"""
        from services.bot_service.settings_handlers import handle_settings_model_callback

        mock_update.callback_query.data = "settings:model:sdxl"

        with patch(
            "services.bot_service.settings_handlers.get_available_models",
            return_value=["sd15", "sdxl"],
        ):
            with patch("services.bot_service.settings_handlers.update_user_settings"):
                await handle_settings_model_callback(mock_update, Mock())

        mock_query.edit_message_text.assert_called_once()
        assert "Модель изменена" in mock_query.edit_message_text.call_args[0][0]
        assert "Stable Diffusion XL" in mock_query.edit_message_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_style_subhandler_processes_style_choice(self, mock_update, mock_query):
        """Test that style sub-handler processes settings:style:anime"""
        from services.bot_service.settings_handlers import handle_settings_style_callback

        mock_update.callback_query.data = "settings:style:anime"

        with patch("services.bot_service.settings_handlers.update_user_settings"):
            await handle_settings_style_callback(mock_update, Mock())

        mock_query.edit_message_text.assert_called_once()
        assert "Стиль изменен" in mock_query.edit_message_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_aspect_subhandler_processes_aspect_choice(self, mock_update, mock_query):
        """Test that aspect sub-handler processes settings:aspect:16:9"""
        from services.bot_service.settings_handlers import handle_settings_aspect_callback

        mock_update.callback_query.data = "settings:aspect:16:9"

        with patch("services.bot_service.settings_handlers.update_user_settings"):
            await handle_settings_aspect_callback(mock_update, Mock())

        mock_query.edit_message_text.assert_called_once()
        assert "Соотношение сторон изменено" in mock_query.edit_message_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_variations_subhandler_processes_variations_choice(self, mock_update, mock_query):
        """Test that variations sub-handler processes settings:variations:2"""
        from services.bot_service.settings_handlers import handle_settings_variations_callback

        mock_update.callback_query.data = "settings:variations:2"

        with patch("services.bot_service.settings_handlers.update_user_settings"):
            await handle_settings_variations_callback(mock_update, Mock())

        mock_query.edit_message_text.assert_called_once()
        assert "Количество вариаций изменено" in mock_query.edit_message_text.call_args[0][0]


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


class TestNoiseReductionSettings:
    """Tests for noise reduction toggle functionality"""

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

    @pytest.fixture
    def mock_settings(self):
        settings = Mock()
        settings.noise_reduction = True
        return settings

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_noise_callback_toggles_on_to_off(self, mock_update, mock_query, mock_settings):
        """Test that noise reduction toggles from ON to OFF"""
        from services.bot_service.settings_handlers import handle_settings_noise_callback

        mock_update.callback_query.data = "settings:noise"

        with patch(
            "services.bot_service.settings_handlers.get_or_create_user_settings",
            return_value=mock_settings,
        ):
            with patch("services.bot_service.settings_handlers.update_user_settings"):
                await handle_settings_noise_callback(mock_update, Mock())

        mock_query.edit_message_text.assert_called_once()
        call_args = mock_query.edit_message_text.call_args[0][0]
        assert "Выключено" in call_args
        assert "пропускаться" in call_args

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_noise_callback_toggles_off_to_on(self, mock_update, mock_query):
        """Test that noise reduction toggles from OFF to ON"""
        from services.bot_service.settings_handlers import handle_settings_noise_callback

        mock_update.callback_query.data = "settings:noise"

        mock_settings = Mock()
        mock_settings.noise_reduction = False

        with patch(
            "services.bot_service.settings_handlers.get_or_create_user_settings",
            return_value=mock_settings,
        ):
            with patch(
                "services.bot_service.settings_handlers.update_user_settings"
            ) as mock_update_settings:
                await handle_settings_noise_callback(mock_update, Mock())

        mock_query.edit_message_text.assert_called_once()
        call_args = mock_query.edit_message_text.call_args[0][0]
        assert "Включено" in call_args
        assert "применяться" in call_args
        mock_update_settings.assert_called_once_with(12345, noise_reduction=True)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_noise_callback_handles_db_error(self, mock_update, mock_query):
        """Test that noise callback handles database errors gracefully"""
        from services.bot_service.settings_handlers import handle_settings_noise_callback

        mock_update.callback_query.data = "settings:noise"

        with patch(
            "services.bot_service.settings_handlers.get_or_create_user_settings",
            side_effect=Exception("DB Error"),
        ):
            await handle_settings_noise_callback(mock_update, Mock())

        mock_query.edit_message_text.assert_called_once()
        call_args = mock_query.edit_message_text.call_args[0][0]
        assert "❌" in call_args or "Не удалось" in call_args
