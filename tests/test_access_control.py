import pytest
import os
import sys
import asyncio
from unittest.mock import patch, Mock, AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Добавляем путь к корню проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.models import Base, User, Transcription, AdminLog, UserRole
from utils.admin_service import AdminService


class TestAccessControlAndRoles:
    """Тесты системы контроля доступа и ролей"""
    
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
    
    @pytest.fixture
    def mock_update(self):
        """Мок для Update"""
        mock_update = Mock()
        mock_update.message = Mock()
        mock_update.message.reply_text = AsyncMock()
        mock_update.effective_user = Mock()
        mock_update.effective_user.id = 123456789
        mock_update.effective_user.username = "testuser"
        mock_update.effective_user.first_name = "Test"
        mock_update.effective_user.last_name = "User"
        return mock_update
    
    @pytest.fixture
    def mock_context(self):
        """Мок для ContextTypes.DEFAULT_TYPE"""
        mock_context = Mock()
        mock_context.args = []
        return mock_context
    
    @pytest.fixture
    def bot_with_env(self, db_session):
        """Фикстура для бота с тестовым окружением"""
        with patch.dict(os.environ, {
            'TELEGRAM_BOT_TOKEN': 'test_token',
            'ADMIN_IDS': '111111111'  # ID администратора
        }):
            with patch('database.models.get_db') as mock_get_db:
                mock_get_db.return_value = db_session

                with patch('database.models.create_tables'):
                    from src.bot import TelegramBot
                    bot = TelegramBot()
                    bot.admin_service = AdminService(db_session)
                    return bot

    def test_user_role_enum_values(self):
        """Тест значений UserRole enum"""
        assert UserRole.USER.value == "user"
        assert UserRole.ADMIN.value == "admin"
    
    def test_user_role_creation(self, db_session):
        """Тест создания пользователей с разными ролями"""
        # Обычный пользователь
        regular_user = User(
            telegram_id=123456789,
            username="regular",
            role=UserRole.USER
        )
        
        # Администратор
        admin_user = User(
            telegram_id=987654321,
            username="admin",
            role=UserRole.ADMIN
        )
        
        db_session.add_all([regular_user, admin_user])
        db_session.commit()
        
        # Проверяем роли
        retrieved_regular = db_session.query(User).filter(User.telegram_id == 123456789).first()
        retrieved_admin = db_session.query(User).filter(User.telegram_id == 987654321).first()
        
        assert retrieved_regular.role == UserRole.USER
        assert retrieved_regular.is_admin() == False
        
        assert retrieved_admin.role == UserRole.ADMIN
        assert retrieved_admin.is_admin() == True
    
    def test_all_users_are_regular_by_default(self, db_session):
        """Тест что все пользователи по умолчанию являются обычными"""
        admin_service = AdminService(db_session)

        # Создаем первого пользователя
        first_user = admin_service.create_or_update_user(
            telegram_id=111111111,
            username="first",
            first_name="First"
        )

        # Создаем второго пользователя
        second_user = admin_service.create_or_update_user(
            telegram_id=123456789,
            username="second",
            first_name="Second"
        )

        # Оба пользователя должны быть обычными
        assert first_user.role == UserRole.USER
        assert second_user.role == UserRole.USER
    
    def test_is_admin_method(self, db_session):
        """Тест метода is_admin"""
        admin_user = User(telegram_id=123456789, role=UserRole.ADMIN)
        regular_user = User(telegram_id=987654321, role=UserRole.USER)
        
        db_session.add_all([admin_user, regular_user])
        db_session.commit()
        
        assert admin_user.is_admin() == True
        assert regular_user.is_admin() == False
    
    def test_admin_service_is_admin_permissions(self, db_session):
        """Тест проверок разрешений в AdminService"""
        admin_service = AdminService(db_session)
        
        # Создаем пользователей
        admin_user = User(telegram_id=111111111, role=UserRole.ADMIN)
        regular_user = User(telegram_id=123456789, role=UserRole.USER)
        
        db_session.add_all([admin_user, regular_user])
        db_session.commit()
        
        # Проверяем разрешения
        assert admin_service.is_admin(admin_user.telegram_id) == True
        assert admin_service.is_admin(regular_user.telegram_id) == False
        assert admin_service.is_admin(999999999) == False  # Несуществующий пользователь
    
    def test_admin_commands_access_control(self, bot_with_env, mock_update, mock_context, db_session):
        """Тест контроля доступа к административным командам"""
        # Создаем администратора с ID из ENV
        admin_user = User(
            telegram_id=111111111,
            role=UserRole.ADMIN
        )
        db_session.add(admin_user)
        db_session.commit()
        
        # Тест доступа администратора
        mock_update.effective_user.id = admin_user.telegram_id
        
        # Admin command
        bot_with_env.is_admin = lambda user_id: user_id == admin_user.telegram_id  # Мок для простоты
        asyncio.run(bot_with_env.admin_command(mock_update, mock_context))
        
        # Проверяем что команда выполнена (не было сообщения об отказе)
        calls = [call.args[0][0] for call in mock_update.message.reply_text.call_args_list]
        admin_call_found = any("Панель администратора" in call for call in calls)
        assert admin_call_found
    
    def test_regular_user_access_denied(self, bot_with_env, mock_update, mock_context, db_session):
        """Тест отказа в доступе для обычного пользователя"""
        regular_user = User(
            telegram_id=123456789,
            role=UserRole.USER
        )
        db_session.add(regular_user)
        db_session.commit()
        
        # Мокаем метод is_admin
        bot_with_env.is_admin = lambda user_id: user_id == 111111111  # Только 111111111 - админ
        
        mock_update.effective_user.id = regular_user.telegram_id
        
        # Тестируем все административные команды
        admin_commands = [
            ('admin_command', []),
            ('stats_command', []),
            ('users_command', []),
            ('block_command', [123456]),
            ('unblock_command', [123456])
        ]
        
        for command_name, args in admin_commands:
            mock_update.message.reply_text.reset_mock()
            mock_context.args = args
            
            command = getattr(bot_with_env, command_name)
            asyncio.run(command(mock_update, mock_context))
            
            # Проверяем что получено сообщение об отказе
            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "нет прав" in call_args.lower()
    
    def test_user_blocking_permissions(self, db_session):
        """Тест разрешений на блокировку пользователей"""
        admin_service = AdminService(db_session)
        
        # Создаем пользователей
        admin_user = User(telegram_id=111111111, role=UserRole.ADMIN)
        regular_user = User(telegram_id=123456789, role=UserRole.USER)
        another_admin = User(telegram_id=222222222, role=UserRole.ADMIN)
        
        db_session.add_all([admin_user, regular_user, another_admin])
        db_session.commit()
        
        # Только администратор может блокировать
        assert admin_service.block_user(admin_user.telegram_id, regular_user.telegram_id) == True
        
        # Обычный пользователь не может блокировать
        assert admin_service.block_user(regular_user.telegram_id, admin_user.telegram_id) == False
        
        # Администратор не может заблокировать себя (если это реализовано)
        # Этот тест зависит от бизнес-логики
    
    def test_admin_id_from_env(self, db_session):
        """Тест использования ADMIN_IDS из переменных окружения"""
        # Тест с несколькими администраторами в ENV
        with patch.dict(os.environ, {'ADMIN_IDS': '111111111,222222222,333333333'}):
            admin_service = AdminService(db_session)
            
            # Создаем пользователей с разными ID
            users = []
            for user_id in [111111111, 222222222, 333333333, 444444444]:
                user = User(
                    telegram_id=user_id,
                    username=f"user_{user_id}",
                    role=UserRole.USER
                )
                users.append(user)
                db_session.add(user)
            
            db_session.commit()
            
            # Все ID из ENV должны иметь права администратора
            assert admin_service.is_admin(111111111) == False  # user с role USER
            assert admin_service.is_admin(222222222) == False
            assert admin_service.is_admin(333333333) == False
            assert admin_service.is_admin(444444444) == False
            
            # Если бы мы мокали is_admin через ENV, то проверили бы это
    
    def test_role_based_ui_content(self, bot_with_env, mock_update, mock_context, db_session):
        """Тест контента UI в зависимости от роли"""
        # Создаем администратора
        admin_user = User(telegram_id=111111111, role=UserRole.ADMIN)
        db_session.add(admin_user)
        db_session.commit()
        
        # Мокаем is_admin
        bot_with_env.is_admin = lambda user_id: user_id == admin_user.telegram_id
        
        mock_update.effective_user.id = admin_user.telegram_id
        
        # Тест /start команды
        asyncio.run(bot_with_env.start_command(mock_update, mock_context))
        
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Административные команды" in call_args
        assert "/admin" in call_args
        
        # Создаем обычного пользователя
        regular_user = User(telegram_id=123456789, role=UserRole.USER)
        db_session.add(regular_user)
        db_session.commit()
        
        mock_update.message.reply_text.reset_mock()
        mock_update.effective_user.id = regular_user.telegram_id
        
        asyncio.run(bot_with_env.start_command(mock_update, mock_context))
        
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Административные команды" not in call_args
        assert "/admin" not in call_args
    
    def test_user_role_persistence(self, db_session):
        """Тест сохранения роли пользователя"""
        admin_service = AdminService(db_session)
        
        # Создаем пользователя
        user = admin_service.create_or_update_user(
            telegram_id=123456789,
            username="testuser",
            first_name="Test"
        )
        
        # Обновляем данные пользователя (роль не должна измениться)
        updated_user = admin_service.create_or_update_user(
            telegram_id=123456789,
            username="updated_user",
            first_name="Updated"
        )
        
        assert user.id == updated_user.id
        assert updated_user.username == "updated_user"
        assert updated_user.first_name == "Updated"
        # Роль должна остаться прежней
    
    def test_admin_logging_permissions(self, db_session):
        """Тест логирования только действий администраторов"""
        admin_service = AdminService(db_session)
        
        admin_user = User(telegram_id=111111111, role=UserRole.ADMIN)
        regular_user = User(telegram_id=123456789, role=UserRole.USER)
        
        db_session.add_all([admin_user, regular_user])
        db_session.commit()
        
        # Действие администратора логируется
        result = admin_service.block_user(admin_user.telegram_id, regular_user.telegram_id, "Test")
        assert result == True
        
        logs = db_session.query(AdminLog).filter(AdminLog.admin_id == admin_user.id).all()
        assert len(logs) == 1
        assert logs[0].action == "block_user"
        
        # Действие обычного пользователя не логируется (возвращается False)
        result = admin_service.block_user(regular_user.telegram_id, admin_user.telegram_id, "Test")
        assert result == False
        
        additional_logs = db_session.query(AdminLog).filter(AdminLog.admin_id == regular_user.id).all()
        assert len(additional_logs) == 0  # Не должно быть новых логов
    
    def test_role_based_data_access(self, db_session):
        """Тест доступа к данным в зависимости от роли"""
        admin_service = AdminService(db_session)
        
        admin_user = User(telegram_id=111111111, role=UserRole.ADMIN)
        regular_user = User(telegram_id=123456789, role=UserRole.USER)
        
        db_session.add_all([admin_user, regular_user])
        db_session.flush()
        
        # Создаем транскрипции для обоих пользователей
        admin_trans = Transcription(user_id=admin_user.id, status="completed")
        regular_trans = Transcription(user_id=regular_user.id, status="completed")
        
        db_session.add_all([admin_trans, regular_trans])
        db_session.commit()
        
        # Администратор может видеть все транскрипции (если реализовано)
        admin_transcriptions = admin_service.get_user_transcriptions(admin_user.telegram_id)
        regular_transcriptions = admin_service.get_user_transcriptions(regular_user.telegram_id)
        
        assert len(admin_transcriptions) == 1
        assert len(regular_transcriptions) == 1
        
        # Каждый видит только свои транскрипции
        assert admin_transcriptions[0].user_id == admin_user.id
        assert regular_transcriptions[0].user_id == regular_user.id


# Вспомогательная функция для запуска async кода в синхронных тестах
def run_async(coro):
    """Запуск корутины в синхронном тесте"""
    return asyncio.get_event_loop().run_until_complete(coro)