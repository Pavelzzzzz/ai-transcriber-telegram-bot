import os
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestUserSettingsModel:
    """Test UserSettings model structure"""

    def test_user_settings_attributes(self):
        from services.common.user_settings_repo import UserSettings

        settings = UserSettings(
            user_id=12345,
            image_model="sdxl",
            image_style="photorealistic",
            aspect_ratio="16:9",
            num_variations=2,
            negative_prompt="blurry",
        )

        assert settings.user_id == 12345
        assert settings.image_model == "sdxl"
        assert settings.image_style == "photorealistic"
        assert settings.aspect_ratio == "16:9"
        assert settings.num_variations == 2
        assert settings.negative_prompt == "blurry"

    def test_user_settings_defaults(self):
        from services.common.user_settings_repo import UserSettings

        settings = UserSettings(user_id=12345)

        assert settings.user_id == 12345
        assert settings.image_model is None
        assert settings.image_style is None
        assert settings.aspect_ratio is None
        assert settings.num_variations is None
        assert settings.negative_prompt is None

    def test_user_settings_to_dict(self):
        from services.common.user_settings_repo import UserSettings

        settings = UserSettings(
            user_id=12345,
            image_model="flux",
            image_style="anime",
            aspect_ratio="9:16",
            num_variations=4,
            negative_prompt="ugly",
        )

        result = settings.to_dict()

        assert result["user_id"] == 12345
        assert result["image_model"] == "flux"
        assert result["image_style"] == "anime"
        assert result["aspect_ratio"] == "9:16"
        assert result["num_variations"] == 4
        assert result["negative_prompt"] == "ugly"


class TestImageGenerationHistoryModel:
    """Test ImageGenerationHistory model structure"""

    def test_history_attributes(self):
        from services.common.user_settings_repo import ImageGenerationHistory

        history = ImageGenerationHistory(
            user_id=12345,
            prompt="A cat",
            model="sdxl",
            style="photorealistic",
            aspect_ratio="1:1",
            file_path="/path/to/image.png",
            status="success",
        )

        assert history.user_id == 12345
        assert history.prompt == "A cat"
        assert history.model == "sdxl"
        assert history.style == "photorealistic"
        assert history.aspect_ratio == "1:1"
        assert history.file_path == "/path/to/image.png"
        assert history.status == "success"

    def test_history_default_status(self):
        from services.common.user_settings_repo import ImageGenerationHistory

        history = ImageGenerationHistory(user_id=12345, prompt="A dog", model="flux")

        assert history.status is None
        assert history.error_message is None


class TestUserSettingsRepoSimple:
    """Test user settings repository functions - simple tests"""

    @patch("services.common.user_settings_repo.get_db")
    def test_get_user_settings_found(self, mock_get_db):
        mock_db = MagicMock()
        mock_settings = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_settings

        mock_ctx = MagicMock()
        mock_ctx.__enter__ = Mock(return_value=mock_db)
        mock_ctx.__exit__ = Mock(return_value=False)
        mock_get_db.return_value = mock_ctx

        from services.common.user_settings_repo import get_user_settings

        result = get_user_settings(12345)

        assert result == mock_settings

    @patch("services.common.user_settings_repo.get_db")
    def test_get_user_settings_not_found(self, mock_get_db):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        mock_ctx = MagicMock()
        mock_ctx.__enter__ = Mock(return_value=mock_db)
        mock_ctx.__exit__ = Mock(return_value=False)
        mock_get_db.return_value = mock_ctx

        from services.common.user_settings_repo import get_user_settings

        result = get_user_settings(99999)

        assert result is None

    @patch("services.common.user_settings_repo.get_db")
    def test_get_or_create_user_settings_new(self, mock_get_db):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        mock_ctx = MagicMock()
        mock_ctx.__enter__ = Mock(return_value=mock_db)
        mock_ctx.__exit__ = Mock(return_value=False)
        mock_get_db.return_value = mock_ctx

        from services.common.user_settings_repo import UserSettings, get_or_create_user_settings

        result = get_or_create_user_settings(12345)

        assert isinstance(result, UserSettings)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
