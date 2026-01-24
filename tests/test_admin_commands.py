import pytest
import os
import sys
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Добавляем путь к корню проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.models import Base, User, Transcription, UserRole


class TestTelegramBotAdminCommands:
    """Тесты административных команд Telegram бота"""
    
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
        mock_update.message.text = ""
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
        mock_context.bot = Mock()
        return mock_context
    
    @pytest.fixture
    def bot_with_env(self, db_session):
        """Фикстура для бота с моками окружения"""
        with patch.dict(os.environ, {
            'TELEGRAM_BOT_TOKEN': 'test_token',
            'ADMIN_IDS': '123456789'  # ID администратора
        }):
            def mock_get_db():
                while True:
                    yield db_session

            with patch('database.models.get_db', mock_get_db):
                
                with patch('database.models.create_tables'):
                    from src.bot import TelegramBot
                    bot = TelegramBot()
                    # Устанавливаем AdminService напрямую
                    from utils.admin_service import AdminService
                    bot.admin_service = AdminService(db_session)
                    return bot
    
    @pytest.fixture
    def admin_user(self, db_session):
        """Создание администратора"""
        admin = User(
            telegram_id=123456789,
            username="admin",
            first_name="Admin",
            last_name="User",
            role=UserRole.ADMIN
        )
        db_session.add(admin)
        db_session.commit()
        return admin
    
    @pytest.fixture
    def regular_user(self, db_session):
        """Создание обычного пользователя"""
        user = User(
            telegram_id=987654321,
            username="user",
            first_name="Regular",
            last_name="User",
            role=UserRole.USER
        )
        db_session.add(user)
        db_session.commit()
        return user

    @pytest.mark.asyncio
    async def test_admin_command_success(self, bot_with_env, mock_update, mock_context, admin_user):
        """Тест успешной команды /admin"""
        mock_update.effective_user.id = admin_user.telegram_id
        
        await bot_with_env.admin_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        
        # Проверяем что сообщение содержит кнопки
        assert call_args[1]['reply_markup'] is not None
        assert "Админ панель:" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_admin_command_non_admin(self, bot_with_env, mock_update, mock_context, regular_user):
        """Тест команды /admin от обычного пользователя"""
        mock_update.effective_user.id = regular_user.telegram_id
        
        await bot_with_env.admin_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "Нет прав" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_stats_command_success(self, bot_with_env, mock_update, mock_context, admin_user, db_session):
        """Тест успешной команды /stats"""
        mock_update.effective_user.id = admin_user.telegram_id
        
        # Добавляем тестовые данные
        user = User(telegram_id=555555555, role=UserRole.USER)
        db_session.add(user)
        db_session.flush()
        
        trans = Transcription(
            user_id=user.id,
            status='completed',
            processing_time=10,
            text_length=100
        )
        db_session.add(trans)
        db_session.commit()
        
        await bot_with_env.stats_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        
        assert "Статистика:" in call_args
        assert "Пользователи" in call_args
        assert "Транскрипции" in call_args
        assert "⏰" in call_args

    @pytest.mark.asyncio
    async def test_stats_command_non_admin(self, bot_with_env, mock_update, mock_context, regular_user):
        """Тест команды /stats от обычного пользователя"""
        mock_update.effective_user.id = regular_user.telegram_id
        
        await bot_with_env.stats_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Нет прав" in call_args

    @pytest.mark.asyncio
    async def test_users_command_success(self, bot_with_env, mock_update, mock_context, admin_user):
        """Тест успешной команды /users"""
        mock_update.effective_user.id = admin_user.telegram_id
        
        await bot_with_env.users_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        
        assert "Пользователи:" in call_args
        assert admin_user.get_full_name() in call_args

    @pytest.mark.asyncio
    async def test_users_command_non_admin(self, bot_with_env, mock_update, mock_context, regular_user):
        """Тест команды /users от обычного пользователя"""
        mock_update.effective_user.id = regular_user.telegram_id
        
        await bot_with_env.users_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Нет прав" in call_args

    @pytest.mark.asyncio
    async def test_block_command_success(self, bot_with_env, mock_update, mock_context, admin_user, regular_user):
        """Тест успешной команды /block"""
        mock_update.effective_user.id = admin_user.telegram_id
        mock_context.args = [str(regular_user.telegram_id), "Test reason"]
        
        await bot_with_env.block_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        
        assert "заблокирован" in call_args
        assert str(regular_user.telegram_id) in call_args
        assert "Test reason" in call_args

    @pytest.mark.asyncio
    async def test_block_command_non_admin(self, bot_with_env, mock_update, mock_context, regular_user, admin_user):
        """Тест команды /block от обычного пользователя"""
        mock_update.effective_user.id = regular_user.telegram_id
        mock_context.args = [str(admin_user.telegram_id), "Test reason"]
        
        await bot_with_env.block_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Нет прав" in call_args

    @pytest.mark.asyncio
    async def test_block_command_no_args(self, bot_with_env, mock_update, mock_context, admin_user):
        """Тест команды /block без аргументов"""
        mock_update.effective_user.id = admin_user.telegram_id
        mock_context.args = []
        
        await bot_with_env.block_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "/block <user_id>" in call_args

    @pytest.mark.asyncio
    async def test_unblock_command_success(self, bot_with_env, mock_update, mock_context, admin_user, regular_user, db_session):
        """Тест успешной команды /unblock"""
        # Сначала блокируем пользователя
        regular_user.is_blocked = True
        db_session.commit()
        
        mock_update.effective_user.id = admin_user.telegram_id
        mock_context.args = [str(regular_user.telegram_id), "Test unblock reason"]
        
        await bot_with_env.unblock_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        
        assert "разблокирован" in call_args
        assert str(regular_user.telegram_id) in call_args
        assert "Test unblock reason" in call_args

    @pytest.mark.asyncio
    async def test_profile_command_success(self, bot_with_env, mock_update, mock_context, regular_user):
        """Тест успешной команды /profile"""
        mock_update.effective_user.id = regular_user.telegram_id
        
        await bot_with_env.profile_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        
        assert "Профиль:" in call_args
        assert "Инфо:" in call_args
        assert regular_user.get_full_name() in call_args
        assert str(regular_user.telegram_id) in call_args

    @pytest.mark.asyncio
    async def test_profile_command_user_not_found(self, bot_with_env, mock_update, mock_context):
        """Тест команды /profile для несуществующего пользователя"""
        mock_update.effective_user.id = 999999999
        
        await bot_with_env.profile_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "не найден" in call_args

    @pytest.mark.asyncio
    async def test_history_command_success(self, bot_with_env, mock_update, mock_context, regular_user, db_session):
        """Тест успешной команды /history"""
        # Создаем транскрипции для пользователя
        user = db_session.query(User).filter(User.telegram_id == regular_user.telegram_id).first()
        
        trans1 = Transcription(
            user_id=user.id,
            status='completed',
            input_text='Test transcription 1',
            processing_time=10,
            text_length=20
        )
        trans2 = Transcription(
            user_id=user.id,
            status='failed',
            error_message='Test error',
            text_length=0
        )
        
        db_session.add_all([trans1, trans2])
        db_session.commit()
        
        mock_update.effective_user.id = regular_user.telegram_id
        
        await bot_with_env.history_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        
        assert "История:" in call_args
        assert "Test transcription 1" in call_args

    @pytest.mark.asyncio
    async def test_history_command_empty(self, bot_with_env, mock_update, mock_context, regular_user):
        """Тест команды /history без транскрипций"""
        mock_update.effective_user.id = regular_user.telegram_id
        
        await bot_with_env.history_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Транскрипций нет" in call_args

    @pytest.mark.asyncio
    async def test_admin_callback_handler_stats(self, bot_with_env, mock_update, mock_context, admin_user):
        """Тест обработчика callback для статистики"""
        mock_update.callback_query = Mock()
        mock_update.callback_query.answer = AsyncMock()
        mock_update.callback_query.edit_message_text = AsyncMock()
        mock_update.callback_query.data = "admin_stats"
        mock_update.effective_user.id = admin_user.telegram_id
        
        await bot_with_env.callback_handler(mock_update, mock_context)
        
        mock_update.callback_query.answer.assert_called_once()
        mock_update.callback_query.edit_message_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_admin_callback_handler_non_admin(self, bot_with_env, mock_update, mock_context, regular_user):
        """Тест callback обработчика от обычного пользователя"""
        mock_update.callback_query = Mock()
        mock_update.callback_query.answer = AsyncMock()
        mock_update.callback_query.edit_message_text = AsyncMock()
        mock_update.callback_query.data = "admin_stats"
        mock_update.effective_user.id = regular_user.telegram_id
        
        await bot_with_env.callback_handler(mock_update, mock_context)
        
        mock_update.callback_query.answer.assert_called_once()
        mock_update.callback_query.edit_message_text.assert_called_once()
        
        call_args = mock_update.callback_query.edit_message_text.call_args[0][0]
        assert "Нет прав" in call_args

    def test_is_admin_admin_user(self, bot_with_env, admin_user):
        """Тест метода is_admin для администратора"""
        assert bot_with_env.is_admin(admin_user.telegram_id) == True

    def test_is_admin_regular_user(self, bot_with_env, regular_user):
        """Тест метода is_admin для обычного пользователя"""
        assert bot_with_env.is_admin(regular_user.telegram_id) == False

    def test_is_admin_nonexistent_user(self, bot_with_env):
        """Тест метода is_admin для несуществующего пользователя"""
        assert bot_with_env.is_admin(999999999) == False

    @pytest.fixture
    def bot_with_admin_usernames(self, db_session):
        """Фикстура для бота с ADMIN_USERNAMES"""
        with patch.dict(os.environ, {
            'TELEGRAM_BOT_TOKEN': 'test_token',
            'ADMIN_USERNAMES': 'test_admin,admin_user'  # тестовые usernames
        }):
            def mock_get_db():
                while True:
                    yield db_session

            with patch('database.models.get_db', mock_get_db):
                with patch('database.models.create_tables'):
                    from src.bot import TelegramBot
                    bot = TelegramBot()
                    # Устанавливаем AdminService напрямую
                    from utils.admin_service import AdminService
                    bot.admin_service = AdminService(db_session)
                    return bot

    def test_is_admin_by_username_from_env(self, bot_with_admin_usernames):
        """Тест проверки администратора по username из ADMIN_USERNAMES"""
        # Пользователь с username из ADMIN_USERNAMES должен быть админом
        assert bot_with_admin_usernames.is_admin(111111111, "test_admin") == True
        assert bot_with_admin_usernames.is_admin(222222222, "admin_user") == True

        # Пользователь с другим username не должен быть админом
        assert bot_with_admin_usernames.is_admin(333333333, "regular_user") == False

        # Пользователь без username не должен быть админом
        assert bot_with_admin_usernames.is_admin(444444444, None) == False

        # Проверка регистра
        assert bot_with_admin_usernames.is_admin(555555555, "TEST_ADMIN") == True  # регистр не важен

    def test_admin_usernames_initialization(self, bot_with_admin_usernames):
        """Тест инициализации списка администраторов из ADMIN_USERNAMES"""
        # Проверяем, что список admin_usernames правильно инициализирован
        assert hasattr(bot_with_admin_usernames, 'admin_usernames')
        assert isinstance(bot_with_admin_usernames.admin_usernames, list)
        assert "test_admin" in bot_with_admin_usernames.admin_usernames
        assert "admin_user" in bot_with_admin_usernames.admin_usernames
        assert len(bot_with_admin_usernames.admin_usernames) == 2

    @pytest.mark.asyncio
    async def test_start_command_with_admin(self, bot_with_env, mock_update, mock_context, admin_user):
        """Тест команды /start для администратора"""
        mock_update.effective_user.id = admin_user.telegram_id
        
        await bot_with_env.start_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        
        assert "AI Транскрибатор" in call_args
        assert "Админ команды:" in call_args
        assert "/admin" in call_args

    @pytest.mark.asyncio
    async def test_start_command_with_regular_user(self, bot_with_env, mock_update, mock_context, regular_user):
        """Тест команды /start для обычного пользователя"""
        mock_update.effective_user.id = regular_user.telegram_id
        
        await bot_with_env.start_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        
        assert "AI Транскрибатор" in call_args
        assert "Административные команды" not in call_args
        assert "/admin" not in call_args

    @pytest.mark.asyncio
    async def test_help_command_with_admin(self, bot_with_env, mock_update, mock_context, admin_user):
        """Тест команды /help для администратора"""
        mock_update.effective_user.id = admin_user.telegram_id
        
        await bot_with_env.help_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        
        assert "Помощь" in call_args
        assert "Админ команды:" in call_args
        assert "/admin" in call_args

    @pytest.mark.asyncio
    async def test_help_command_with_regular_user(self, bot_with_env, mock_update, mock_context, regular_user):
        """Тест команды /help для обычного пользователя"""
        mock_update.effective_user.id = regular_user.telegram_id
        
        await bot_with_env.help_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        
        assert "Помощь" in call_args
        assert "Для администраторов" not in call_args