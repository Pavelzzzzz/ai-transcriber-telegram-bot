import pytest
import os
import sys
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from services.common.schemas import (
    TaskMessage, ResultMessage, TaskType, TaskStatus,
    ImageModel, ImageStyle, AspectRatio, IMAGE_GEN_METADATA_DEFAULTS
)


class TestImageGenServiceIntegration:
    """Integration tests for image generation service"""
    
    @pytest.mark.integration
    def test_image_gen_task_message_creation(self):
        """Test creating image generation task message"""
        task = TaskMessage(
            task_id="img-gen-test-123",
            task_type=TaskType.IMAGE_GEN,
            user_id=12345,
            chat_id=67890,
            timestamp=datetime.now(),
            file_path="A beautiful sunset",
            metadata={
                "width": 1024,
                "height": 1024,
                "model": "sdxl",
                "style": "photorealistic",
                "aspect_ratio": "1:1",
                "num_variations": 2
            }
        )
        
        assert task.task_type == TaskType.IMAGE_GEN
        assert task.file_path == "A beautiful sunset"
        assert task.metadata["model"] == "sdxl"
        assert task.metadata["num_variations"] == 2
    
    @pytest.mark.integration
    def test_image_gen_result_message_creation(self):
        """Test creating image generation result message"""
        result = ResultMessage(
            task_id="img-gen-test-123",
            status=TaskStatus.SUCCESS,
            result_type="image",
            result_data={
                "file_path": "/test/image.png",
                "file_paths": ["/test/image.png"],
                "prompt": "A beautiful sunset",
                "model": "sdxl",
                "style": "photorealistic",
                "width": 1024,
                "height": 1024
            }
        )
        
        assert result.status == TaskStatus.SUCCESS
        assert "file_path" in result.result_data
        assert result.result_data["model"] == "sdxl"
    
    @pytest.mark.integration
    def test_image_gen_result_with_error(self):
        """Test image generation result with error"""
        result = ResultMessage(
            task_id="img-gen-test-456",
            status=TaskStatus.FAILED,
            result_type="image",
            result_data={},
            error="Model loading failed"
        )
        
        assert result.status == TaskStatus.FAILED
        assert result.error == "Model loading failed"
    
    @pytest.mark.integration
    def test_prompt_validation(self):
        """Test prompt validation"""
        from services.image_gen_service.processor import ImageGenerationProcessor
        
        processor = ImageGenerationProcessor()
        
        with pytest.raises(ValueError):
            processor._validate_prompt("")
        
        with pytest.raises(ValueError):
            processor._validate_prompt("ab")
        
        assert processor._validate_prompt("A cat") is True


class TestImageModelEnum:
    """Test ImageModel enum"""
    
    @pytest.mark.integration
    def test_image_model_values(self):
        assert ImageModel.SD15.value == "sd15"
        assert ImageModel.SDXL.value == "sdxl"
        assert ImageModel.FLUX.value == "flux"
    
    @pytest.mark.integration
    def test_image_model_members(self):
        models = list(ImageModel)
        assert len(models) == 3
        assert ImageModel.SD15 in models
        assert ImageModel.SDXL in models
        assert ImageModel.FLUX in models


class TestImageStyleEnum:
    """Test ImageStyle enum"""
    
    @pytest.mark.integration
    def test_image_style_values(self):
        assert ImageStyle.NONE.value == ""
        assert ImageStyle.PHOTOREALISTIC.value == "photorealistic"
        assert ImageStyle.ANIME.value == "anime"
        assert ImageStyle.ART.value == "art"
        assert ImageStyle.THREE_D.value == "3d"


class TestAspectRatioEnum:
    """Test AspectRatio enum"""
    
    @pytest.mark.integration
    def test_aspect_ratio_values(self):
        assert AspectRatio.SQUARE.value == "1:1"
        assert AspectRatio.LANDSCAPE.value == "16:9"
        assert AspectRatio.PORTRAIT.value == "9:16"
        assert AspectRatio.CLASSIC.value == "4:3"


class TestImageGenMetadataDefaults:
    """Test image generation metadata defaults"""
    
    @pytest.mark.integration
    def test_default_metadata(self):
        assert IMAGE_GEN_METADATA_DEFAULTS["model"] == "sdxl"
        assert IMAGE_GEN_METADATA_DEFAULTS["style"] == ""
        assert IMAGE_GEN_METADATA_DEFAULTS["aspect_ratio"] == "1:1"
        assert IMAGE_GEN_METADATA_DEFAULTS["num_variations"] == 1
        assert IMAGE_GEN_METADATA_DEFAULTS["negative_prompt"] == ""
        assert IMAGE_GEN_METADATA_DEFAULTS["num_inference_steps"] == 30
        assert IMAGE_GEN_METADATA_DEFAULTS["guidance_scale"] == 7.5
        assert IMAGE_GEN_METADATA_DEFAULTS["seed"] is None


class TestHardwareIntegration:
    """Test hardware detection integration"""
    
    @pytest.mark.integration
    def test_models_config_exists(self):
        from services.common.hardware import MODELS_CONFIG
        
        assert "sd15" in MODELS_CONFIG
        assert "sdxl" in MODELS_CONFIG
        assert "flux" in MODELS_CONFIG
        
        assert MODELS_CONFIG["sd15"]["min_vram_gb"] == 0
        assert MODELS_CONFIG["sdxl"]["min_vram_gb"] == 8
        assert MODELS_CONFIG["flux"]["min_vram_gb"] == 16
    
    @pytest.mark.integration
    def test_styles_config_exists(self):
        from services.common.hardware import STYLES_CONFIG
        
        assert "" in STYLES_CONFIG
        assert "photorealistic" in STYLES_CONFIG
        assert "anime" in STYLES_CONFIG
        assert "art" in STYLES_CONFIG
        assert "3d" in STYLES_CONFIG
    
    @pytest.mark.integration
    def test_aspect_ratio_sizes(self):
        from services.common.hardware import ASPECT_RATIO_SIZES
        
        assert "1:1" in ASPECT_RATIO_SIZES
        assert "16:9" in ASPECT_RATIO_SIZES
        assert "9:16" in ASPECT_RATIO_SIZES
        assert "4:3" in ASPECT_RATIO_SIZES
        
        assert ASPECT_RATIO_SIZES["1:1"] == (1024, 1024)
        assert ASPECT_RATIO_SIZES["16:9"] == (1024, 576)
    
    @pytest.mark.integration
    @patch('services.common.hardware.torch')
    def test_get_available_models_cpu(self, mock_torch):
        mock_torch.cuda.is_available.return_value = False
        
        from services.common.hardware import get_available_models
        
        available = get_available_models()
        
        assert "sd15" in available
    
    @pytest.mark.integration
    @patch('services.common.hardware.torch')
    def test_is_model_available(self, mock_torch):
        mock_torch.cuda.is_available.return_value = False
        
        from services.common.hardware import is_model_available
        
        assert is_model_available("sd15") is True


class TestImageGenProcessorInit:
    """Test image generation processor initialization"""
    
    @pytest.mark.integration
    def test_processor_init(self):
        from services.image_gen_service.processor import ImageGenerationProcessor
        
        processor = ImageGenerationProcessor()
        assert processor is not None
        assert processor._pipelines == {}


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
