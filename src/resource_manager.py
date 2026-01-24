"""Resource cleanup manager for temporary files and resources"""

import os
import tempfile
import shutil
import logging
import asyncio
from typing import List, Optional, Any, Callable, Union
from contextlib import contextmanager, asynccontextmanager
from pathlib import Path
from src.exceptions import FileProcessingError, ErrorHandler

logger = logging.getLogger(__name__)

class ResourceManager:
    """Управление временными ресурсами и их очисткой"""
    
    def __init__(self):
        self._temp_files: List[str] = []
        self._temp_dirs: List[str] = []
        self._cleanup_callbacks: List[Callable] = []
    
    def register_temp_file(self, file_path: Union[str, Path]) -> str:
        """Регистрация временного файла для очистки"""
        path_str = str(file_path)
        self._temp_files.append(path_str)
        return path_str
    
    def register_temp_dir(self, dir_path: Union[str, Path]) -> str:
        """Регистрация временной директории для очистки"""
        path_str = str(dir_path)
        self._temp_dirs.append(path_str)
        return path_str
    
    def register_cleanup_callback(self, callback: Callable) -> None:
        """Регистрация callback для очистки"""
        self._cleanup_callbacks.append(callback)
    
    def cleanup_file(self, file_path: str) -> bool:
        """Безопасное удаление файла"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.debug(f"Removed temporary file: {file_path}")
                return True
        except Exception as e:
            ErrorHandler.log_error(e, {"file_path": file_path, "operation": "file_cleanup"})
        return False
    
    def cleanup_directory(self, dir_path: str, remove_contents_only: bool = False) -> bool:
        """Безопасное удаление директории"""
        try:
            if os.path.exists(dir_path):
                if remove_contents_only:
                    shutil.rmtree(dir_path, ignore_errors=True)
                    os.makedirs(dir_path, exist_ok=True)
                    logger.debug(f"Cleaned directory contents: {dir_path}")
                else:
                    shutil.rmtree(dir_path)
                    logger.debug(f"Removed directory: {dir_path}")
                return True
        except Exception as e:
            ErrorHandler.log_error(e, {"dir_path": dir_path, "operation": "dir_cleanup"})
        return False
    
    def cleanup_all(self) -> None:
        """Очистка всех зарегистрированных ресурсов"""
        # Выполнение cleanup callbacks
        for callback in self._cleanup_callbacks:
            try:
                callback()
            except Exception as e:
                ErrorHandler.log_error(e, {"operation": "cleanup_callback"})
        
        # Очистка файлов
        for file_path in self._temp_files:
            self.cleanup_file(file_path)
        
        # Очистка директорий
        for dir_path in self._temp_dirs:
            self.cleanup_directory(dir_path)
        
        # Очистка списков
        self._temp_files.clear()
        self._temp_dirs.clear()
        self._cleanup_callbacks.clear()
    
    def get_stats(self) -> dict:
        """Получение статистики использования ресурсов"""
        return {
            "temp_files": len(self._temp_files),
            "temp_dirs": len(self._temp_dirs),
            "cleanup_callbacks": len(self._cleanup_callbacks),
            "total_resources": len(self._temp_files) + len(self._temp_dirs)
        }

# Глобальный экземпляр resource manager
resource_manager = ResourceManager()

@contextmanager
def temp_file(suffix: str = "", prefix: str = "temp_") -> Any:
    """Контекстный менеджер для создания временного файла"""
    try:
        fd, path = tempfile.mkstemp(suffix=suffix, prefix=prefix)
        os.close(fd)
        resource_manager.register_temp_file(path)
        yield path
    except Exception as e:
        ErrorHandler.log_error(e, {"operation": "temp_file_creation"})
        raise FileProcessingError(
            message="Failed to create temporary file",
            context={"suffix": suffix, "prefix": prefix, "error": str(e)}
        )
    finally:
        # File будет очищен через resource_manager
        pass

@contextmanager
def temp_dir() -> Any:
    """Контекстный менеджер для создания временной директории"""
    try:
        path = tempfile.mkdtemp()
        resource_manager.register_temp_dir(path)
        yield path
    except Exception as e:
        ErrorHandler.log_error(e, {"operation": "temp_dir_creation"})
        raise FileProcessingError(
            message="Failed to create temporary directory",
            context={"error": str(e)}
        )
    finally:
        # Directory будет очищена через resource_manager
        pass

@asynccontextmanager
async def async_temp_file(suffix: str = "", prefix: str = "temp_") -> Any:
    """Асинхронный контекстный менеджер для временного файла"""
    try:
        fd, path = await asyncio.to_thread(tempfile.mkstemp, suffix, prefix)
        await asyncio.to_thread(os.close, fd)
        resource_manager.register_temp_file(path)
        yield path
    except Exception as e:
        ErrorHandler.log_error(e, {"operation": "async_temp_file_creation"})
        raise FileProcessingError(
            message="Failed to create async temporary file",
            context={"suffix": suffix, "prefix": prefix, "error": str(e)}
        )
    finally:
        pass

@asynccontextmanager
async def async_temp_dir() -> Any:
    """Асинхронный контекстный менеджер для временной директории"""
    try:
        path = await asyncio.to_thread(tempfile.mkdtemp)
        resource_manager.register_temp_dir(path)
        yield path
    except Exception as e:
        ErrorHandler.log_error(e, {"operation": "async_temp_dir_creation"})
        raise FileProcessingError(
            message="Failed to create async temporary directory",
            context={"error": str(e)}
        )
    finally:
        pass

class FileDownloader:
    """Безопасная загрузка файлов с автоматической очисткой"""
    
    def __init__(self, download_dir: str = "downloads"):
        self.download_dir = download_dir
        self._ensure_download_dir()
    
    def _ensure_download_dir(self) -> None:
        """Создание директории для загрузок"""
        os.makedirs(self.download_dir, exist_ok=True)
        resource_manager.register_temp_dir(self.download_dir)
    
    async def download_file(self, bot, file_id: str, user_id: int) -> str:
        """Загрузка файла с автоматической очисткой"""
        try:
            file = await bot.get_file(file_id)
            file_path = os.path.join(self.download_dir, f"{user_id}_{file.file_id}")
            resource_manager.register_temp_file(file_path)
            
            await file.download_to_drive(file_path)
            logger.info(f"File downloaded successfully: {file_path}")
            return file_path
            
        except Exception as e:
            ErrorHandler.log_error(e, {
                "file_id": file_id,
                "user_id": user_id,
                "operation": "file_download"
            })
            raise FileProcessingError(
                message="Failed to download file",
                file_path=file_id,
                context={"error": str(e)}
            )

class AudioProcessor:
    """Обработка аудио с автоматической очисткой"""
    
    @staticmethod
    @asynccontextmanager
    async def process_audio(audio_path: str) -> Any:
        """Контекст для обработки аудио файла"""
        try:
            yield audio_path
        except Exception as e:
            ErrorHandler.log_error(e, {"audio_path": audio_path, "operation": "audio_processing"})
            raise AudioProcessingError(
                message="Audio processing failed",
                audio_path=audio_path,
                context={"error": str(e)}
            )
        finally:
            # Файл будет очищен через resource_manager
            pass

class ImageProcessor:
    """Обработка изображений с автоматической очисткой"""
    
    @staticmethod
    @asynccontextmanager
    async def process_image(image_path: str) -> Any:
        """Контекст для обработки изображения"""
        try:
            yield image_path
        except Exception as e:
            ErrorHandler.log_error(e, {"image_path": image_path, "operation": "image_processing"})
            raise ImageProcessingError(
                message="Image processing failed",
                image_path=image_path,
                context={"error": str(e)}
            )
        finally:
            # Файл будет очищен через resource_manager
            pass

# Функции для удобного использования
def safe_remove_file(file_path: str) -> bool:
    """Безопасное удаление файла с логированием"""
    return resource_manager.cleanup_file(file_path)

def safe_remove_directory(dir_path: str, remove_contents_only: bool = False) -> bool:
    """Безопасное удаление директории с логированием"""
    return resource_manager.cleanup_directory(dir_path, remove_contents_only)

def register_cleanup_function(func: Callable) -> None:
    """Регистрация функции для очистки при shutdown"""
    resource_manager.register_cleanup_callback(func)