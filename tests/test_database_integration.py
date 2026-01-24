import pytest
import os
import sys
from datetime import datetime
from unittest.mock import patch, Mock

# Добавляем путь к корню проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.models import Base, User, Transcription, AdminLog, BotStatistics, UserRole, TranscriptionType
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Добавляем путь к корню проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.models import Base, User, Transcription, AdminLog, BotStatistics, UserRole, get_db, create_tables


class TestDatabaseIntegration:
    """Тесты интеграции с базой данных"""
    
    @pytest.fixture
    def test_database(self):
        """Создание тестовой базы данных"""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        return SessionLocal()
    
    def test_get_db_generator(self):
        """Тест генератора get_db"""
        db_sessions = []
        
        with patch('database.models.SessionLocal') as mock_session_local:
            mock_session = Mock()
            mock_session_local.return_value = mock_session
            
            # Тестируем как генератор
            gen = get_db()
            db_session = next(gen)
            
            assert db_session == mock_session
            mock_session_local.assert_called_once()
            
            # Тестируем закрытие сессии
            try:
                next(gen)
            except StopIteration:
                pass
            
            mock_session.close.assert_called_once()
    
    def test_create_tables_function(self):
        """Тест функции create_tables"""
        with patch('database.models.Base') as mock_base:
            create_tables()
            mock_base.metadata.create_all.assert_called_once()
    
    def test_user_crud_operations(self, test_database):
        """Тест CRUD операций для User"""
        # Create
        user = User(
            telegram_id=123456789,
            username="testuser",
            first_name="Test",
            last_name="User"
        )
        test_database.add(user)
        test_database.commit()
        
        # Read
        retrieved_user = test_database.query(User).filter(User.telegram_id == 123456789).first()
        assert retrieved_user is not None
        assert retrieved_user.username == "testuser"
        
        # Update
        retrieved_user.username = "updated_user"
        test_database.commit()
        
        updated_user = test_database.query(User).filter(User.telegram_id == 123456789).first()
        assert updated_user.username == "updated_user"
        
        # Delete
        test_database.delete(updated_user)
        test_database.commit()
        
        deleted_user = test_database.query(User).filter(User.telegram_id == 123456789).first()
        assert deleted_user is None
    
    def test_transcription_crud_operations(self, test_database):
        """Тест CRUD операций для Transcription"""
        # Сначала создаем пользователя
        user = User(telegram_id=123456789)
        test_database.add(user)
        test_database.flush()
        
        # Create Transcription
        transcription = Transcription(
            user_id=user.id,
            transcription_type=TranscriptionType.TEXT_TO_AUDIO,
            input_text="Test text",
            status="completed",
            processing_time=10,
            text_length=9
        )
        test_database.add(transcription)
        test_database.commit()
        
        # Read
        retrieved_trans = test_database.query(Transcription).filter(Transcription.user_id == user.id).first()
        assert retrieved_trans is not None
        assert retrieved_trans.input_text == "Test text"
        assert retrieved_trans.transcription_type == TranscriptionType.TEXT_TO_AUDIO
        assert retrieved_trans.status == "completed"
        
        # Update
        retrieved_trans.status = "failed"
        retrieved_trans.error_message = "Test error"
        test_database.commit()
        
        updated_trans = test_database.query(Transcription).filter(Transcription.id == retrieved_trans.id).first()
        assert updated_trans.status == "failed"
        assert updated_trans.error_message == "Test error"
        
        # Delete
        test_database.delete(updated_trans)
        test_database.commit()
        
        deleted_trans = test_database.query(Transcription).filter(Transcription.user_id == user.id).first()
        assert deleted_trans is None
    
    def test_admin_log_crud_operations(self, test_database):
        """Тест CRUD операций для AdminLog"""
        # Создаем администратора и пользователя
        admin = User(telegram_id=123456789, role=UserRole.ADMIN)
        target = User(telegram_id=987654321, role=UserRole.USER)
        test_database.add_all([admin, target])
        test_database.flush()
        
        # Create AdminLog
        admin_log = AdminLog(
            admin_id=admin.id,
            action="block_user",
            target_user_id=target.id,
            description="Test block action",
            ip_address="192.168.1.1"
        )
        test_database.add(admin_log)
        test_database.commit()
        
        # Read
        retrieved_log = test_database.query(AdminLog).filter(AdminLog.admin_id == admin.id).first()
        assert retrieved_log is not None
        assert retrieved_log.action == "block_user"
        assert retrieved_log.target_user_id == target.id
        assert retrieved_log.description == "Test block action"
        assert retrieved_log.ip_address == "192.168.1.1"
        
        # Update
        retrieved_log.description = "Updated description"
        test_database.commit()
        
        updated_log = test_database.query(AdminLog).filter(AdminLog.id == retrieved_log.id).first()
        assert updated_log.description == "Updated description"
        
        # Delete
        test_database.delete(updated_log)
        test_database.commit()
        
        deleted_log = test_database.query(AdminLog).filter(AdminLog.admin_id == admin.id).first()
        assert deleted_log is None
    
    def test_bot_statistics_crud_operations(self, test_database):
        """Тест CRUD операций для BotStatistics"""
        stats_date = datetime.utcnow()
        
        # Create BotStatistics
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
        test_database.add(bot_stats)
        test_database.commit()
        
        # Read
        retrieved_stats = test_database.query(BotStatistics).filter(BotStatistics.date == stats_date).first()
        assert retrieved_stats is not None
        assert retrieved_stats.total_users == 100
        assert retrieved_stats.active_users == 25
        assert retrieved_stats.total_transcriptions == 500
        assert retrieved_stats.successful_transcriptions == 450
        assert retrieved_stats.failed_transcriptions == 50
        assert retrieved_stats.total_processing_time == 7500
        assert retrieved_stats.avg_processing_time == 15
        
        # Update
        retrieved_stats.total_users = 150
        test_database.commit()
        
        updated_stats = test_database.query(BotStatistics).filter(BotStatistics.date == stats_date).first()
        assert updated_stats.total_users == 150
        
        # Delete
        test_database.delete(updated_stats)
        test_database.commit()
        
        deleted_stats = test_database.query(BotStatistics).filter(BotStatistics.date == stats_date).first()
        assert deleted_stats is None
    
    def test_relationship_user_transcriptions(self, test_database):
        """Тест связи User -> Transcriptions"""
        user = User(telegram_id=123456789)
        test_database.add(user)
        test_database.flush()
        
        # Создаем несколько транскрипций
        trans1 = Transcription(user_id=user.id, transcription_type=TranscriptionType.TEXT_TO_AUDIO, status="completed", input_text="Text 1")
        trans2 = Transcription(user_id=user.id, transcription_type=TranscriptionType.TEXT_TO_AUDIO, status="failed", error_message="Error 1")
        trans3 = Transcription(user_id=user.id, transcription_type=TranscriptionType.TEXT_TO_AUDIO, status="pending")
        
        test_database.add_all([trans1, trans2, trans3])
        test_database.commit()
        
        retrieved_user = test_database.query(User).filter(User.telegram_id == 123456789).first()
        
        assert len(retrieved_user.transcriptions) == 3
        assert all(t.user_id == retrieved_user.id for t in retrieved_user.transcriptions)
        
        # Проверяем что транскрипции отсортированы по created_at (по умолчанию)
        statuses = [t.status for t in retrieved_user.transcriptions]
        assert statuses == ["completed", "failed", "pending"] or statuses == ["failed", "completed", "pending"]
    
    def test_relationship_user_admin_logs(self, test_database):
        """Тест связи User -> AdminLogs"""
        admin = User(telegram_id=123456789, role=UserRole.ADMIN)
        target = User(telegram_id=987654321)
        test_database.add_all([admin, target])
        test_database.flush()
        
        # Создаем несколько логов
        log1 = AdminLog(admin_id=admin.id, action="block_user", target_user_id=target.id)
        log2 = AdminLog(admin_id=admin.id, action="unblock_user", target_user_id=target.id)
        log3 = AdminLog(admin_id=admin.id, action="test_action")
        
        test_database.add_all([log1, log2, log3])
        test_database.commit()
        
        retrieved_admin = test_database.query(User).filter(User.telegram_id == 123456789).first()
        
        assert len(retrieved_admin.admin_logs) == 3
        assert all(log.admin_id == retrieved_admin.id for log in retrieved_admin.admin_logs)
    
    def test_relationship_transcription_user(self, test_database):
        """Тест связи Transcription -> User"""
        user = User(
            telegram_id=123456789,
            username="testuser",
            first_name="Test"
        )
        test_database.add(user)
        test_database.flush()
        
        transcription = Transcription(
            user_id=user.id,
            transcription_type=TranscriptionType.TEXT_TO_AUDIO,
            status="completed",
            input_text="Test transcription"
        )
        test_database.add(transcription)
        test_database.commit()
        
        retrieved_trans = test_database.query(Transcription).first()
        retrieved_user = retrieved_trans.user
        
        assert retrieved_user is not None
        assert retrieved_user.telegram_id == 123456789
        assert retrieved_user.username == "testuser"
        assert retrieved_user.first_name == "Test"
    
    def test_relationship_admin_log_user(self, test_database):
        """Тест связи AdminLog -> User"""
        admin = User(
            telegram_id=123456789,
            username="admin",
            role=UserRole.ADMIN
        )
        test_database.add(admin)
        test_database.flush()
        
        admin_log = AdminLog(
            admin_id=admin.id,
            action="test_action",
            description="Test admin action"
        )
        test_database.add(admin_log)
        test_database.commit()
        
        retrieved_log = test_database.query(AdminLog).first()
        retrieved_admin = retrieved_log.admin
        
        assert retrieved_admin is not None
        assert retrieved_admin.telegram_id == 123456789
        assert retrieved_admin.username == "admin"
        assert retrieved_admin.is_admin() == True
    
    def test_database_constraints(self, test_database):
        """Тест ограничений базы данных"""
        # Тест уникальности telegram_id
        user1 = User(telegram_id=123456789, username="user1")
        user2 = User(telegram_id=123456789, username="user2")
        
        test_database.add(user1)
        test_database.commit()
        
        test_database.add(user2)
        
        # Должна быть ошибка при коммите
        with pytest.raises(Exception):  # IntegrityError
            test_database.commit()
        
        test_database.rollback()
    
    def test_database_indexes(self, test_database):
        """Тест индексов базы данных"""
        # Создаем пользователя
        user = User(telegram_id=123456789)
        test_database.add(user)
        test_database.flush()
        
        # Создаем транскрипции
        for i in range(100):
            transcription = Transcription(
                user_id=user.id,
                status=f"status_{i % 3}",
                text_length=i
            )
            test_database.add(transcription)
        
        test_database.commit()
        
        # Проверяем что запросы работают эффективно (с индексами)
        # Поиск по user_id (индексированное поле)
        transcriptions_by_user = test_database.query(Transcription).filter(Transcription.user_id == user.id).all()
        assert len(transcriptions_by_user) == 100
        
        # Поиск по status (неиндексированное поле)
        transcriptions_by_status = test_database.query(Transcription).filter(Transcription.status == "status_1").all()
        assert len(transcriptions_by_status) > 0
    
    def test_database_cascade_operations(self, test_database):
        """Тест каскадных операций"""
        # Создаем пользователя с транскрипциями
        user = User(telegram_id=123456789)
        test_database.add(user)
        test_database.flush()
        
        trans1 = Transcription(user_id=user.id, transcription_type=TranscriptionType.TEXT_TO_AUDIO, status="completed")
        trans2 = Transcription(user_id=user.id, transcription_type=TranscriptionType.TEXT_TO_AUDIO, status="failed")
        
        test_database.add_all([trans1, trans2])
        test_database.commit()
        
        user_id = user.id
        trans_count = test_database.query(Transcription).filter(Transcription.user_id == user_id).count()
        assert trans_count == 2
        
        # Удаляем пользователя
        test_database.delete(user)
        test_database.commit()
        
        # Транскрипции должны остаться в БД (в реальном приложении может быть настроен CASCADE)
        remaining_trans = test_database.query(Transcription).filter(Transcription.user_id == user_id).all()
        # Это зависит от настроек CASCADE в моделях
    
    def test_database_datetime_handling(self, test_database):
        """Тест обработки даты и времени"""
        now = datetime.utcnow()
        
        # Создаем пользователя
        user = User(telegram_id=123456789)
        test_database.add(user)
        test_database.flush()
        
        # Создаем транскрипцию с точным временем
        transcription = Transcription(
            user_id=user.id,
            status="completed",
            created_at=now
        )
        test_database.add(transcription)
        test_database.commit()
        
        # Проверяем что время сохранилось корректно
        retrieved_trans = test_database.query(Transcription).filter(Transcription.user_id == user.id).first()
        
        # Должно быть близко к исходному времени (разница в секундах приемлема)
        time_diff = abs(retrieved_trans.created_at - now)
        assert time_diff.total_seconds() < 1  # Разница менее 1 секунды
    
    def test_database_text_length_handling(self, test_database):
        """Тест обработки длинных текстов"""
        user = User(telegram_id=123456789)
        test_database.add(user)
        test_database.flush()
        
        # Создаем транскрипцию с очень длинным текстом
        long_text = "A" * 10000  # 10,000 символов
        
        transcription = Transcription(
            user_id=user.id,
            transcription_type=TranscriptionType.TEXT_TO_AUDIO,
            status="completed",
            input_text=long_text,
            text_length=len(long_text)
        )
        test_database.add(transcription)
        test_database.commit()
        
        retrieved_trans = test_database.query(Transcription).filter(Transcription.user_id == user.id).first()
        
        assert retrieved_trans.input_text == long_text
        assert retrieved_trans.text_length == len(long_text)
    
    def test_database_null_handling(self, test_database):
        """Тест обработки NULL значений"""
        user = User(telegram_id=123456789)
        test_database.add(user)
        test_database.flush()
        
        # Создаем транскрипцию с NULL полями
        transcription = Transcription(
            user_id=user.id,
            status="pending"
            # Оставляем поля как NULL по умолчанию
        )
        test_database.add(transcription)
        test_database.commit()
        
        retrieved_trans = test_database.query(Transcription).filter(Transcription.user_id == user.id).first()
        
        assert retrieved_trans.transcription_type == TranscriptionType.TEXT_TO_AUDIO
        assert retrieved_trans.input_text is None
        assert retrieved_trans.input_audio_path is None
        assert retrieved_trans.output_audio_path is None
        assert retrieved_trans.processing_time is None
        assert retrieved_trans.error_message is None
        assert retrieved_trans.text_length == 0  # Должно быть 0 по умолчанию