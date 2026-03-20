import os
from unittest.mock import MagicMock, patch

import pytest


class TestOCRProcessorGPUDetection:
    """Tests for GPU detection"""

    def test_gpu_detection_nvidia(self):
        with patch.dict(os.environ, {"GPU_TYPE": "nvidia"}):
            from services.ocr_service.processor import OCRProcessor

            processor = OCRProcessor()
            assert processor._detect_gpu() is True

    def test_gpu_detection_amd(self):
        with patch.dict(os.environ, {"GPU_TYPE": "amd"}):
            from services.ocr_service.processor import OCRProcessor

            processor = OCRProcessor()
            assert processor._detect_gpu() is True

    def test_gpu_detection_cpu(self):
        with patch.dict(os.environ, {"GPU_TYPE": "cpu"}):
            from services.ocr_service.processor import OCRProcessor

            processor = OCRProcessor()
            assert processor._detect_gpu() is False

    def test_gpu_detection_intel(self):
        with patch.dict(os.environ, {"GPU_TYPE": "intel"}):
            from services.ocr_service.processor import OCRProcessor

            processor = OCRProcessor()
            assert processor._detect_gpu() is False

    def test_gpu_detection_default(self):
        with patch.dict(os.environ, {}, clear=True):
            from services.ocr_service.processor import OCRProcessor

            processor = OCRProcessor()
            assert processor._detect_gpu() is False


class TestOCRProcessorPreprocessing:
    """Tests for image preprocessing"""

    def test_preprocess_image_converts_to_grayscale(self):
        from PIL import Image

        from services.ocr_service.processor import OCRProcessor

        processor = OCRProcessor()
        test_image = Image.new("RGB", (100, 100), color="red")

        result = processor._preprocess_image(test_image)

        assert result.mode == "L"

    def test_preprocess_image_enhances_contrast(self):
        from PIL import Image

        from services.ocr_service.processor import OCRProcessor

        processor = OCRProcessor()
        test_image = Image.new("L", (100, 100), color=128)

        result = processor._preprocess_image(test_image)

        assert result.mode == "L"
        assert result.size == (100, 100)

    def test_preprocess_image_applies_denoise(self):
        from PIL import Image

        from services.ocr_service.processor import OCRProcessor

        processor = OCRProcessor()
        test_image = Image.new("L", (100, 100), color=128)

        result = processor._preprocess_image(test_image)

        assert result.mode == "L"


class TestOCRProcessorPostprocessing:
    """Tests for text postprocessing"""

    def test_postprocess_empty_result(self):
        from services.ocr_service.processor import OCRProcessor

        processor = OCRProcessor()
        result = processor._postprocess_text(None)
        assert result == ""

    def test_postprocess_empty_list(self):
        from services.ocr_service.processor import OCRProcessor

        processor = OCRProcessor()
        result = processor._postprocess_text([])
        assert result == ""

    def test_postprocess_single_item(self):
        from services.ocr_service.processor import OCRProcessor

        processor = OCRProcessor()
        result = processor._postprocess_text([[None, "hello", None]])
        assert result == "hello"

    def test_postprocess_multiple_items(self):
        from services.ocr_service.processor import OCRProcessor

        processor = OCRProcessor()
        result = processor._postprocess_text(
            [
                [None, "hello", None],
                [None, "world", None],
            ]
        )
        assert result == "hello world"


class TestOCRProcessorValidation:
    """Tests for input validation"""

    def test_supported_formats(self):
        from services.ocr_service.processor import SUPPORTED_FORMATS

        assert ".jpg" in SUPPORTED_FORMATS
        assert ".jpeg" in SUPPORTED_FORMATS
        assert ".png" in SUPPORTED_FORMATS
        assert ".webp" in SUPPORTED_FORMATS


class TestOCRProcessorLazyLoading:
    """Tests for lazy loading of RapidOCR reader"""

    @pytest.fixture
    def rapidocr_available(self):
        try:
            import rapidocr_onnxruntime

            return True
        except ImportError:
            return False

    def test_reader_initialized_on_first_access(self, rapidocr_available):
        if not rapidocr_available:
            pytest.skip("rapidocr_onnxruntime not installed")

        with patch.dict(os.environ, {"GPU_TYPE": "cpu"}):
            from services.ocr_service.processor import OCRProcessor

            processor = OCRProcessor()
            assert processor._reader is None

            with patch("rapidocr_onnxruntime.RapidOCR") as mock_rapid:
                _ = processor.reader
                mock_rapid.assert_called_once()
                assert processor._reader is not None

    def test_reader_uses_gpu_when_enabled(self, rapidocr_available):
        if not rapidocr_available:
            pytest.skip("rapidocr_onnxruntime not installed")

        with patch.dict(os.environ, {"GPU_TYPE": "nvidia"}):
            from services.ocr_service.processor import OCRProcessor

            processor = OCRProcessor()

            with patch("rapidocr_onnxruntime.RapidOCR") as mock_rapid:
                _ = processor.reader
                mock_rapid.assert_called_once_with(
                    det_use_cuda=True,
                    rec_use_cuda=True,
                    cls_use_cuda=True,
                )

    def test_reader_uses_cpu_when_disabled(self, rapidocr_available):
        if not rapidocr_available:
            pytest.skip("rapidocr_onnxruntime not installed")

        with patch.dict(os.environ, {"GPU_TYPE": "cpu"}):
            from services.ocr_service.processor import OCRProcessor

            processor = OCRProcessor()

            with patch("rapidocr_onnxruntime.RapidOCR") as mock_rapid:
                _ = processor.reader
                mock_rapid.assert_called_once_with(
                    det_use_cuda=False,
                    rec_use_cuda=False,
                    cls_use_cuda=False,
                )
