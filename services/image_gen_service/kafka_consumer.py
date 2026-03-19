import logging
import asyncio
import uuid
import os
from typing import Callable, Dict
from threading import Thread, Lock
from concurrent.futures import ThreadPoolExecutor, Future

from ..common import KafkaConsumerError, TaskMessage, ResultMessage, TaskStatus, kafka_config
from .processor import ImageGenerationProcessor

logger = logging.getLogger(__name__)

MAX_WORKERS = int(os.getenv('IMAGE_GEN_MAX_WORKERS', '2'))


class ImageGenKafkaConsumer:
    def __init__(self, config, result_sender: Callable[[ResultMessage], None], processor=None):
        self.config = config
        self.result_sender = result_sender
        self.processor = processor if processor else ImageGenerationProcessor()
        self._consumer = None
        self._running = False
        self._thread = None
        self._executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
        self._pending_tasks: Dict[str, Future] = {}
        self._tasks_lock = Lock()
        self._notification_sender: Callable[[str, str], None] | None = None
    
    def set_notification_sender(self, sender: Callable[[str, str], None]):
        self._notification_sender = sender
    
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
                    max_poll_interval_ms=10800000,
                    max_poll_records=10,
                    session_timeout_ms=30000,
                    heartbeat_interval_ms=10000
                )
            except Exception as e:
                raise KafkaConsumerError(f"Failed to create Kafka consumer: {e}", "image_gen_service")
        return self._consumer
    
    def _get_queue_status(self) -> dict:
        with self._tasks_lock:
            pending = len(self._pending_tasks)
            processing = sum(1 for f in self._pending_tasks.values() if not f.done())
            completed = sum(1 for f in self._pending_tasks.values() if f.done())
            
            tasks_detail = []
            for task_id, future in self._pending_tasks.items():
                status = "completed" if future.done() else ("processing" if future.running() else "queued")
                tasks_detail.append({"task_id": task_id, "status": status})
        
        return {
            "pending": pending,
            "processing": processing,
            "completed": completed,
            "max_workers": MAX_WORKERS,
            "tasks": tasks_detail
        }
    
    def _send_started_notification(self, task: TaskMessage):
        if self._notification_sender:
            try:
                user_id = str(task.user_id or task.metadata.get('user_id', 'unknown'))
                self._notification_sender(
                    user_id,
                    f"🔄 Started processing: {task.task_id[:8]}...\n📝 Prompt: {task.file_path[:50]}..."
                )
            except Exception as e:
                logger.warning(f"Failed to send started notification: {e}")
    
    def _submit_task(self, task: TaskMessage) -> Future:
        task_id = task.task_id
        placeholder_future: Future = Future()
        placeholder_future.set_result(None)
        
        with self._tasks_lock:
            self._pending_tasks[task_id] = placeholder_future
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        future = self._executor.submit(self._run_task_sync, task, loop)
        
        with self._tasks_lock:
            self._pending_tasks[task_id] = future
        
        future.add_done_callback(lambda f: self._cleanup_task(task_id, f))
        
        return future
    
    def _run_task_sync(self, task: TaskMessage, loop: asyncio.AbstractEventLoop) -> ResultMessage:
        try:
            return loop.run_until_complete(self._process_task(task))
        finally:
            loop.close()
    
    def _cleanup_task(self, task_id: str, future: Future):
        try:
            if future.done() and not future.cancelled():
                result = future.result()
                if result and self.result_sender:
                    self.result_sender(result)
                    logger.info(f"Result sent for task {task_id}")
        except Exception as e:
            logger.error(f"Error sending result for task {task_id}: {e}")
        finally:
            with self._tasks_lock:
                if task_id in self._pending_tasks:
                    del self._pending_tasks[task_id]
            logger.info(f"Task {task_id} removed from pending queue")
    
    async def _process_task(self, task: TaskMessage) -> ResultMessage:
        try:
            prompt = task.file_path
            metadata = task.metadata or {}
            
            self._send_started_notification(task)
            
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
        
        while self._running:
            try:
                messages = consumer.poll(timeout_ms=1000)
                for topic_partition, records in messages.items():
                    for record in records:
                        try:
                            task = TaskMessage.from_json(record.value)
                            logger.info(f"Received image generation task: {task.task_id}")
                            
                            self._submit_task(task)
                            
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
        logger.info(f"Image Generation Kafka consumer started with {MAX_WORKERS} workers")
    
    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        self._executor.shutdown(wait=True)
        if self._consumer:
            self._consumer.close()
            self._consumer = None
        logger.info("Image Generation Kafka consumer stopped")
