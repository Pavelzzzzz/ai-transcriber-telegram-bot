import pytest
import os
import sys
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from services.common.schemas import TaskMessage, ResultMessage, TaskType, TaskStatus


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
            metadata={"width": 1024, "height": 1024}
        )
        
        assert task.task_type == TaskType.IMAGE_GEN
        assert task.file_path == "A beautiful sunset"
        assert task.metadata["width"] == 1024
    
    @pytest.mark.integration
    def test_image_gen_result_message_creation(self):
        """Test creating image generation result message"""
        result = ResultMessage(
            task_id="img-gen-test-123",
            status=TaskStatus.SUCCESS,
            result_type="image",
            result_data={
                "file_path": "/test/image.png",
                "prompt": "A beautiful sunset",
                "width": 1024,
                "height": 1024
            }
        )
        
        assert result.status == TaskStatus.SUCCESS
        assert "file_path" in result.result_data
        assert result.result_data["prompt"] == "A beautiful sunset"
    
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


class TestImageGenProcessor:
    """Test image generation processor logic"""
    
    @pytest.mark.integration
    def test_processor_init(self):
        """Test image generation processor initialization"""
        from services.image_gen_service.processor import ImageGenerationProcessor
        
        processor = ImageGenerationProcessor()
        assert processor is not None
        assert processor.model_id == "stabilityai/stable-diffusion-xl-base-1.0"
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    @patch('services.image_gen_service.processor.Image')
    async def test_generate_image_mock(self, mock_image_class):
        """Test image generation with mock"""
        from services.image_gen_service.processor import ImageGenerationProcessor
        
        mock_image = Mock()
        mock_image.save = Mock()
        mock_image_class.new.return_value = mock_image
        mock_image_class.Draw.return_value = Mock()
        
        processor = ImageGenerationProcessor()
        
        result = await processor.generate_image("A beautiful sunset")
        
        assert "file_path" in result
        assert result["prompt"] == "A beautiful sunset"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
