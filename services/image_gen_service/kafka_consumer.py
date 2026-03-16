import logging
import asyncio
from typing import Callable
from threading import Thread

from ..common import KafkaConsumerError, TaskMessage, ResultMessage, TaskStatus, kafka_config
from .processor import ImageGenerationProcessor

logger = logging.getLogger(__name__)


class ImageGenKafkaConsumer:
    def __init__(self, config, result_sender: Callable[[ResultMessage], None], processor=None):
        self.config = config
        self.result_sender = result_sender
        self.processor = processor if processor else ImageGenerationProcessor()
        self._consumer = None
        self._running = False
        self._thread = None
    
    def _get_consumer(self):
        if self._consumer is None:
            try:
                from kafka import KafkaConsumer
                self._consumer = KafkaConsumer(
                    self.config.topics['tasks_image_gen'],
                    bootstrap_servers=self.config.bootstrap_servers,
                    client_id=f"{self.config.client_id}_image_gen_consumer",
                    value_deserializer=lambda v: v.decode('utf-8'),
                    auto_offset_reset='earliest',
                    group_id=f"{self.config.client_id}_image_gen_group",
                    max_poll_interval_ms=900000,
                    max_poll_records=1,
                    session_timeout_ms=30000,
                    heartbeat_interval_ms=10000
                )
            except Exception as e:
                raise KafkaConsumerError(f"Failed to create Kafka consumer: {e}", "image_gen_service")
        return self._consumer
    
    async def _process_task(self, task: TaskMessage) -> ResultMessage:
        try:
            prompt = task.file_path
            metadata = task.metadata or {}
            
            result = await self.processor.generate_image(prompt, metadata)
            
            return ResultMessage(
                task_id=task.task_id,
                status=TaskStatus.SUCCESS,
                result_type="image",
                result_data=result
            )
        except Exception as e:
            logger.error(f"Failed to process image generation task {task.task_id}: {e}")
            return ResultMessage(
                task_id=task.task_id,
                status=TaskStatus.FAILED,
                result_type="image",
                result_data={},
                error=str(e)
            )
    
    def _consume_loop(self):
        consumer = self._get_consumer()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        while self._running:
            try:
                messages = consumer.poll(timeout_ms=1000)
                for topic_partition, records in messages.items():
                    for record in records:
                        try:
                            task = TaskMessage.from_json(record.value)
                            logger.info(f"Processing image generation task: {task.task_id}")
                            
                            result = loop.run_until_complete(self._process_task(task))
                            self.result_sender(result)
                            
                        except Exception as e:
                            logger.error(f"Error processing message: {e}")
            except Exception as e:
                logger.error(f"Error in consumer loop: {e}")
                if self._running:
                    import time
                    time.sleep(1)
        
        loop.close()
    
    def start(self):
        if self._running:
            return
        
        self._running = True
        self._thread = Thread(target=self._consume_loop, daemon=True)
        self._thread.start()
        logger.info("Image Generation Kafka consumer started")
    
    def stop(self):
        self._running = False
        if self._consumer:
            self._consumer.close()
            self._consumer = None
        logger.info("Image Generation Kafka consumer stopped")
