import pytest
import os
import sys
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Добавляем путь к корню проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.models import Base, User, Transcription, AdminLog, BotStatistics, UserRole, TranscriptionType


class TestDatabaseModels:
    """Тесты для моделей базы данных"""
    
    @pytest.fixture
    def db_session(self):
        """Создание тестовой сессии базы данных"""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()
        yield session
        session.close()
    
    def test_user_model_creation(self, db_session):
        """Тест создания модели User"""
        user = User(
            telegram_id=123456789,
            username="testuser",
            first_name="Test",
            last_name="User"
        )
        
        db_session.add(user)
        db_session.commit()
        
        retrieved_user = db_session.query(User).filter(User.telegram_id == 123456789).first()
        
        assert retrieved_user is not None
        assert retrieved_user.telegram_id == 123456789
        assert retrieved_user.username == "testuser"
        assert retrieved_user.first_name == "Test"
        assert retrieved_user.last_name == "User"
        assert retrieved_user.role == UserRole.USER
        assert retrieved_user.is_active == True
        assert retrieved_user.is_blocked == False
        assert retrieved_user.created_at is not None
        assert retrieved_user.last_activity is not None
    
    def test_user_model_admin_role(self, db_session):
        """Тест создания пользователя с админской ролью"""
        admin_user = User(
            telegram_id=987654321,
            username="admin",
            first_name="Admin",
            role=UserRole.ADMIN
        )
        
        db_session.add(admin_user)
        db_session.commit()
        
        retrieved_user = db_session.query(User).filter(User.telegram_id == 987654321).first()
        
        assert retrieved_user is not None
        assert retrieved_user.role == UserRole.ADMIN
        assert retrieved_user.is_admin() == True
    
    def test_user_model_get_full_name(self, db_session):
        """Тест метода get_full_name"""
        # Тест с полным именем
        user1 = User(
            telegram_id=111111111,
            first_name="First",
            last_name="Last"
        )
        db_session.add(user1)
        
        # Тест только с именем
        user2 = User(
            telegram_id=222222222,
            first_name="OnlyFirst"
        )
        db_session.add(user2)
        
        # Только с юзернеймом
        user3 = User(
            telegram_id=333333333,
            username="username"
        )
        db_session.add(user3)
        
        # Пустой пользователь
        user4 = User(
            telegram_id=444444444
        )
        db_session.add(user4)
        
        db_session.commit()
        
        assert user1.get_full_name() == "First Last"
        assert user2.get_full_name() == "OnlyFirst"
        assert user3.get_full_name() == "@username"
        assert user4.get_full_name() == "User #444444444"
    
    def test_user_model_repr(self, db_session):
        """Тест __repr__ метода"""
        user = User(
            telegram_id=123456789,
            username="testuser"
        )
        
        assert repr(user) == "<User(telegram_id=123456789, username=testuser)>"
    
    def test_transcription_model_creation(self, db_session):
        """Тест создания модели Transcription"""
        user = User(telegram_id=123456789)
        db_session.add(user)
        db_session.flush()  # Получаем ID пользователя
        
        transcription = Transcription(
            user_id=user.id,
            transcription_type=TranscriptionType.TEXT_TO_AUDIO,
            input_text="Test text",
            input_audio_path="/path/to/input/audio.wav",
            output_audio_path="/path/to/output/audio.wav",
            text_length=9,
            processing_time=15,
            status="completed"
        )
        
        db_session.add(transcription)
        db_session.commit()
        
        retrieved_trans = db_session.query(Transcription).filter(Transcription.user_id == user.id).first()
        
        assert retrieved_trans is not None
        assert retrieved_trans.user_id == user.id
        assert retrieved_trans.transcription_type == TranscriptionType.TEXT_TO_AUDIO
        assert retrieved_trans.input_text == "Test text"
        assert retrieved_trans.input_audio_path == "/path/to/input/audio.wav"
        assert retrieved_trans.output_audio_path == "/path/to/output/audio.wav"
        assert retrieved_trans.text_length == 9
        assert retrieved_trans.processing_time == 15
        assert retrieved_trans.status == "completed"
        assert retrieved_trans.created_at is not None
    
    def test_transcription_model_relationship(self, db_session):
        """Тест связи Transcription -> User"""
        user = User(
            telegram_id=123456789,
            username="testuser"
        )
        db_session.add(user)
        db_session.flush()
        
        transcription = Transcription(
            user_id=user.id,
            status="completed"
        )
        db_session.add(transcription)
        db_session.commit()
        
        retrieved_trans = db_session.query(Transcription).first()
        retrieved_user = retrieved_trans.user
        
        assert retrieved_user is not None
        assert retrieved_user.telegram_id == 123456789
        assert retrieved_user.username == "testuser"
    
    def test_transcription_model_repr(self, db_session):
        """Тест __repr__ метода"""
        user = User(telegram_id=123456789)
        db_session.add(user)
        db_session.flush()
        
        transcription = Transcription(
            user_id=user.id,
            transcription_type=TranscriptionType.TEXT_TO_AUDIO,
            status="completed"
        )
        db_session.add(transcription)
        
        assert "Transcription" in repr(transcription)
        assert "completed" in repr(transcription)
        assert "text_to_audio" in repr(transcription)
    
    def test_admin_log_model_creation(self, db_session):
        """Тест создания модели AdminLog"""
        admin_user = User(
            telegram_id=123456789,
            username="admin",
            role=UserRole.ADMIN
        )
        target_user = User(
            telegram_id=987654321,
            username="target"
        )
        db_session.add_all([admin_user, target_user])
        db_session.flush()
        
        admin_log = AdminLog(
            admin_id=admin_user.id,
            action="block_user",
            target_user_id=target_user.id,
            description="Blocked user for violation",
            ip_address="192.168.1.1"
        )
        
        db_session.add(admin_log)
        db_session.commit()
        
        retrieved_log = db_session.query(AdminLog).filter(AdminLog.admin_id == admin_user.id).first()
        
        assert retrieved_log is not None
        assert retrieved_log.admin_id == admin_user.id
        assert retrieved_log.action == "block_user"
        assert retrieved_log.target_user_id == target_user.id
        assert retrieved_log.description == "Blocked user for violation"
        assert retrieved_log.ip_address == "192.168.1.1"
        assert retrieved_log.created_at is not None
    
    def test_admin_log_model_relationship(self, db_session):
        """Тест связи AdminLog -> User"""
        admin_user = User(
            telegram_id=123456789,
            username="admin",
            role=UserRole.ADMIN
        )
        db_session.add(admin_user)
        db_session.flush()
        
        admin_log = AdminLog(
            admin_id=admin_user.id,
            action="test_action"
        )
        db_session.add(admin_log)
        db_session.commit()
        
        retrieved_log = db_session.query(AdminLog).first()
        retrieved_admin = retrieved_log.admin
        
        assert retrieved_admin is not None
        assert retrieved_admin.telegram_id == 123456789
        assert retrieved_admin.username == "admin"
    
    def test_admin_log_model_repr(self, db_session):
        """Тест __repr__ метода"""
        admin_user = User(telegram_id=123456789, role=UserRole.ADMIN)
        db_session.add(admin_user)
        db_session.flush()
        
        admin_log = AdminLog(
            admin_id=admin_user.id,
            action="test_action"
        )
        db_session.add(admin_log)
        
        assert "AdminLog" in repr(admin_log)
        assert "test_action" in repr(admin_log)
    
    def test_bot_statistics_model_creation(self, db_session):
        """Тест создания модели BotStatistics"""
        stats_date = datetime.utcnow()
        
        bot_stats = BotStatistics(
            date=stats_date,
            total_users=100,
            active_users=25,
            total_transcriptions=500,
            successful_transcriptions=450,
            failed_transcriptions=50,
            total_processing_time=7500,
            avg_processing_time=15
        )
        
        db_session.add(bot_stats)
        db_session.commit()
        
        retrieved_stats = db_session.query(BotStatistics).filter(BotStatistics.date == stats_date).first()
        
        assert retrieved_stats is not None
        assert retrieved_stats.date == stats_date
        assert retrieved_stats.total_users == 100
        assert retrieved_stats.active_users == 25
        assert retrieved_stats.total_transcriptions == 500
        assert retrieved_stats.successful_transcriptions == 450
        assert retrieved_stats.failed_transcriptions == 50
        assert retrieved_stats.total_processing_time == 7500
        assert retrieved_stats.avg_processing_time == 15
        assert retrieved_stats.created_at is not None
    
    def test_bot_statistics_model_repr(self, db_session):
        """Тест __repr__ метода"""
        stats_date = datetime.utcnow()
        
        bot_stats = BotStatistics(
            date=stats_date,
            total_users=100
        )
        db_session.add(bot_stats)
        
        assert "BotStatistics" in repr(bot_stats)
        assert "100" in repr(bot_stats)
    
    def test_user_role_enum(self):
        """Тест UserRole enum"""
        assert UserRole.USER.value == "user"
        assert UserRole.ADMIN.value == "admin"
        
        # Тест создания пользователя с ролью
        user = User(telegram_id=123456789, role=UserRole.ADMIN)
        assert user.role == UserRole.ADMIN
        assert user.is_admin() == True
    
    def test_user_transcriptions_relationship(self, db_session):
        """Тест связи User -> Transcriptions"""
        user = User(telegram_id=123456789)
        db_session.add(user)
        db_session.flush()
        
        # Создаем несколько транскрипций
        trans1 = Transcription(user_id=user.id, status="completed")
        trans2 = Transcription(user_id=user.id, status="failed")
        trans3 = Transcription(user_id=user.id, status="pending")
        
        db_session.add_all([trans1, trans2, trans3])
        db_session.commit()
        
        retrieved_user = db_session.query(User).filter(User.telegram_id == 123456789).first()
        
        assert len(retrieved_user.transcriptions) == 3
        assert all(t.user_id == retrieved_user.id for t in retrieved_user.transcriptions)
    
    def test_user_admin_logs_relationship(self, db_session):
        """Тест связи User -> AdminLogs"""
        admin_user = User(telegram_id=123456789, role=UserRole.ADMIN)
        db_session.add(admin_user)
        db_session.flush()
        
        # Создаем несколько логов
        log1 = AdminLog(admin_id=admin_user.id, action="block_user")
        log2 = AdminLog(admin_id=admin_user.id, action="unblock_user")
        log3 = AdminLog(admin_id=admin_user.id, action="test_action")
        
        db_session.add_all([log1, log2, log3])
        db_session.commit()
        
        retrieved_user = db_session.query(User).filter(User.telegram_id == 123456789).first()
        
        assert len(retrieved_user.admin_logs) == 3
        assert all(log.admin_id == retrieved_user.id for log in retrieved_user.admin_logs)
    
    def test_model_constraints(self, db_session):
        """Тест ограничений моделей"""
        # Тест уникальности telegram_id
        user1 = User(telegram_id=123456789)
        user2 = User(telegram_id=123456789)  # Такой же ID
        
        db_session.add(user1)
        db_session.commit()
        
        db_session.add(user2)
        
        # Должна быть ошибка при commit
        with pytest.raises(Exception):  # IntegrityError expected
            db_session.commit()
    
    def test_model_defaults(self, db_session):
        """Тест значений по умолчанию"""
        user = User(telegram_id=123456789)
        
        db_session.add(user)
        db_session.commit()
        
        assert user.role == UserRole.USER
        assert user.is_active == True
        assert user.is_blocked == False
        
        transcription = Transcription(user_id=user.id)
        
        db_session.add(transcription)
        db_session.commit()
        
        assert transcription.status == 'pending'
        assert transcription.text_length == 0
        assert transcription.transcription_type == TranscriptionType.TEXT_TO_AUDIO
        assert transcription.input_text is None
        assert transcription.input_audio_path is None
        assert transcription.output_audio_path is None
        assert transcription.processing_time is None
        assert transcription.error_message is None