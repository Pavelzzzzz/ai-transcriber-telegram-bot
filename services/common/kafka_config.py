import os
from typing import Optional
from dataclasses import dataclass


@dataclass
class KafkaConfig:
    bootstrap_servers: str
    client_id: str
    topics: dict
    
    @classmethod
    def from_env(cls) -> 'KafkaConfig':
        return cls(
            bootstrap_servers=os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
            client_id=os.getenv('KAFKA_CLIENT_ID', 'ai-transcriber'),
            topics={
                'tasks_ocr': os.getenv('KAFKA_TOPIC_OCR_TASKS', 'tasks.ocr'),
                'tasks_transcribe': os.getenv('KAFKA_TOPIC_TRANSCRIBE_TASKS', 'tasks.transcribe'),
                'tasks_tts': os.getenv('KAFKA_TOPIC_TTS_TASKS', 'tasks.tts'),
                'tasks_image_gen': os.getenv('KAFKA_TOPIC_IMAGE_GEN_TASKS', 'tasks.image_gen'),
                'results_ocr': os.getenv('KAFKA_TOPIC_OCR_RESULTS', 'results.ocr'),
                'results_transcribe': os.getenv('KAFKA_TOPIC_TRANSCRIBE_RESULTS', 'results.transcribe'),
                'results_tts': os.getenv('KAFKA_TOPIC_TTS_RESULTS', 'results.tts'),
                'results_image_gen': os.getenv('KAFKA_TOPIC_IMAGE_GEN_RESULTS', 'results.image_gen'),
                'notifications': os.getenv('KAFKA_TOPIC_NOTIFICATIONS', 'notifications'),
            }
        )


kafka_config = KafkaConfig.from_env()
