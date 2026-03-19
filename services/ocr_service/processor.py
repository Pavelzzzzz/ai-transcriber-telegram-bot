import logging
import os

from utils.image_processor import ImageProcessor

logger = logging.getLogger(__name__)


class OCRProcessor:
    def __init__(self):
        self.image_processor = ImageProcessor()

    async def process_image(self, file_path: str, languages: list = None) -> dict:
        try:
            logger.info(f"Processing OCR for file: {file_path}")

            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

            extracted_text = await self.image_processor.extract_text_from_image(file_path)

            return {
                "text": extracted_text,
                "file_path": file_path,
                "languages": languages or ["ru", "eng"],
            }
        except Exception as e:
            logger.error(f"OCR processing failed: {e}")
            raise
