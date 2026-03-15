import pytest
import os
import sys
from unittest.mock import Mock, patch, AsyncMock, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from services.image_gen_service.processor import ImageGenerationProcessor


class TestImageGenerationProcessor:
    @pytest.fixture
    def processor(self):
        return ImageGenerationProcessor("stabilityai/stable-diffusion-xl-base-1.0")
    
    def test_init_default(self):
        processor = ImageGenerationProcessor()
        assert processor.model_id == "stabilityai/stable-diffusion-xl-base-1.0"
    
    def test_init_custom_model(self):
        processor = ImageGenerationProcessor("stabilityai/stable-diffusion-2-1")
        assert processor.model_id == "stabilityai/stable-diffusion-2-1"
    
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
    @patch('services.image_gen_service.processor.StableDiffusionXLPipeline')
    async def test_generate_image_sdxl(self, mock_pipeline_class, processor):
        mock_pipe = Mock()
        mock_image = Mock()
        mock_image.save = Mock()
        
        mock_result = Mock()
        mock_result.images = [mock_image]
        
        mock_pipe.return_value = mock_result
        
        with patch('services.image_gen_service.processor.torch.inference_mode'):
            with patch('services.image_gen_service.processor.os.makedirs'):
                processor._pipeline = mock_pipe
                
                result = await processor.generate_image("A sunset", 1024, 1024)
                
                assert "image_path" in result
                assert result["prompt"] == "A sunset"
                assert result["width"] == 1024
                assert result["height"] == 1024
                assert result["model"] == "stabilityai/stable-diffusion-xl-base-1.0"
    
    @pytest.mark.asyncio
    async def test_generate_image_validation_error(self, processor):
        with pytest.raises(ValueError):
            await processor.generate_image("ab")
    
    @pytest.mark.asyncio
    @patch('services.image_gen_service.processor.StableDiffusionXLPipeline')
    async def test_generate_image_with_custom_params(self, mock_pipeline_class, processor):
        mock_pipe = Mock()
        mock_image = Mock()
        mock_image.save = Mock()
        
        mock_result = Mock()
        mock_result.images = [mock_image]
        
        mock_pipe.return_value = mock_result
        
        with patch('services.image_gen_service.processor.torch.inference_mode'):
            with patch('services.image_gen_service.processor.os.makedirs'):
                processor._pipeline = mock_pipe
                
                result = await processor.generate_image(
                    "A cat",
                    width=512,
                    height=512,
                    num_inference_steps=20,
                    guidance_scale=5.0
                )
                
                assert result["width"] == 512
                assert result["height"] == 512
                assert result["num_inference_steps"] == 20
                assert result["guidance_scale"] == 5.0
