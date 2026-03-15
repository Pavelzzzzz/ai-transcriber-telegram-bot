import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.common import kafka_config, ResultMessage, KafkaProducerError
from .kafka_consumer import TranscriptionKafkaConsumer

logger = logging.getLogger(__name__)


class TranscriptionService:
    def __init__(self, model_name: str = "base"):
        self.model_name = model_name
        self.consumer = None
        self._result_producer = None
    
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
    
    def start(self):
        logger.info(f"Starting Transcription Service with model: {self.model_name}...")
        self.consumer = TranscriptionKafkaConsumer(kafka_config, self.send_result, self.model_name)
        self.consumer.start()
        logger.info("Transcription Service started successfully")
    
    def stop(self):
        logger.info("Stopping Transcription Service...")
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
    
    model_name = os.getenv('WHISPER_MODEL', 'base')
    service = TranscriptionService(model_name)
    try:
        service.start()
    except KeyboardInterrupt:
        service.stop()


if __name__ == '__main__':
    main()
