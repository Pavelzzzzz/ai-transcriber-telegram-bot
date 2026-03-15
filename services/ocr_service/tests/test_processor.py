import pytest
import os
import sys
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from services.common.schemas import TaskMessage, ResultMessage, TaskType, TaskStatus
from services.ocr_service.processor import OCRProcessor


class TestOCRProcessor:
    @pytest.fixture
    def processor(self):
        return OCRProcessor()
    
    @pytest.mark.asyncio
    @patch('services.ocr_service.processor.ImageProcessor')
    async def test_process_image_success(self, mock_image_processor_class, processor):
        mock_processor = Mock()
        mock_processor.extract_text_from_image = AsyncMock(return_value="Extracted text from image")
        mock_image_processor_class.return_value = mock_processor
        
        result = await processor.process_image("/path/to/image.jpg")
        
        assert result["text"] == "Extracted text from image"
        assert result["file_path"] == "/path/to/image.jpg"
        mock_processor.extract_text_from_image.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('services.ocr_service.processor.ImageProcessor')
    async def test_process_image_with_languages(self, mock_image_processor_class, processor):
        mock_processor = Mock()
        mock_processor.extract_text_from_image = AsyncMock(return_value="Text")
        mock_image_processor_class.return_value = mock_processor
        
        result = await processor.process_image("/path/to/image.jpg", languages=["ru", "eng"])
        
        assert result["languages"] == ["ru", "eng"]
    
    @pytest.mark.asyncio
    @patch('services.ocr_service.processor.ImageProcessor')
    async def test_process_image_file_not_found(self, mock_image_processor_class, processor):
        mock_processor = Mock()
        mock_processor.extract_text_from_image = AsyncMock(side_effect=FileNotFoundError("File not found"))
        mock_image_processor_class.return_value = mock_processor
        
        with pytest.raises(FileNotFoundError):
            await processor.process_image("/nonexistent/image.jpg")
    
    @pytest.mark.asyncio
    @patch('services.ocr_service.processor.ImageProcessor')
    async def test_process_image_error(self, mock_image_processor_class, processor):
        mock_processor = Mock()
        mock_processor.extract_text_from_image = AsyncMock(side_effect=Exception("OCR Error"))
        mock_image_processor_class.return_value = mock_processor
        
        with pytest.raises(Exception, match="OCR Error"):
            await processor.process_image("/path/to/image.jpg")
