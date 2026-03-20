import logging
import signal
import sys

from .kafka_consumer import ReceiptKafkaConsumer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def main():
    logger.info("Starting Receipt Service...")

    consumer = ReceiptKafkaConsumer()

    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        consumer.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("Receipt Service started successfully")
    consumer.start()


if __name__ == "__main__":
    main()
