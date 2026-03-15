import logging
import asyncio
from typing import Callable
from threading import Thread

from ..common import KafkaConsumerError, TaskMessage, ResultMessage, TaskStatus, kafka_config
from .processor import TTSProcessor

logger = logging.getLogger(__name__)


class TTSKafkaConsumer:
    def __init__(self, config, result_sender: Callable[[ResultMessage], None], language: str = "ru"):
        self.config = config
        self.result_sender = result_sender
        self.processor = TTSProcessor(language)
        self._consumer = None
        self._running = False
        self._thread = None
    
    def _get_consumer(self):
        if self._consumer is None:
            try:
                from kafka import KafkaConsumer
                self._consumer = KafkaConsumer(
                    self.config.topics['tasks_tts'],
                    bootstrap_servers=self.config.bootstrap_servers,
                    client_id=f"{self.config.client_id}_tts_consumer",
                    value_deserializer=lambda v: v.decode('utf-8'),
                    auto_offset_reset='earliest',
                    group_id=f"{self.config.client_id}_tts_group"
                )
            except Exception as e:
                raise KafkaConsumerError(f"Failed to create Kafka consumer: {e}", "tts_service")
        return self._consumer
    
    def _process_task(self, task: TaskMessage) -> ResultMessage:
        try:
            language = task.metadata.get('language', self.processor.language)
            self.processor.language = language
            
            result = self.processor.generate_speech_async(task.file_path)
            
            return ResultMessage(
                task_id=task.task_id,
                status=TaskStatus.SUCCESS,
                result_type="audio",
                result_data=result
            )
        except Exception as e:
            logger.error(f"Failed to process TTS task {task.task_id}: {e}")
            return ResultMessage(
                task_id=task.task_id,
                status=TaskStatus.FAILED,
                result_type="audio",
                result_data={},
                error=str(e)
            )
    
    def _consume_loop(self):
        consumer = self._get_consumer()
        
        while self._running:
            try:
                messages = consumer.poll(timeout_ms=1000)
                for topic_partition, records in messages.items():
                    for record in records:
                        try:
                            task = TaskMessage.from_json(record.value)
                            logger.info(f"Processing TTS task: {task.task_id}")
                            
                            result = self._process_task(task)
                            self.result_sender(result)
                            
                        except Exception as e:
                            logger.error(f"Error processing message: {e}")
            except Exception as e:
                logger.error(f"Error in consumer loop: {e}")
                if self._running:
                    import time
                    time.sleep(1)
    
    def start(self):
        if self._running:
            return
        
        self._running = True
        self._thread = Thread(target=self._consume_loop, daemon=True)
        self._thread.start()
        logger.info("TTS Kafka consumer started")
    
    def stop(self):
        self._running = False
        if self._consumer:
            self._consumer.close()
            self._consumer = None
        logger.info("TTS Kafka consumer stopped")
