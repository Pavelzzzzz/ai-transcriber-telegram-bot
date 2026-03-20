import logging
import os
from typing import Any

from PIL import Image, ImageEnhance, ImageFilter

logger = logging.getLogger(__name__)

SUPPORTED_FORMATS = [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"]


class OCRProcessor:
    def __init__(self):
        self._reader = None
        self._gpu_enabled = False

    def _detect_gpu(self) -> bool:
        gpu_type = os.getenv("GPU_TYPE", "cpu").lower()
        return gpu_type in ("nvidia", "amd")

    @property
    def reader(self):
        if self._reader is None:
            from rapidocr_onnxruntime import RapidOCR

            self._gpu_enabled = self._detect_gpu()
            logger.info(f"Initializing RapidOCR (GPU: {self._gpu_enabled})")

            self._reader = RapidOCR(
                det_use_cuda=self._gpu_enabled,
                rec_use_cuda=self._gpu_enabled,
                cls_use_cuda=self._gpu_enabled,
            )
        return self._reader

    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        if image.mode != "L":
            image = image.convert("L")

        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)

        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.2)

        image = image.filter(ImageFilter.MedianFilter(size=3))

        return image

    def _postprocess_text(self, result: list | None) -> str:
        if not result:
            return ""

        parts = []
        for item in result:
            if isinstance(item, (list, tuple)) and len(item) > 1:
                parts.append(item[1])

        return " ".join(parts)

    async def process_image(self, file_path: str, languages: list[str] = None) -> dict[str, Any]:
        try:
            logger.info(f"Processing OCR for file: {file_path}")

            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext not in SUPPORTED_FORMATS:
                raise ValueError(f"Unsupported format: {file_ext}")

            image = Image.open(file_path)

            processed = self._preprocess_image(image)

            result, elapse, _ = self.reader(processed)

            extracted_text = self._postprocess_text(result)

            logger.info(f"OCR completed in {elapse:.3f}s, text length: {len(extracted_text)}")

            return {
                "text": extracted_text.strip(),
                "file_path": file_path,
                "languages": languages or ["ru", "eng"],
                "gpu_enabled": self._gpu_enabled,
                "processing_time": elapse,
            }

        except Exception as e:
            logger.error(f"OCR processing failed: {e}")
            raise
