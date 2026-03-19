import logging
import os
import signal
from abc import ABC, abstractmethod
from collections.abc import Callable
from threading import Event

logger = logging.getLogger(__name__)

try:
    import tornado.ioloop
    import tornado.web

    TORNADO_AVAILABLE = True
except ImportError:
    TORNADO_AVAILABLE = False
    logger.warning("Tornado not available, health check endpoints will be disabled")


class BaseService(ABC):
    def __init__(self, service_name: str):
        self.service_name = service_name
        self._running = False
        self._shutdown_event = Event()
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        logger.info(f"{self.service_name}: Received signal {signum}, initiating shutdown...")
        self.stop()

    @abstractmethod
    def _initialize(self) -> None:
        """Initialize service components"""
        pass

    @abstractmethod
    def _process_message(self, message: dict) -> dict:
        """Process a message - to be implemented by subclasses"""
        pass

    @abstractmethod
    def _get_health_status(self) -> dict:
        """Return health status of the service"""
        pass

    def start(self) -> None:
        """Start the service"""
        logger.info(f"Starting {self.service_name}...")
        try:
            self._initialize()
            self._running = True
            logger.info(f"{self.service_name} started successfully")

            while self._running:
                self._shutdown_event.wait(timeout=1)
                if not self._running:
                    break

        except Exception as e:
            logger.error(f"Error starting {self.service_name}: {e}")
            raise

    def stop(self) -> None:
        """Stop the service gracefully"""
        logger.info(f"Stopping {self.service_name}...")
        self._running = False
        self._shutdown_event.set()
        logger.info(f"{self.service_name} stopped")


class HealthCheckHandler:
    """Fallback health check handler when tornado is not available"""

    def __init__(self, get_status_func: Callable[[], dict]):
        self.get_status_func = get_status_func


def run_service_with_healthcheck(service: BaseService, port: int = 8080) -> None:
    """Run service with embedded health check server"""

    if not TORNADO_AVAILABLE:
        logger.warning("Tornado not available, running service without health check server")
        service.start()
        return

    class HealthHandler(tornado.web.RequestHandler):
        def get(self):
            status = service._get_health_status()
            self.set_header("Content-Type", "application/json")

            if status.get("status") == "healthy":
                self.set_status(200)
            else:
                self.set_status(503)

            import json

            self.write(json.dumps(status))

    app = tornado.web.Application(
        [
            (r"/health", HealthHandler),
        ]
    )

    app.listen(port)
    logger.info(f"Health check server running on port {port}")

    import threading

    health_server = threading.Thread(target=tornado.ioloop.IOLoop.current().start, daemon=True)
    health_server.start()

    service.start()


def setup_logging(service_name: str, level: str = None) -> logging.Logger:
    """Setup centralized logging for services"""
    log_level = level or os.getenv("LOG_LEVEL", "INFO")

    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger = logging.getLogger(service_name)
    return logger
