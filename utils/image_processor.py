import logging
import os

import pytesseract
from PIL import Image

logger = logging.getLogger(__name__)


class ImageProcessor:
    def __init__(self):
        """Инициализация обработчика изображений"""
        self.supported_formats = [".jpg", ".jpeg", ".png", ".webp"]

        try:
            pytesseract.get_tesseract_version()
            logger.info("Tesseract успешно инициализирован")
        except Exception as e:
            logger.error(f"Ошибка при инициализации Tesseract: {e}")
            logger.warning("Убедитесь, что Tesseract OCR установлен и доступен в PATH")

    async def extract_text_from_image(self, image_path: str) -> str:
        """Извлечение текста из изображения"""
        try:
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Файл не найден: {image_path}")

            file_ext = os.path.splitext(image_path)[1].lower()
            if file_ext not in self.supported_formats:
                raise ValueError(f"Неподдерживаемый формат: {file_ext}")

            logger.info(f"Обработка изображения: {image_path}")

            image = Image.open(image_path)

            if image.mode != "RGB":
                image = image.convert("RGB")

            image = image.resize((image.width * 2, image.height * 2), Image.Resampling.LANCZOS)

            custom_config = r"--oem 3 --psm 6 -l rus+eng"
            extracted_text = pytesseract.image_to_string(image, config=custom_config)

            cleaned_text = extracted_text.strip().replace("\n", " ")
            cleaned_text = " ".join(cleaned_text.split())

            logger.info(f"Текст успешно извлечен, длина: {len(cleaned_text)}")
            return cleaned_text

        except Exception as e:
            logger.error(f"Ошибка при извлечении текста из изображения: {e}")
            raise

    def preprocess_image(self, image: Image.Image) -> Image.Image:
        """Предобработка изображения для улучшения распознавания"""
        try:
            from PIL import ImageEnhance, ImageFilter

            image = image.convert("L")

            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(2.0)

            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.5)

            image = image.filter(ImageFilter.MedianFilter(size=3))

            return image

        except Exception as e:
            logger.error(f"Ошибка при предобработке изображения: {e}")
            return image
