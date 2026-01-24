from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Enum, Float
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime, timezone
import enum
import os

Base = declarative_base()

class UserRole(enum.Enum):
    USER = "user"
    ADMIN = "admin"

class User(Base):
    """Модель пользователя"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_blocked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    last_activity = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Связи
    transcriptions = relationship("Transcription", back_populates="user", cascade="all, delete-orphan")
    admin_logs = relationship("AdminLog", back_populates="admin", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, username={self.username})>"
    
    def is_admin(self):
        return self.role == UserRole.ADMIN
    
    def get_full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.username:
            return f"@{self.username}"
        else:
            return f"User #{self.telegram_id}"

class TranscriptionType(enum.Enum):
    """Типы транскрипации"""
    IMAGE_TO_TEXT = "image_to_text"  # Изображение -> Текст
    AUDIO_TO_TEXT = "audio_to_text"  # Аудио -> Текст
    TEXT_TO_AUDIO = "text_to_audio"  # Текст -> Аудио

class Transcription(Base):
    """Модель транскрипации (двунаправленная)"""
    __tablename__ = 'transcriptions'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    transcription_type = Column(Enum(TranscriptionType), nullable=False, default=TranscriptionType.TEXT_TO_AUDIO)

    # Для TEXT_TO_AUDIO: входной текст
    # Для AUDIO_TO_TEXT: распознанный текст
    input_text = Column(Text, nullable=True)

    # Для TEXT_TO_AUDIO: сгенерированный аудиофайл
    # Для AUDIO_TO_TEXT: входной аудиофайл
    input_audio_path = Column(String(500), nullable=True)

    # Для TEXT_TO_AUDIO: сгенерированный аудиофайл (дублирование для совместимости)
    # Для AUDIO_TO_TEXT: может быть пустым
    output_audio_path = Column(String(500), nullable=True)

    # Метаданные
    text_length = Column(Integer, nullable=False, default=0)
    processing_time = Column(Integer, nullable=True)  # в секундах
    audio_duration = Column(Float, nullable=True)  # длительность аудио в секундах

    # Статус и ошибки
    status = Column(String(20), default='pending', nullable=False)  # pending, processing, completed, failed
    error_message = Column(Text, nullable=True)

    # Временные метки
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Связи
    user = relationship("User", back_populates="transcriptions")

    def __repr__(self):
        return f"<Transcription(id={self.id}, user_id={self.user_id}, type={self.transcription_type.value}, status={self.status})>"

    def is_text_to_audio(self):
        """Проверяет, является ли транскрипация преобразованием текста в аудио"""
        return self.transcription_type == TranscriptionType.TEXT_TO_AUDIO

    def is_audio_to_text(self):
        """Проверяет, является ли транскрипация преобразованием аудио в текст"""
        return self.transcription_type == TranscriptionType.AUDIO_TO_TEXT

class AdminLog(Base):
    """Модель логов действий администратора"""
    __tablename__ = 'admin_logs'
    
    id = Column(Integer, primary_key=True)
    admin_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    action = Column(String(100), nullable=False)  # block_user, unblock_user, etc.
    target_user_id = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Связи
    admin = relationship("User", back_populates="admin_logs")
    
    def __repr__(self):
        return f"<AdminLog(id={self.id}, action={self.action})>"

class BotStatistics(Base):
    """Модель статистики бота"""
    __tablename__ = 'bot_statistics'
    
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False, index=True)  # дата статистики
    total_users = Column(Integer, default=0, nullable=False)
    active_users = Column(Integer, default=0, nullable=False)  # пользователи за день
    total_transcriptions = Column(Integer, default=0, nullable=False)
    successful_transcriptions = Column(Integer, default=0, nullable=False)
    failed_transcriptions = Column(Integer, default=0, nullable=False)
    total_processing_time = Column(Integer, default=0, nullable=False)  # в секундах
    avg_processing_time = Column(Integer, default=0, nullable=False)  # в секундах
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    def __repr__(self):
        return f"<BotStatistics(date={self.date}, total_users={self.total_users})>"

# Создание соединения с базой данных
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///bot.db')
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Получение сессии базы данных"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """Создание таблиц"""
    Base.metadata.create_all(bind=engine)