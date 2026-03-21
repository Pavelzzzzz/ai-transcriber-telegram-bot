import logging
import signal
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from services.common import KafkaProducerError, ResultMessage, kafka_config
from services.common.base_service import BaseService

from .kafka_consumer import OCRKafkaConsumer

logger = logging.getLogger(__name__)


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/metrics":
            from services.common.metrics import get_metrics_collector

            collector = get_metrics_collector("ocr_service")
            metrics = collector.get_metrics()

            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(metrics.encode())
        else:
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "ok", "service": "ocr_service"}')

    def log_message(self, format, *args):
        pass


def start_health_server(port=8002):
    server = HTTPServer(("", port), HealthHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()


class OCRService(BaseService):
    def __init__(self):
        super().__init__("ocr_service")
        self.consumer = None
        self._result_producer = None
        self._initialized = False

        import threading

        self._health_thread = threading.Thread(target=start_health_server, daemon=True)
        self._health_thread.start()

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        logger.info(f"Received signal {signum}, initiating shutdown...")
        self.stop()

    def _initialize(self) -> None:
        logger.info("Initializing OCR Service...")
        self.consumer = OCRKafkaConsumer(kafka_config, self.send_result)
        self.consumer.start()
        self._initialized = True
        logger.info("OCR Service initialized")

    def _get_result_producer(self):
        if self._result_producer is None:
            try:
                from kafka import KafkaProducer

                self._result_producer = KafkaProducer(
                    bootstrap_servers=kafka_config.bootstrap_servers,
                    client_id=f"{kafka_config.client_id}_ocr_producer",
                    value_serializer=lambda v: v.encode("utf-8"),
                    key_serializer=lambda k: k.encode("utf-8") if k else None,
                )
            except Exception as e:
                raise KafkaProducerError(f"Failed to create result producer: {e}", "ocr_service")
        return self._result_producer

    def send_result(self, result: ResultMessage):
        try:
            producer = self._get_result_producer()
            topic = kafka_config.topics["results_ocr"]

            future = producer.send(topic, key=str(result.task_id), value=result.to_json())
            future.get(timeout=10)
            logger.info(f"OCR result sent for task {result.task_id}")
        except Exception as e:
            logger.error(f"Failed to send result: {e}")

    def _process_message(self, message: dict) -> dict:
        return {"status": "processed"}

    def _get_health_status(self) -> dict:
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "service": "ocr_service",
            "consumer_active": self.consumer is not None and self.consumer._running
            if self.consumer
            else False,
        }

    def start(self) -> None:
        logger.info("Starting OCR Service...")
        try:
            self._initialize()
            self._running = True
            logger.info("OCR Service started successfully")

            while self._running:
                logger.debug("Main loop iteration...")
                self._shutdown_event.wait(timeout=1)
            logger.info("Main loop ended")

        except Exception as e:
            logger.error(f"Error starting service: {e}")
            raise

    def stop(self) -> None:
        logger.info("Stopping OCR Service...")
        self._running = False
        self._shutdown_event.set()

        if self.consumer:
            self.consumer.stop()
        if self._result_producer:
            self._result_producer.close()

        logger.info("OCR Service stopped")


def main():
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    service = OCRService()
    try:
        service.start()
    except KeyboardInterrupt:
        service.stop()


if __name__ == "__main__":
    main()
