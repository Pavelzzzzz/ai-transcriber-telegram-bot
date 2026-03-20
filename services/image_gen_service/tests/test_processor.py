import os
import sys
from unittest.mock import Mock, patch

import pytest

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
)

from services.image_gen_service.processor import ImageGenerationProcessor


class TestImageGenerationProcessor:
    @pytest.fixture
    def processor(self):
        return ImageGenerationProcessor()

    def test_init(self, processor):
        assert processor is not None
        assert processor._pipelines == {}
        assert processor._current_model is None

    def test_validate_prompt_success(self, processor):
        result = processor._validate_prompt("A beautiful sunset")
        assert result is True

    def test_validate_prompt_too_short(self, processor):
        with pytest.raises(ValueError, match="Prompt must be at least 3 characters"):
            processor._validate_prompt("ab")

    def test_validate_prompt_empty(self, processor):
        with pytest.raises(ValueError, match="Prompt must be at least 3 characters"):
            processor._validate_prompt("")

    def test_validate_prompt_whitespace_only(self, processor):
        with pytest.raises(ValueError, match="Prompt must be at least 3 characters"):
            processor._validate_prompt("   ")

    @pytest.mark.asyncio
    async def test_generate_image_validation_error(self, processor):
        with pytest.raises(ValueError):
            await processor.generate_image("ab")

    def test_clear_cache(self, processor):
        processor._pipelines = {"test": Mock()}
        processor._current_model = "test"

        processor.clear_cache()

        assert processor._pipelines == {}
        assert processor._current_model is None


class TestImageGenerationProcessorConfig:
    """Test processor configuration constants"""

    def test_max_retries(self):
        assert ImageGenerationProcessor.MAX_RETRIES == 3

    def test_retry_delay(self):
        assert ImageGenerationProcessor.RETRY_DELAY == 2


class TestStyleModelOverride:
    """Test that style configuration works correctly"""

    def test_style_config_has_model_id(self):
        """Test that style config includes model_id for overriding default model"""
        from services.common.hardware import STYLES_CONFIG

        assert STYLES_CONFIG["photorealistic"]["model_id"] == "SG161222/Realistic_Vision_V5.1_noVAE"
        assert STYLES_CONFIG["anime"]["model_id"] == "cagliostrolab/animagine-xl-3.1"

    def test_style_config_has_negative_prompt(self):
        """Test that style config includes negative_prompt"""
        from services.common.hardware import STYLES_CONFIG

        assert "negative_prompt" in STYLES_CONFIG["photorealistic"]
        assert "negative_prompt" in STYLES_CONFIG["anime"]
        assert "cartoon" in STYLES_CONFIG["photorealistic"]["negative_prompt"]
        assert "realistic" in STYLES_CONFIG["anime"]["negative_prompt"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
