import logging
import signal
import sys
import time

from ..common import ResultMessage, kafka_config
from .kafka_consumer import ReceiptKafkaConsumer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


class ReceiptService:
    def __init__(self):
        self.consumer = None
        self._producer = None
        self._running = True

    def _get_producer(self):
        if self._producer is None:
            from kafka import KafkaProducer

            self._producer = KafkaProducer(
                bootstrap_servers=kafka_config.bootstrap_servers,
                client_id=f"{kafka_config.client_id}_receipt_producer",
                value_serializer=lambda v: v.encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
            )
        return self._producer

    def send_result(self, result: ResultMessage):
        try:
            producer = self._get_producer()
            topic = kafka_config.topics["results_receipt"]

            future = producer.send(topic, key=str(result.task_id), value=result.to_json())
            future.get(timeout=10)
            logger.info(f"Receipt result sent for task {result.task_id}")
        except Exception as e:
            logger.error(f"Failed to send result: {e}")

    def start(self):
        logger.info("Starting Receipt Service...")

        self.consumer = ReceiptKafkaConsumer(kafka_config, result_sender=self.send_result)

        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            self._running = False
            self.consumer.stop()
            if self._producer:
                self._producer.close()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        self.consumer.start()
        logger.info("Receipt Service started successfully")

        while self._running:
            time.sleep(1)

    def stop(self):
        logger.info("Stopping Receipt Service...")
        self._running = False
        if self.consumer:
            self.consumer.stop()
        if self._producer:
            self._producer.close()
        logger.info("Receipt Service stopped")


def main():
    service = ReceiptService()
    try:
        service.start()
    except KeyboardInterrupt:
        service.stop()


if __name__ == "__main__":
    main()
