import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.common import kafka_config, ResultMessage, KafkaProducerError
from .kafka_consumer import TTSKafkaConsumer

logger = logging.getLogger(__name__)


class TTSService:
    def __init__(self, language: str = "ru"):
        self.language = language
        self.consumer = None
        self._result_producer = None
    
    def _get_result_producer(self):
        if self._result_producer is None:
            try:
                from kafka import KafkaProducer
                self._result_producer = KafkaProducer(
                    bootstrap_servers=kafka_config.bootstrap_servers,
                    client_id=f"{kafka_config.client_id}_tts_producer",
                    value_serializer=lambda v: v.encode('utf-8'),
                    key_serializer=lambda k: k.encode('utf-8') if k else None
                )
            except Exception as e:
                raise KafkaProducerError(f"Failed to create result producer: {e}", "tts_service")
        return self._result_producer
    
    def send_result(self, result: ResultMessage):
        try:
            producer = self._get_result_producer()
            topic = kafka_config.topics['results_tts']
            
            future = producer.send(
                topic,
                key=str(result.task_id),
                value=result.to_json()
            )
            future.get(timeout=10)
            logger.info(f"TTS result sent for task {result.task_id}")
        except Exception as e:
            logger.error(f"Failed to send result: {e}")
    
    def start(self):
        logger.info(f"Starting TTS Service with language: {self.language}...")
        self.consumer = TTSKafkaConsumer(kafka_config, self.send_result, self.language)
        self.consumer.start()
        logger.info("TTS Service started successfully")
    
    def stop(self):
        logger.info("Stopping TTS Service...")
        if self.consumer:
            self.consumer.stop()
        if self._result_producer:
            self._result_producer.close()
        logger.info("TTS Service stopped")


def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    language = os.getenv('TTS_LANGUAGE', 'ru')
    service = TTSService(language)
    try:
        service.start()
    except KeyboardInterrupt:
        service.stop()


if __name__ == '__main__':
    main()
