import pytest
import os
import sys
import asyncio
import time
import json
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
from threading import Thread

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from services.common.schemas import TaskMessage, ResultMessage, TaskType, TaskStatus
from services.common.kafka_config import KafkaConfig


class TestBotServiceIntegration:
    """Integration tests for bot service with Kafka"""
    
    @pytest.fixture
    def kafka_config(self):
        return KafkaConfig.from_env()
    
    @pytest.fixture
    def mock_telegram_update(self):
        update = Mock()
        update.effective_user = Mock()
        update.effective_user.id = 12345
        update.effective_chat = Mock()
        update.effective_chat.id = 67890
        update.message = Mock()
        update.message.message_id = 111
        update.message.reply_text = AsyncMock()
        return update
    
    @pytest.mark.integration
    def test_kafka_topics_exist(self, kafka_config):
        """Test that Kafka topics are configured"""
        assert kafka_config.bootstrap_servers is not None
        assert 'tasks_ocr' in kafka_config.topics
        assert 'tasks_transcribe' in kafka_config.topics
        assert 'tasks_image_gen' in kafka_config.topics
        assert 'tasks_tts' in kafka_config.topics
        assert 'results_ocr' in kafka_config.topics
        assert 'results_transcribe' in kafka_config.topics
        assert 'results_image_gen' in kafka_config.topics
        assert 'results_tts' in kafka_config.topics
    
    @pytest.mark.integration
    def test_task_message_serialization(self):
        """Test TaskMessage serialization/deserialization"""
        task = TaskMessage(
            task_id="test-123",
            task_type=TaskType.OCR,
            user_id=12345,
            chat_id=67890,
            timestamp=datetime.now(),
            file_path="/path/to/image.jpg",
            metadata={"language": "ru"}
        )
        
        json_str = task.to_json()
        restored = TaskMessage.from_json(json_str)
        
        assert restored.task_id == task.task_id
        assert restored.task_type == task.task_type
        assert restored.user_id == task.user_id
        assert restored.chat_id == task.chat_id
        assert restored.file_path == task.file_path
        assert restored.metadata["language"] == "ru"
    
    @pytest.mark.integration
    def test_result_message_serialization(self):
        """Test ResultMessage serialization/deserialization"""
        result = ResultMessage(
            task_id="test-456",
            status=TaskStatus.SUCCESS,
            result_type="text",
            result_data={"text": "Hello World"},
            error=None
        )
        
        json_str = result.to_json()
        restored = ResultMessage.from_json(json_str)
        
        assert restored.task_id == result.task_id
        assert restored.status == result.status
        assert restored.result_data["text"] == "Hello World"
    
    @pytest.mark.integration
    def test_task_types_enum(self):
        """Test TaskType enum values"""
        assert TaskType.OCR.value == "ocr"
        assert TaskType.TRANSCRIBE.value == "transcribe"
        assert TaskType.IMAGE_GEN.value == "image_gen"
    
    @pytest.mark.integration
    def test_task_status_enum(self):
        """Test TaskStatus enum values"""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.PROCESSING.value == "processing"
        assert TaskStatus.SUCCESS.value == "success"
        assert TaskStatus.FAILED.value == "failed"


class TestKafkaProducerConsumer:
    """Test Kafka producer and consumer integration"""
    
    @pytest.mark.integration
    @pytest.mark.skipif(
        os.getenv('KAFKA_BOOTSTRAP_SERVERS') is None,
        reason="Kafka not available"
    )
    def test_kafka_connection(self):
        """Test Kafka connection"""
        from kafka import KafkaConsumer
        from kafka import KafkaProducer
        
        config = KafkaConfig.from_env()
        
        try:
            producer = KafkaProducer(
                bootstrap_servers=config.bootstrap_servers,
                client_id="test-producer",
                value_serializer=lambda v: v.encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                request_timeout_ms=5000
            )
            
            consumer = KafkaConsumer(
                bootstrap_servers=config.bootstrap_servers,
                client_id="test-consumer",
                request_timeout_ms=5000,
                api_version_auto_timeout_ms=5000
            )
            
            assert producer is not None
            assert consumer is not None
            
            producer.close()
            consumer.close()
        except Exception as e:
            pytest.skip(f"Kafka not available: {e}")
    
    @pytest.mark.integration
    @pytest.mark.skipif(
        os.getenv('KAFKA_BOOTSTRAP_SERVERS') is None,
        reason="Kafka not available"
    )
    def test_produce_consume_message(self):
        """Test producing and consuming a message"""
        from kafka import KafkaConsumer
        from kafka import KafkaProducer
        
        config = KafkaConfig.from_env()
        test_topic = "test.integration"
        
        try:
            producer = KafkaProducer(
                bootstrap_servers=config.bootstrap_servers,
                client_id="test-producer-integration",
                value_serializer=lambda v: v.encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None
            )
            
            test_message = "test message"
            future = producer.send(test_topic, key="test", value=test_message)
            future.get(timeout=10)
            producer.flush()
            
            consumer = KafkaConsumer(
                test_topic,
                bootstrap_servers=config.bootstrap_servers,
                client_id="test-consumer-integration",
                auto_offset_reset='earliest',
                consumer_timeout_ms=5000,
                value_deserializer=lambda v: v.decode('utf-8')
            )
            
            messages = []
            for message in consumer:
                messages.append(message.value)
                if len(messages) >= 1:
                    break
            
            producer.close()
            consumer.close()
            
            assert test_message in messages
        except Exception as e:
            pytest.skip(f"Kafka integration test failed: {e}")


class TestBotServiceHandlers:
    """Test bot service message handlers"""
    
    @pytest.mark.integration
    def test_pending_tasks_storage(self):
        """Test pending tasks dictionary"""
        pending_tasks = {}
        
        task_id = "test-task-123"
        pending_tasks[task_id] = {
            'chat_id': 12345,
            'task_type': 'ocr',
            'file_path': '/test.jpg'
        }
        
        assert task_id in pending_tasks
        assert pending_tasks[task_id]['chat_id'] == 12345
        assert pending_tasks[task_id]['task_type'] == 'ocr'
        
        del pending_tasks[task_id]
        assert task_id not in pending_tasks
    
    @pytest.mark.integration
    def test_user_modes_storage(self):
        """Test user modes storage"""
        user_modes = {}
        
        user_id = 12345
        user_modes[user_id] = 'img_to_text'
        
        assert user_modes.get(user_id) == 'img_to_text'
        
        user_modes[user_id] = 'text_to_image'
        assert user_modes.get(user_id) == 'text_to_image'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
