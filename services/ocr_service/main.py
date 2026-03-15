import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.common import kafka_config, ResultMessage, KafkaProducerError
from .kafka_consumer import OCRKafkaConsumer

logger = logging.getLogger(__name__)


class OCRService:
    def __init__(self):
        self.consumer = None
        self._result_producer = None
    
    def _get_result_producer(self):
        if self._result_producer is None:
            try:
                from kafka import KafkaProducer
                self._result_producer = KafkaProducer(
                    bootstrap_servers=kafka_config.bootstrap_servers,
                    client_id=f"{kafka_config.client_id}_ocr_producer",
                    value_serializer=lambda v: v.encode('utf-8'),
                    key_serializer=lambda k: k.encode('utf-8') if k else None
                )
            except Exception as e:
                raise KafkaProducerError(f"Failed to create result producer: {e}", "ocr_service")
        return self._result_producer
    
    def send_result(self, result: ResultMessage):
        try:
            producer = self._get_result_producer()
            topic = kafka_config.topics['results_ocr']
            
            future = producer.send(
                topic,
                key=str(result.task_id),
                value=result.to_json()
            )
            future.get(timeout=10)
            logger.info(f"OCR result sent for task {result.task_id}")
        except Exception as e:
            logger.error(f"Failed to send result: {e}")
    
    def start(self):
        logger.info("Starting OCR Service...")
        self.consumer = OCRKafkaConsumer(kafka_config, self.send_result)
        self.consumer.start()
        logger.info("OCR Service started successfully")
    
    def stop(self):
        logger.info("Stopping OCR Service...")
        if self.consumer:
            self.consumer.stop()
        if self._result_producer:
            self._result_producer.close()
        logger.info("OCR Service stopped")


def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    service = OCRService()
    try:
        service.start()
    except KeyboardInterrupt:
        service.stop()


if __name__ == '__main__':
    main()
