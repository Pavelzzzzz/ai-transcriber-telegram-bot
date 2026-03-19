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
    @patch("services.image_gen_service.processor.os.makedirs")
    async def test_generate_image_mock(self, mock_makedirs, processor):
        with patch(
            "services.image_gen_service.processor.get_available_models", return_value=["sd15"]
        ):
            with patch(
                "services.image_gen_service.processor.MODELS_CONFIG",
                {"sd15": {"model_id": "runwayml/stable-diffusion-v1-5", "min_vram_gb": 0}},
            ):
                mock_pipeline = Mock()
                mock_image = Mock()
                mock_result = Mock()
                mock_result.images = [mock_image]
                mock_pipeline.return_value = mock_result

                with patch(
                    "services.image_gen_service.processor.StableDiffusionPipeline"
                ) as mock_class:
                    mock_class.from_pretrained.return_value = mock_pipeline
                    mock_pipeline.to.return_value = mock_pipeline

                    result = await processor.generate_image("A sunset")

                    assert "file_path" in result or "file_paths" in result
                    assert result["prompt"] == "A sunset"

    @pytest.mark.asyncio
    async def test_generate_image_validation_error(self, processor):
        with pytest.raises(ValueError):
            await processor.generate_image("ab")

    @pytest.mark.asyncio
    @patch("services.image_gen_service.processor.os.makedirs")
    async def test_generate_image_with_metadata(self, mock_makedirs, processor):
        metadata = {
            "model": "sdxl",
            "style": "photorealistic",
            "aspect_ratio": "16:9",
            "num_variations": 2,
            "negative_prompt": "blurry",
            "num_inference_steps": 20,
            "guidance_scale": 5.0,
        }

        with patch(
            "services.image_gen_service.processor.get_available_models", return_value=["sdxl"]
        ):
            with patch(
                "services.image_gen_service.processor.MODELS_CONFIG",
                {
                    "sdxl": {
                        "model_id": "stabilityai/stable-diffusion-xl-base-1.0",
                        "min_vram_gb": 8,
                    }
                },
            ):
                with patch(
                    "services.image_gen_service.processor.ASPECT_RATIO_SIZES", {"16:9": (1024, 576)}
                ):
                    mock_pipeline = Mock()
                    mock_image = Mock()
                    mock_result = Mock()
                    mock_result.images = [mock_image]
                    mock_pipeline.return_value = mock_result

                    with patch(
                        "services.image_gen_service.processor.StableDiffusionXLPipeline"
                    ) as mock_class:
                        mock_class.from_pretrained.return_value = mock_pipeline
                        mock_pipeline.enable_model_cpu_offload = Mock()

                        result = await processor.generate_image("A cat", metadata)

                        assert result["model"] == "sdxl"
                        assert result["style"] == "photorealistic"
                        assert result["aspect_ratio"] == "16:9"
                        assert result["num_variations"] == 2

    def test_clear_cache(self, processor):
        processor._pipelines = {"test": Mock()}
        processor._current_model = "test"

        with patch("services.image_gen_service.processor.torch") as mock_torch:
            mock_torch.cuda.is_available.return_value = True
            mock_torch.cuda.empty_cache = Mock()

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
    """Test that style model_id overrides the default model"""

    @pytest.fixture
    def processor(self):
        return ImageGenerationProcessor()

    @pytest.mark.asyncio
    @patch("services.image_gen_service.processor.os.makedirs")
    async def test_style_overrides_model(self, mock_makedirs, processor):
        """Test that photorealistic style uses its model_id instead of default"""
        metadata = {
            "model": "sd15",
            "style": "photorealistic",
        }

        with patch(
            "services.image_gen_service.processor.get_available_models",
            return_value=["SG161222/Realistic_Vision_V5.1_noVAE"],
        ):
            with patch(
                "services.image_gen_service.processor.STABLES_DIFFUSION_MODEL_CONFIG",
                {
                    "SG161222/Realistic_Vision_V5.1_noVAE": {
                        "model_id": "SG161222/Realistic_Vision_V5.1_noVAE",
                        "min_vram_gb": 0,
                    }
                },
            ):
                with patch(
                    "services.image_gen_service.processor.ASPECT_RATIO_SIZES", {"1:1": (1024, 1024)}
                ):
                    mock_pipeline = Mock()
                    mock_image = Mock()
                    mock_result = Mock()
                    mock_result.images = [mock_image]
                    mock_pipeline.return_value = mock_result

                    with patch(
                        "services.image_gen_service.processor.StableDiffusionPipeline"
                    ) as mock_class:
                        mock_class.from_pretrained.return_value = mock_pipeline
                        mock_pipeline.to.return_value = mock_pipeline

                        result = await processor.generate_image("A cat", metadata)

                        mock_class.from_pretrained.assert_called()
                        call_args = mock_class.from_pretrained.call_args
                        assert "SG161222/Realistic_Vision_V5.1_noVAE" in str(call_args)

    @pytest.mark.asyncio
    @patch("services.image_gen_service.processor.os.makedirs")
    async def test_style_appends_negative_prompt(self, mock_makedirs, processor):
        """Test that style negative_prompt is appended to user negative_prompt"""
        metadata = {
            "model": "sd15",
            "style": "anime",
            "negative_prompt": "blurry",
        }

        with patch(
            "services.image_gen_service.processor.get_available_models",
            return_value=["cagliostrolab/animagine-xl-3.1"],
        ):
            with patch(
                "services.image_gen_service.processor.STABLES_DIFFUSION_MODEL_CONFIG",
                {
                    "cagliostrolab/animagine-xl-3.1": {
                        "model_id": "cagliostrolab/animagine-xl-3.1",
                        "min_vram_gb": 0,
                    }
                },
            ):
                with patch(
                    "services.image_gen_service.processor.ASPECT_RATIO_SIZES", {"1:1": (1024, 1024)}
                ):
                    mock_pipeline = Mock()
                    mock_image = Mock()
                    mock_result = Mock()
                    mock_result.images = [mock_image]
                    mock_pipeline.return_value = mock_result

                    with patch(
                        "services.image_gen_service.processor.StableDiffusionPipeline"
                    ) as mock_class:
                        mock_class.from_pretrained.return_value = mock_pipeline
                        mock_pipeline.to.return_value = mock_pipeline

                        result = await processor.generate_image("A cat", metadata)

                        mock_pipeline.assert_called()
                        call_kwargs = mock_pipeline.call_args.kwargs
                        assert "negative_prompt" in call_kwargs
                        assert "blurry" in call_kwargs["negative_prompt"]
                        assert "realistic" in call_kwargs["negative_prompt"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
