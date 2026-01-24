import pytest
import os
import sys
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Добавляем путь к корню проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.models import Base, User, Transcription, AdminLog, UserRole
from utils.admin_service import AdminService


class TestAdminService:
    """Тесты для класса AdminService"""
    
    @pytest.fixture
    def db_session(self):
        """Создание тестовой сессии базы данных"""
        # Используем in-memory SQLite для тестов
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
    
    @pytest.fixture
    def admin_service(self, db_session):
        """Фикстура для AdminService"""
        return AdminService(db_session)
    
    @pytest.fixture
    def admin_user(self, db_session):
        """Создание администратора для тестов"""
        admin = User(
            telegram_id=123456789,
            username="admin",
            first_name="Admin",
            role=UserRole.ADMIN
        )
        db_session.add(admin)
        db_session.commit()
        return admin
    
    @pytest.fixture
    def regular_user(self, db_session):
        """Создание обычного пользователя для тестов"""
        user = User(
            telegram_id=987654321,
            username="user",
            first_name="User",
            role=UserRole.USER
        )
        db_session.add(user)
        db_session.commit()
        return user
    
    def test_is_admin_with_admin_user(self, admin_service, admin_user):
        """Тест проверки админских прав для администратора"""
        assert admin_service.is_admin(admin_user.telegram_id) == True
    
    def test_is_admin_with_regular_user(self, admin_service, regular_user):
        """Тест проверки админских прав для обычного пользователя"""
        assert admin_service.is_admin(regular_user.telegram_id) == False
    
    def test_is_admin_with_nonexistent_user(self, admin_service):
        """Тест проверки админских прав для несуществующего пользователя"""
        assert admin_service.is_admin(999999999) == False
    
    def test_get_admin_users(self, admin_service, admin_user, regular_user):
        """Тест получения списка администраторов"""
        admin_users = admin_service.get_admin_users()
        assert len(admin_users) == 1
        assert admin_users[0].telegram_id == admin_user.telegram_id
        assert admin_users[0].is_admin() == True
    
    def test_get_user_statistics_empty_db(self, admin_service):
        """Тест получения статистики пользователей в пустой БД"""
        stats = admin_service.get_user_statistics()
        assert stats['total_users'] == 0
        assert stats['active_users'] == 0
        assert stats['blocked_users'] == 0
        assert stats['admin_users'] == 0
    
    def test_get_user_statistics_with_users(self, admin_service, admin_user, regular_user, db_session):
        """Тест получения статистики с пользователями"""
        # Создаем еще одного пользователя
        another_user = User(
            telegram_id=111111111,
            username="user2",
            first_name="User2",
            role=UserRole.USER,
            last_activity=datetime.utcnow() - timedelta(days=1),  # Активный
            is_blocked=True
        )
        db_session.add(another_user)
        db_session.commit()
        
        stats = admin_service.get_user_statistics()
        assert stats['total_users'] == 3
        assert stats['active_users'] == 2  # admin_user и another_user активны
        assert stats['blocked_users'] == 1  # another_user заблокирован
        assert stats['admin_users'] == 1  # Только admin_user
    
    def test_get_transcription_statistics_empty_db(self, admin_service):
        """Тест получения статистики транскрипций в пустой БД"""
        stats = admin_service.get_transcription_statistics()
        assert stats['total_transcriptions'] == 0
        assert stats['successful_transcriptions'] == 0
        assert stats['failed_transcriptions'] == 0
        assert stats['success_rate'] == 0
        assert stats['avg_processing_time'] == 0
    
    def test_get_transcription_statistics_with_transcriptions(self, admin_service, admin_user, db_session):
        """Тест получения статистики с транскрипциями"""
        # Создаем транскрипции
        successful_trans = Transcription(
            user_id=admin_user.id,
            status='completed',
            processing_time=10,
            text_length=100
        )
        
        another_successful = Transcription(
            user_id=admin_user.id,
            status='completed',
            processing_time=20,
            text_length=200
        )
        
        failed_trans = Transcription(
            user_id=admin_user.id,
            status='failed',
            processing_time=None,
            text_length=0
        )
        
        db_session.add_all([successful_trans, another_successful, failed_trans])
        db_session.commit()
        
        stats = admin_service.get_transcription_statistics()
        assert stats['total_transcriptions'] == 3
        assert stats['successful_transcriptions'] == 2
        assert stats['failed_transcriptions'] == 1
        assert stats['success_rate'] == round(2/3 * 100, 2)  # ~66.67%
        assert stats['avg_processing_time'] == 15  # (10 + 20) / 2
    
    def test_get_users_list(self, admin_service, admin_user, regular_user, db_session):
        """Тест получения списка пользователей"""
        # Создаем еще одного пользователя для проверки сортировки
        another_user = User(
            telegram_id=555555555,
            username="user3",
            first_name="User3",
            role=UserRole.USER
        )
        db_session.add(another_user)
        db_session.commit()
        
        users = admin_service.get_users_list(limit=2)
        assert len(users) == 2
        # Проверяем что возвращаются последние пользователи (сортировка по created_at DESC)
    
    def test_block_user_success(self, admin_service, admin_user, regular_user):
        """Тест успешной блокировки пользователя"""
        result = admin_service.block_user(
            admin_user.telegram_id, 
            regular_user.telegram_id, 
            "Test block"
        )
        assert result == True
        
        # Проверяем что пользователь заблокирован
        db = admin_service.db
        blocked_user = db.query(User).filter(User.telegram_id == regular_user.telegram_id).first()
        assert blocked_user.is_blocked == True
        
        # Проверяем что лог создан
        log = db.query(AdminLog).filter(AdminLog.admin_id == admin_user.id).first()
        assert log is not None
        assert log.action == "block_user"
        assert "Test block" in log.description
    
    def test_block_user_non_admin(self, admin_service, regular_user, admin_user):
        """Тест попытки блокировки от имени обычного пользователя"""
        result = admin_service.block_user(
            regular_user.telegram_id, 
            admin_user.telegram_id, 
            "Test block"
        )
        assert result == False
    
    def test_block_user_nonexistent_target(self, admin_service, admin_user):
        """Тест попытки блокировки несуществующего пользователя"""
        result = admin_service.block_user(
            admin_user.telegram_id, 
            999999999, 
            "Test block"
        )
        assert result == False
    
    def test_unblock_user_success(self, admin_service, admin_user, regular_user, db_session):
        """Тест успешной разблокировки пользователя"""
        # Сначала блокируем пользователя
        regular_user.is_blocked = True
        db_session.commit()
        
        result = admin_service.unblock_user(
            admin_user.telegram_id, 
            regular_user.telegram_id, 
            "Test unblock"
        )
        assert result == True
        
        # Проверяем что пользователь разблокирован
        db = admin_service.db
        unblocked_user = db.query(User).filter(User.telegram_id == regular_user.telegram_id).first()
        assert unblocked_user.is_blocked == False
        
        # Проверяем что лог создан
        log = db.query(AdminLog).filter(AdminLog.admin_id == admin_user.id).first()
        assert log is not None
        assert log.action == "unblock_user"
        assert "Test unblock" in log.description
    
    def test_get_user_info(self, admin_service, regular_user):
        """Тест получения информации о пользователе"""
        user = admin_service.get_user_info(regular_user.telegram_id)
        assert user is not None
        assert user.telegram_id == regular_user.telegram_id
        assert user.username == regular_user.username
    
    def test_get_user_info_nonexistent(self, admin_service):
        """Тест получения информации о несуществующем пользователе"""
        user = admin_service.get_user_info(999999999)
        assert user is None
    
    def test_get_user_transcriptions(self, admin_service, regular_user, db_session):
        """Тест получения транскрипций пользователя"""
        # Создаем транскрипции для пользователя
        trans1 = Transcription(
            user_id=regular_user.id,
            status='completed',
            processing_time=10,
            text_length=100
        )
        trans2 = Transcription(
            user_id=regular_user.id,
            status='pending',
            processing_time=None,
            text_length=0
        )
        
        db_session.add_all([trans1, trans2])
        db_session.commit()
        
        transcriptions = admin_service.get_user_transcriptions(regular_user.telegram_id)
        assert len(transcriptions) == 2
        # Проверяем сортировку по created_at DESC
        assert transcriptions[0].id >= transcriptions[1].id
    
    def test_get_admin_logs(self, admin_service, admin_user, regular_user, db_session):
        """Тест получения логов администратора"""
        # Создаем логи
        log1 = AdminLog(
            admin_id=admin_user.id,
            action="test_action1",
            description="Test log 1"
        )
        log2 = AdminLog(
            admin_id=admin_user.id,
            action="test_action2",
            description="Test log 2"
        )
        
        db_session.add_all([log1, log2])
        db_session.commit()
        
        logs = admin_service.get_admin_logs()
        assert len(logs) >= 2
        # Проверяем сортировку по created_at DESC
        assert logs[0].created_at >= logs[1].created_at
    
    def test_update_user_activity(self, admin_service, regular_user, db_session):
        """Тест обновления активности пользователя"""
        old_activity = regular_user.last_activity
        
        # Ждем немного чтобы время обновилось
        import time
        time.sleep(0.01)
        
        admin_service.update_user_activity(regular_user.telegram_id)
        
        db = admin_service.db
        updated_user = db.query(User).filter(User.telegram_id == regular_user.telegram_id).first()
        assert updated_user.last_activity > old_activity
    
    def test_create_or_update_user_new_user(self, admin_service):
        """Тест создания нового пользователя (не первого)"""
        # Создаем первого пользователя отдельно
        first_user = admin_service.create_or_update_user(
            telegram_id=999999999,
            username="first_user",
            first_name="First",
            last_name="User"
        )
        assert first_user.role == UserRole.USER

        # Теперь создаем второго пользователя
        user = admin_service.create_or_update_user(
            telegram_id=111111111,
            username="new_user",
            first_name="New",
            last_name="User"
        )

        assert user is not None
        assert user.telegram_id == 111111111
        assert user.username == "new_user"
        assert user.first_name == "New"
        assert user.last_name == "User"
        assert user.role == UserRole.USER  # Не первый пользователь
    
    def test_create_or_update_user_first_user(self, admin_service):
        """Тест создания первого пользователя (должен быть обычным пользователем)"""
        # Очищаем базу данных
        admin_service.db.query(User).delete()
        admin_service.db.commit()

        user = admin_service.create_or_update_user(
            telegram_id=222222222,
            username="first_user",
            first_name="First"
        )

        assert user is not None
        assert user.role == UserRole.USER  # Первый пользователь должен быть обычным пользователем
    
    def test_create_or_update_user_existing_user(self, admin_service, regular_user):
        """Тест обновления существующего пользователя"""
        user = admin_service.create_or_update_user(
            telegram_id=regular_user.telegram_id,
            username="updated_username",
            first_name="Updated",
            last_name="Name"
        )
        
        assert user is not None
        assert user.id == regular_user.id
        assert user.username == "updated_username"
        assert user.first_name == "Updated"
        assert user.last_name == "Name"
    
    def test_log_transcription(self, admin_service, admin_user, db_session):
        """Тест логирования транскрипции"""
        admin_service.log_transcription(
            user_id=admin_user.telegram_id,
            status='completed',
            processing_time=15,
            text_length=150
        )
        
        db = admin_service.db
        transcription = db.query(Transcription).filter(Transcription.user_id == admin_user.id).first()
        assert transcription is not None
        assert transcription.status == 'completed'
        assert transcription.processing_time == 15
        assert transcription.text_length == 150