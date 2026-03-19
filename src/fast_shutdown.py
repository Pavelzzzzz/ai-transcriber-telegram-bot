import asyncio
import logging
import signal
from contextlib import asynccontextmanager

from src.database_manager import db_manager
from src.resource_manager import resource_manager

logger = logging.getLogger(__name__)


class FastShutdownManager:
    """Быстрый graceful shutdown с таймаутами"""

    def __init__(self):
        self._shutdown_requested = False
        self._active_tasks: set[asyncio.Task] = set()
        self._shutdown_callbacks = []
        self._shutdown_timeout = 15  # Максимально 15 секунд

        # Регистрация сигналов
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        if hasattr(signal, "SIGBREAK"):
            signal.signal(signal.SIGBREAK, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Обработчик сигналов"""
        if self._shutdown_requested:
            return

        self._shutdown_requested = True
        logger.info(f"Received signal {signum}, initiating fast shutdown...")

        # Запуск shutdown в фоне
        asyncio.create_task(self._fast_shutdown())

    @asynccontextmanager
    async def track_task(self, coro):
        """Отслеживание активных задач"""
        task = asyncio.create_task(coro)
        self._active_tasks.add(task)
        try:
            yield task
        finally:
            self._active_tasks.discard(task)
            if task.done():
                task.cancel()

    def register_shutdown_callback(self, callback):
        """Регистрация callback для shutdown"""
        self._shutdown_callbacks.append(callback)

    async def _fast_shutdown(self):
        """Быстрый graceful shutdown"""
        logger.info("Starting fast graceful shutdown...")

        try:
            # 1. Отмена всех активных задач (с таймаутом)
            if self._active_tasks:
                logger.info(f"Cancelling {len(self._active_tasks)} active tasks...")

                tasks = list(self._active_tasks)
                for task in tasks:
                    if not task.done():
                        task.cancel()

                # Ожидание завершения с таймаутом
                await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=self._shutdown_timeout,
                )

            # 2. Выполнение shutdown callbacks
            logger.info("Executing shutdown callbacks...")
            for callback in self._shutdown_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback()
                    else:
                        callback()
                except Exception as e:
                    logger.error(f"Error in shutdown callback: {e}")

            # 3. Закрытие ресурсов (параллельно)
            logger.info("Cleaning up resources...")

            cleanup_tasks = [
                asyncio.to_thread(resource_manager.cleanup_all),
                asyncio.to_thread(db_manager.close_all_connections),
            ]

            if cleanup_tasks:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)

            logger.info("Graceful shutdown completed")

        except Exception as e:
            logger.error(f"Error during fast shutdown: {e}")

    def is_shutdown_requested(self) -> bool:
        """Проверка статуса shutdown"""
        return self._shutdown_requested

    def get_stats(self) -> dict:
        """Получение статистики shutdown"""
        return {
            "shutdown_requested": self._shutdown_requested,
            "active_tasks": len(self._active_tasks),
            "shutdown_callbacks": len(self._shutdown_callbacks),
            "shutdown_timeout": self._shutdown_timeout,
        }


# Глобальный экземпляр
shutdown_manager = FastShutdownManager()


def get_shutdown_manager() -> FastShutdownManager:
    """Получение менеджера shutdown"""
    return shutdown_manager
