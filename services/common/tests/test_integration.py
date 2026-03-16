import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestTaskQueueRepo:
    """Tests for task queue repository"""
    
    @pytest.fixture
    def mock_db_url(self, monkeypatch):
        monkeypatch.setenv(
            "DATABASE_URL", 
            "postgresql://bot:secret@localhost:5432/ai_transcriber"
        )
    
    @pytest.mark.integration
    def test_task_queue_functions_exist(self):
        """Test that task queue functions exist"""
        from services.common import task_queue_repo
        
        assert hasattr(task_queue_repo, 'add_task')
        assert hasattr(task_queue_repo, 'get_user_tasks')
        assert hasattr(task_queue_repo, 'update_task_status')
        assert hasattr(task_queue_repo, 'cancel_task')
        assert hasattr(task_queue_repo, 'update_task_priority')
        assert hasattr(task_queue_repo, 'get_pending_tasks')
    
    @pytest.mark.integration
    def test_task_queue_item_class_exists(self):
        """Test TaskQueueItem class exists"""
        from services.common.task_queue_repo import TaskQueueItem
        
        assert TaskQueueItem is not None
        assert hasattr(TaskQueueItem, 'task_id')
        assert hasattr(TaskQueueItem, 'user_id')
        assert hasattr(TaskQueueItem, 'task_type')
        assert hasattr(TaskQueueItem, 'status')
        assert hasattr(TaskQueueItem, 'priority')


class TestUserSettingsRepo:
    """Tests for user settings repository"""
    
    @pytest.mark.integration
    def test_user_settings_functions_exist(self):
        """Test that user settings functions exist"""
        from services.common import user_settings_repo
        
        assert hasattr(user_settings_repo, 'get_or_create_user_settings')
        assert hasattr(user_settings_repo, 'update_user_settings')
        assert hasattr(user_settings_repo, 'reset_user_settings')
    
    @pytest.mark.integration
    def test_user_settings_class_exists(self):
        """Test UserSettings class exists"""
        from services.common.user_settings_repo import UserSettings
        
        assert UserSettings is not None
        assert hasattr(UserSettings, 'user_id')
        assert hasattr(UserSettings, 'image_model')
        assert hasattr(UserSettings, 'image_style')
        assert hasattr(UserSettings, 'aspect_ratio')


class TestDatabaseConnection:
    """Tests for database connection"""
    
    @pytest.mark.integration
    @pytest.mark.skipif(
        os.getenv('DATABASE_URL') is None,
        reason="Database URL not configured"
    )
    def test_database_connection(self):
        """Test database connection"""
        from services.common.database import get_database_engine
        
        engine = get_database_engine()
        assert engine is not None
        
        try:
            conn = engine.connect()
            conn.close()
        except Exception as e:
            pytest.skip(f"Database not available: {e}")


class TestHardwareDetection:
    """Tests for hardware detection"""
    
    @pytest.mark.integration
    def test_hardware_functions_exist(self):
        """Test hardware detection functions exist"""
        from services.common import hardware
        
        assert hasattr(hardware, 'get_compute_device')
        assert hasattr(hardware, 'get_vram_gb')
        assert hasattr(hardware, 'get_available_models')
        assert hasattr(hardware, 'is_model_available')
        assert hasattr(hardware, 'get_model_display_name')
    
    @pytest.mark.integration
    def test_models_config_exists(self):
        """Test models configuration exists"""
        from services.common.hardware import MODELS_CONFIG
        
        assert 'sd15' in MODELS_CONFIG
        assert 'sdxl' in MODELS_CONFIG
        assert 'flux' in MODELS_CONFIG
    
    @pytest.mark.integration
    def test_styles_config_exists(self):
        """Test styles configuration exists"""
        from services.common.hardware import STYLES_CONFIG
        
        assert isinstance(STYLES_CONFIG, dict)
    
    @pytest.mark.integration
    def test_aspect_ratios_exist(self):
        """Test aspect ratios exist"""
        from services.common.hardware import ASPECT_RATIO_SIZES
        
        assert '1:1' in ASPECT_RATIO_SIZES
        assert '16:9' in ASPECT_RATIO_SIZES
        assert '9:16' in ASPECT_RATIO_SIZES


class TestSchemas:
    """Tests for data schemas"""
    
    @pytest.mark.integration
    def test_task_message_schema(self):
        """Test TaskMessage schema"""
        from services.common.schemas import TaskMessage, TaskType
        from datetime import datetime
        
        task = TaskMessage(
            task_id="test-123",
            task_type=TaskType.IMAGE_GEN,
            user_id=12345,
            chat_id=67890,
            timestamp=datetime.now(),
            file_path="test prompt",
            metadata={"model": "sd15"}
        )
        
        assert task.task_id == "test-123"
        assert task.task_type == TaskType.IMAGE_GEN
        assert task.user_id == 12345
        assert task.metadata["model"] == "sd15"
    
    @pytest.mark.integration
    def test_result_message_schema(self):
        """Test ResultMessage schema"""
        from services.common.schemas import ResultMessage, TaskStatus
        
        result = ResultMessage(
            task_id="test-456",
            status=TaskStatus.SUCCESS,
            result_type="image",
            result_data={"file_path": "/path/to/image.png"}
        )
        
        assert result.task_id == "test-456"
        assert result.status == TaskStatus.SUCCESS
        assert result.result_data["file_path"] == "/path/to/image.png"
    
    @pytest.mark.integration
    def test_image_gen_metadata_defaults(self):
        """Test image generation metadata defaults"""
        from services.common.schemas import IMAGE_GEN_METADATA_DEFAULTS
        
        assert 'model' in IMAGE_GEN_METADATA_DEFAULTS
        assert 'style' in IMAGE_GEN_METADATA_DEFAULTS
        assert 'aspect_ratio' in IMAGE_GEN_METADATA_DEFAULTS
        assert 'num_variations' in IMAGE_GEN_METADATA_DEFAULTS


class TestKafkaConfig:
    """Tests for Kafka configuration"""
    
    @pytest.mark.integration
    def test_kafka_config_topics(self):
        """Test Kafka topics configuration"""
        from services.common.kafka_config import kafka_config
        
        assert kafka_config.topics is not None
        assert 'tasks_ocr' in kafka_config.topics
        assert 'tasks_transcribe' in kafka_config.topics
        assert 'tasks_image_gen' in kafka_config.topics
        assert 'tasks_tts' in kafka_config.topics
        assert 'results_ocr' in kafka_config.topics
        assert 'results_transcribe' in kafka_config.topics
        assert 'results_image_gen' in kafka_config.topics
        assert 'results_tts' in kafka_config.topics


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
