import pytest
import os
import tempfile
from unittest.mock import Mock, patch
from PIL import Image

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.image_processor import ImageProcessor


class TestImageProcessor:
    """Тесты для класса ImageProcessor"""
    
    @pytest.fixture
    def mock_pytesseract(self):
        """Мок для pytesseract"""
        mock_tesseract = Mock()
        mock_tesseract.get_tesseract_version.return_value = "5.0.0"
        mock_tesseract.image_to_string.return_value = "  Тестовый текст  \nс переносами  \n\n  "
        return mock_tesseract
    
    @pytest.fixture
    def processor(self, mock_pytesseract):
        """Фикстура для создания экземпляра ImageProcessor с моком"""
        with patch('utils.image_processor.pytesseract.get_tesseract_version', 
                  return_value=mock_pytesseract.get_tesseract_version()):
            return ImageProcessor()
    
    @pytest.fixture
    def sample_image(self):
        """Создание тестового изображения"""
        image = Image.new('RGB', (100, 50), color='white')
        return image
    
    def test_init(self, processor):
        """Тест инициализации"""
        assert processor.supported_formats == ['.jpg', '.jpeg', '.png', '.webp']
    
    def test_init_tesseract_error(self):
        """Тест инициализации с ошибкой Tesseract"""
        with patch('utils.image_processor.pytesseract.get_tesseract_version', 
                  side_effect=Exception("Tesseract not found")):
            processor = ImageProcessor()
            assert processor.supported_formats == ['.jpg', '.jpeg', '.png', '.webp']
    
    @pytest.mark.asyncio
    async def test_extract_text_from_image_success(self, processor, sample_image):
        """Тест успешного извлечения текста"""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            sample_image.save(tmp_file.name)
            
            with patch('os.path.exists', return_value=True):
                with patch('utils.image_processor.pytesseract.image_to_string', 
                          return_value="  Тестовый текст  \nс переносами  \n\n  "):
                    result = await processor.extract_text_from_image(tmp_file.name)
                    
                    assert result == "Тестовый текст с переносами"
            
            os.unlink(tmp_file.name)
    
    @pytest.mark.asyncio
    async def test_extract_text_file_not_found(self, processor):
        """Тест обработки отсутствующего файла"""
        non_existent_file = "/path/to/non/existent/file.jpg"
        
        with pytest.raises(FileNotFoundError):
            await processor.extract_text_from_image(non_existent_file)
    
    @pytest.mark.asyncio
    async def test_extract_text_unsupported_format(self, processor, sample_image):
        """Тест обработки неподдерживаемого формата"""
        with tempfile.NamedTemporaryFile(suffix='.gif', delete=False) as tmp_file:
            sample_image.save(tmp_file.name)
            
            with patch('os.path.exists', return_value=True):
                with pytest.raises(ValueError, match="Неподдерживаемый формат"):
                    await processor.extract_text_from_image(tmp_file.name)
            
            os.unlink(tmp_file.name)
    
    @pytest.mark.asyncio
    async def test_extract_text_empty_result(self, processor, sample_image):
        """Тест обработки пустого результата"""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            sample_image.save(tmp_file.name)
            
            with patch('os.path.exists', return_value=True):
                with patch('utils.image_processor.pytesseract.image_to_string', 
                          return_value="   \n\n   "):
                    result = await processor.extract_text_from_image(tmp_file.name)
                    
                    assert result == ""
            
            os.unlink(tmp_file.name)
    
    @pytest.mark.asyncio
    async def test_extract_text_tesseract_error(self, processor, sample_image):
        """Тест обработки ошибки Tesseract"""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            sample_image.save(tmp_file.name)
            
            with patch('os.path.exists', return_value=True):
                with patch('utils.image_processor.pytesseract.image_to_string', 
                          side_effect=Exception("Tesseract error")):
                    with pytest.raises(Exception, match="Tesseract error"):
                        await processor.extract_text_from_image(tmp_file.name)
            
            os.unlink(tmp_file.name)
    
    def test_preprocess_image_success(self, processor, sample_image):
        """Тест успешной предобработки изображения"""
        processed_image = processor.preprocess_image(sample_image)
        
        assert processed_image.mode == 'L'
        assert processed_image.size == sample_image.size
    
    def test_preprocess_image_error(self, processor, sample_image):
        """Тест обработки ошибки в предобработке"""
        with patch('utils.image_processor.ImageEnhance.Contrast', 
                  side_effect=Exception("Enhance error")):
            result = processor.preprocess_image(sample_image)
            
            assert result is sample_image
    
    @pytest.mark.asyncio
    async def test_extract_text_image_conversion(self, processor):
        """Тест конвертации изображения в RGB"""
        rgba_image = Image.new('RGBA', (100, 50), color='white')
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            rgba_image.save(tmp_file.name)
            
            with patch('os.path.exists', return_value=True):
                with patch('utils.image_processor.pytesseract.image_to_string', 
                          return_value="Тестовый текст"):
                    with patch('PIL.Image.open', return_value=rgba_image):
                        result = await processor.extract_text_from_image(tmp_file.name)
                        
                        assert result == "Тестовый текст"
            
            os.unlink(tmp_file.name)
    
    @pytest.mark.asyncio
    async def test_extract_text_image_resize(self, processor, sample_image):
        """Тест изменения размера изображения"""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            sample_image.save(tmp_file.name)
            
            with patch('os.path.exists', return_value=True):
                with patch('utils.image_processor.pytesseract.image_to_string', 
                          return_value="Тестовый текст") as mock_ocr:
                    with patch('PIL.Image.open') as mock_open:
                        mock_image = Mock()
                        mock_image.mode = 'RGB'
                        mock_image.resize.return_value = sample_image
                        mock_open.return_value = mock_image
                        
                        await processor.extract_text_from_image(tmp_file.name)
                        
                        mock_image.resize.assert_called_once()
                        resize_args = mock_image.resize.call_args[0]
                        assert resize_args[0] == (sample_image.width * 2, sample_image.height * 2)
            
            os.unlink(tmp_file.name)
    
    @pytest.mark.asyncio
    async def test_extract_text_custom_config(self, processor, sample_image):
        """Тест использования кастомной конфигурации Tesseract"""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            sample_image.save(tmp_file.name)
            
            with patch('os.path.exists', return_value=True):
                with patch('utils.image_processor.pytesseract.image_to_string', 
                          return_value="Тестовый текст") as mock_ocr:
                    await processor.extract_text_from_image(tmp_file.name)
                    
                    mock_ocr.assert_called_once()
                    config_arg = mock_ocr.call_args[1]['config']
                    assert '--oem 3 --psm 6 -l rus+eng' in config_arg
            
            os.unlink(tmp_file.name)
    
    @pytest.mark.asyncio
    async def test_extract_text_cleaning(self, processor, sample_image):
        """Тест очистки текста"""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            sample_image.save(tmp_file.name)
            
            with patch('os.path.exists', return_value=True):
                with patch('utils.image_processor.pytesseract.image_to_string', 
                          return_value="  Текст   с   множественными\n\nпробелами  \n  "):
                    result = await processor.extract_text_from_image(tmp_file.name)
                    
                    assert result == "Текст с множественными пробелами"
            
            os.unlink(tmp_file.name)
    
    def test_supported_formats(self, processor):
        """Тест поддерживаемых форматов"""
        expected_formats = ['.jpg', '.jpeg', '.png', '.webp']
        assert processor.supported_formats == expected_formats
        
        for fmt in expected_formats:
            assert fmt in processor.supported_formats