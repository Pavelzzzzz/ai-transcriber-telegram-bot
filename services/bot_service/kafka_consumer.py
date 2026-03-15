import logging
import asyncio
from typing import Callable, Optional, Dict, Any
from threading import Thread

from ..common import KafkaConsumerError, ResultMessage, TaskStatus, kafka_config

logger = logging.getLogger(__name__)


class ResultConsumer:
    def __init__(self, config, result_callback: Callable[[ResultMessage], None]):
        self.config = config
        self.result_callback = result_callback
        self._consumer = None
        self._running = False
        self._thread = None
    
    def _get_consumer(self):
        if self._consumer is None:
            try:
                from kafka import KafkaConsumer
                self._consumer = KafkaConsumer(
                    self.config.topics['results_ocr'],
                    self.config.topics['results_transcribe'],
                    self.config.topics['results_tts'],
                    self.config.topics['results_image_gen'],
                    bootstrap_servers=self.config.bootstrap_servers,
                    client_id=f"{self.config.client_id}_consumer",
                    value_deserializer=lambda v: v.decode('utf-8'),
                    auto_offset_reset='latest',
                    group_id=f"{self.config.client_id}_bot_group"
                )
            except Exception as e:
                raise KafkaConsumerError(f"Failed to create Kafka consumer: {e}", "bot_service")
        return self._consumer
    
    def _process_message(self, message):
        try:
            result = ResultMessage.from_json(message.value)
            logger.info(f"Received result for task {result.task_id}: {result.status}")
            self.result_callback(result)
        except Exception as e:
            logger.error(f"Failed to process message: {e}")
    
    def _consume_loop(self):
        consumer = self._get_consumer()
        while self._running:
            try:
                messages = consumer.poll(timeout_ms=1000)
                for topic_partition, records in messages.items():
                    for record in records:
                        self._process_message(record)
            except Exception as e:
                logger.error(f"Error in consumer loop: {e}")
                if self._running:
                    asyncio.sleep(1)
    
    def start(self):
        if self._running:
            return
        
        self._running = True
        self._thread = Thread(target=self._consume_loop, daemon=True)
        self._thread.start()
        logger.info("Result consumer started")
    
    def stop(self):
        self._running = False
        if self._consumer:
            self._consumer.close()
            self._consumer = None
        logger.info("Result consumer stopped")
