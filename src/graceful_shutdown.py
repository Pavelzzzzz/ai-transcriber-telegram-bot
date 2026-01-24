"""Graceful shutdown manager for the bot"""

import signal
import asyncio
import logging
import atexit
from typing import Optional, Set, Callable, Any
from src.exceptions import ErrorHandler
from src.resource_manager import resource_manager

logger = logging.getLogger(__name__)

class GracefulShutdownManager:
    """Менеджер для грациозного останова бота"""
    
    def __init__(self):
        self._shutdown_requested = False
        self._active_tasks: Set[asyncio.Task] = set()
        self._shutdown_callbacks: list[Callable] = []
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._application = None
        
    def register_task(self, task: asyncio.Task) -> None:
        """Регистрация активной задачи"""
        self._active_tasks.add(task)
        task.add_done_callback(lambda: self._active_tasks.discard(task))
    
    def register_shutdown_callback(self, callback: Callable) -> None:
        """Регистрация callback для shutdown"""
        self._shutdown_callbacks.append(callback)
    
    def request_shutdown(self, signal_number: Optional[int] = None, frame: Optional[Any] = None) -> None:
        """Запрос на остановку бота"""
        if self._shutdown_requested:
            return
            
        self._shutdown_requested = True
        signal_name = signal.Signals(signal_number).name if signal_number else "UNKNOWN"
        logger.info(f"Shutdown requested via signal: {signal_name}")
        
        if self._loop:
            self._loop.create_task(self._graceful_shutdown())
    
    async def _graceful_shutdown(self) -> None:
        """Выполнение грациозного останова"""
        logger.info("Starting graceful shutdown...")
        
        # 1. Прекращение приема новых сообщений
        if self._application:
            logger.info("Stopping bot application...")
            await self._application.stop()
        
        # 2. Ожидание завершения активных задач (с timeout)
        if self._active_tasks:
            logger.info(f"Waiting for {len(self._active_tasks)} active tasks to complete...")
            
            # Ждем завершения задач с timeout 30 секунд
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._active_tasks, return_exceptions=True),
                    timeout=30.0
                )
            except asyncio.TimeoutError:
                logger.warning("Timeout waiting for tasks to complete, forcing cancellation")
                
                # Принудительная отмена оставшихся задач
                for task in self._active_tasks:
                    if not task.done():
                        task.cancel()
                
                # Ждем завершения отмененных задач
                await asyncio.gather(*self._active_tasks, return_exceptions=True)
        
        # 3. Выполнение shutdown callbacks
        logger.info("Executing shutdown callbacks...")
        for callback in self._shutdown_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                ErrorHandler.log_error(e, {"operation": "shutdown_callback"})
        
        # 4. Очистка ресурсов
        logger.info("Cleaning up resources...")
        try:
            resource_manager.cleanup_all()
        except Exception as e:
            ErrorHandler.log_error(e, {"operation": "resource_cleanup"})
        
        # 5. Закрытие базы данных
        logger.info("Closing database connections...")
        try:
            from src.database_manager import db_manager
            db_manager.close_all_connections()
        except Exception as e:
            ErrorHandler.log_error(e, {"operation": "database_close"})
        
        logger.info("Graceful shutdown completed")
    
    def setup_signal_handlers(self, loop: asyncio.AbstractEventLoop) -> None:
        """Настройка обработчиков сигналов"""
        self._loop = loop
        
        # SIGTERM (docker stop, systemctl stop)
        signal.signal(signal.SIGTERM, self.request_shutdown)
        
        # SIGINT (Ctrl+C)
        signal.signal(signal.SIGINT, self.request_shutdown)
        
        # Альтернативный способ для Windows
        if hasattr(signal, 'SIGBREAK'):
            signal.signal(signal.SIGBREAK, self.request_shutdown)
        
        # Регистрация atexit callback
        atexit.register(self._atexit_handler)
    
    def _atexit_handler(self) -> None:
        """Обработчик для atexit"""
        if not self._shutdown_requested:
            logger.warning("Process exiting without graceful shutdown")
            asyncio.create_task(self._graceful_shutdown())
    
    def set_application(self, application) -> None:
        """Установка ссылки на Application"""
        self._application = application
    
    def get_shutdown_status(self) -> dict:
        """Получение статуса shutdown"""
        return {
            "shutdown_requested": self._shutdown_requested,
            "active_tasks": len(self._active_tasks),
            "shutdown_callbacks": len(self._shutdown_callbacks)
        }

# Глобальный экземпляр менеджера
shutdown_manager = GracefulShutdownManager()

def setup_graceful_shutdown(loop: asyncio.AbstractEventLoop, application=None) -> None:
    """Настройка грациозного останова"""
    shutdown_manager.setup_signal_handlers(loop)
    if application:
        shutdown_manager.set_application(application)
    
    logger.info("Graceful shutdown handlers configured")

def request_shutdown(signal_number: Optional[int] = None, frame: Optional[Any] = None) -> None:
    """Функция для запроса shutdown из любого места"""
    shutdown_manager.request_shutdown(signal_number, frame)

def register_shutdown_callback(callback: Callable) -> None:
    """Регистрация callback для shutdown"""
    shutdown_manager.register_shutdown_callback(callback)

def register_active_task(task: asyncio.Task) -> None:
    """Регистрация активной задачи"""
    shutdown_manager.register_task(task)

# Декоратор для автоматической регистрации задачи
def track_task(func):
    """Декоратор для отслеживания завершения задачи"""
    async def wrapper(*args, **kwargs):
        task = asyncio.create_task(func(*args, **kwargs))
        register_active_task(task)
        return await task
    
    return wrapper