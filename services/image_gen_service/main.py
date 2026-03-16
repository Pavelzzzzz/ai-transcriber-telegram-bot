import logging
import os
import signal
import threading
from threading import Event
from http.server import HTTPServer, BaseHTTPRequestHandler

from services.common import kafka_config, ResultMessage, KafkaProducerError
from services.common.base_service import BaseService
from .kafka_consumer import ImageGenKafkaConsumer
from .processor import ImageGenerationProcessor

logger = logging.getLogger(__name__)


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/metrics':
            from services.common.metrics import get_metrics_collector
            collector = get_metrics_collector("image_gen_service")
            metrics = collector.get_metrics()
            
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(metrics.encode())
        else:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "ok", "service": "image_gen_service"}')
    
    def log_message(self, format, *args):
        pass


def start_health_server(port=8080):
    server = HTTPServer(('', port), HealthHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()


class ImageGenerationService(BaseService):
    def __init__(self):
        super().__init__("image_gen_service")
        self.model_id = os.getenv('SDXL_MODEL_ID', 'stabilityai/stable-diffusion-xl-base-1.0')
        self.default_model = os.getenv('DEFAULT_MODEL', 'sd15')
        self.consumer = None
        self._result_producer = None
        self._processor = None
        self._shutdown_event = Event()
        self._initialized = False
        
        start_health_server()
        
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        logger.info(f"Received signal {signum}, initiating shutdown...")
        self.stop()
    
    def _preload_model(self) -> None:
        """Preload the default model on service startup"""
        logger.info(f"Preloading default model: {self.default_model}")
        try:
            if self._processor is None:
                self._processor = ImageGenerationProcessor()
            
            self._processor._get_pipeline_for_model(self.default_model)
            logger.info(f"Model {self.default_model} preloaded successfully")
        except Exception as e:
            logger.error(f"Failed to preload model {self.default_model}: {e}")
            raise
    
    def _initialize(self) -> None:
        logger.info(f"Initializing Image Generation Service...")
        
        self._preload_model()
        
        self.consumer = ImageGenKafkaConsumer(kafka_config, self.send_result, self._processor)
        self.consumer.start()
        self._initialized = True
        logger.info("Image Generation Service initialized")
    
    def _get_result_producer(self):
        if self._result_producer is None:
            try:
                from kafka import KafkaProducer
                self._result_producer = KafkaProducer(
                    bootstrap_servers=kafka_config.bootstrap_servers,
                    client_id=f"{kafka_config.client_id}_image_gen_producer",
                    value_serializer=lambda v: v.encode('utf-8'),
                    key_serializer=lambda k: k.encode('utf-8') if k else None
                )
            except Exception as e:
                raise KafkaProducerError(f"Failed to create result producer: {e}", "image_gen_service")
        return self._result_producer
    
    def send_result(self, result: ResultMessage):
        try:
            producer = self._get_result_producer()
            topic = kafka_config.topics['results_image_gen']
            
            future = producer.send(
                topic,
                key=str(result.task_id),
                value=result.to_json()
            )
            future.get(timeout=10)
            logger.info(f"Image generation result sent for task {result.task_id}")
        except Exception as e:
            logger.error(f"Failed to send result: {e}")
    
    def _process_message(self, message: dict) -> dict:
        return {"status": "processed"}
    
    def _get_health_status(self) -> dict:
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "service": "image_gen_service",
            "model": self.model_id,
            "consumer_active": self.consumer is not None and self.consumer._running if self.consumer else False
        }
    
    def start(self) -> None:
        logger.info(f"Starting Image Generation Service...")
        try:
            self._initialize()
            self._running = True
            logger.info("Image Generation Service started successfully")
            
            while self._running:
                self._shutdown_event.wait(timeout=1)
                    
        except Exception as e:
            logger.error(f"Error starting service: {e}")
            raise
    
    def stop(self) -> None:
        logger.info("Stopping Image Generation Service...")
        self._running = False
        self._shutdown_event.set()
        
        if self.consumer:
            self.consumer.stop()
        if self._result_producer:
            self._result_producer.close()
        
        logger.info("Image Generation Service stopped")


def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    service = ImageGenerationService()
    try:
        service.start()
    except KeyboardInterrupt:
        service.stop()


if __name__ == '__main__':
    main()
