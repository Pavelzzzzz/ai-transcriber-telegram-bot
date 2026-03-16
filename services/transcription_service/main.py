import logging
import os
import signal
from threading import Event

from services.common import kafka_config, ResultMessage, KafkaProducerError
from services.common.base_service import BaseService
from .kafka_consumer import TranscriptionKafkaConsumer

logger = logging.getLogger(__name__)


class TranscriptionService(BaseService):
    def __init__(self):
        super().__init__("transcription_service")
        self.model_name = os.getenv('WHISPER_MODEL', 'base')
        self.consumer = None
        self._result_producer = None
        self._initialized = False
        
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        logger.info(f"Received signal {signum}, initiating shutdown...")
        self.stop()
    
    def _initialize(self) -> None:
        logger.info(f"Initializing Transcription Service with model: {self.model_name}...")
        self.consumer = TranscriptionKafkaConsumer(kafka_config, self.send_result, self.model_name)
        self.consumer.start()
        self._initialized = True
        logger.info("Transcription Service initialized")
    
    def _get_result_producer(self):
        if self._result_producer is None:
            try:
                from kafka import KafkaProducer
                self._result_producer = KafkaProducer(
                    bootstrap_servers=kafka_config.bootstrap_servers,
                    client_id=f"{kafka_config.client_id}_transcribe_producer",
                    value_serializer=lambda v: v.encode('utf-8'),
                    key_serializer=lambda k: k.encode('utf-8') if k else None
                )
            except Exception as e:
                raise KafkaProducerError(f"Failed to create result producer: {e}", "transcription_service")
        return self._result_producer
    
    def send_result(self, result: ResultMessage):
        try:
            producer = self._get_result_producer()
            topic = kafka_config.topics['results_transcribe']
            
            future = producer.send(
                topic,
                key=str(result.task_id),
                value=result.to_json()
            )
            future.get(timeout=10)
            logger.info(f"Transcription result sent for task {result.task_id}")
        except Exception as e:
            logger.error(f"Failed to send result: {e}")
    
    def _process_message(self, message: dict) -> dict:
        return {"status": "processed"}
    
    def _get_health_status(self) -> dict:
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "service": "transcription_service",
            "model": self.model_name,
            "consumer_active": self.consumer is not None and self.consumer._running if self.consumer else False
        }
    
    def start(self) -> None:
        logger.info("Starting Transcription Service...")
        try:
            self._initialize()
            self._running = True
            logger.info("Transcription Service started successfully")
            
            while self._running:
                self._shutdown_event.wait(timeout=1)
                    
        except Exception as e:
            logger.error(f"Error starting service: {e}")
            raise
    
    def stop(self) -> None:
        logger.info("Stopping Transcription Service...")
        self._running = False
        self._shutdown_event.set()
        
        if self.consumer:
            self.consumer.stop()
        if self._result_producer:
            self._result_producer.close()
        
        logger.info("Transcription Service stopped")


def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    service = TranscriptionService()
    try:
        service.start()
    except KeyboardInterrupt:
        service.stop()


if __name__ == '__main__':
    main()
