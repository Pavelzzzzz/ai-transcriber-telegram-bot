"""Database connection manager with connection pooling and proper session management"""

import logging
import os
from contextlib import contextmanager, asynccontextmanager
from sqlalchemy import create_engine, event, exc
from sqlalchemy.orm import sessionmaker, Session, scoped_session
from sqlalchemy.pool import QueuePool, StaticPool
from typing import Generator, Optional, AsyncGenerator
from database.models import Base
from src.exceptions import DatabaseError, ErrorHandler

logger = logging.getLogger(__name__)

# Конфигурация connection pool
POOL_SIZE = 10
MAX_OVERFLOW = 20
POOL_TIMEOUT = 30
POOL_RECYCLE = 3600  # 1 час
POOL_PRE_PING = True

class DatabaseManager:
    """Управление подключениями к базе данных с connection pooling"""
    
    def __init__(self):
        self.engine = None
        self.session_factory = None
        self._initialize_engine()
    
    def _initialize_engine(self):
        """Инициализация SQLAlchemy engine с connection pooling"""
        try:
            database_url = os.getenv('DATABASE_URL', 'sqlite:///bot.db')
            
            # Настройки engine в зависимости от типа базы данных
            if database_url.startswith('sqlite'):
                # SQLite с StaticPool для потоко-безопасности
                self.engine = create_engine(
                    database_url,
                    poolclass=StaticPool,
                    connect_args={
                        "check_same_thread": False,
                        "timeout": 20
                    },
                    echo=os.getenv('DEBUG', 'False').lower() == 'true'
                )
            else:
                # PostgreSQL/MySQL с QueuePool
                self.engine = create_engine(
                    database_url,
                    poolclass=QueuePool,
                    pool_size=POOL_SIZE,
                    max_overflow=MAX_OVERFLOW,
                    pool_timeout=POOL_TIMEOUT,
                    pool_recycle=POOL_RECYCLE,
                    pool_pre_ping=POOL_PRE_PING,
                    pool_reset_on_return='commit',
                    echo=os.getenv('DEBUG', 'False').lower() == 'true'
                )
            
            # Создание session factory
            self.session_factory = sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False
            )
            
            # Добавление event handlers для логирования
            self._add_event_listeners()
            
            logger.info("Database engine initialized with connection pooling")
            
        except Exception as e:
            logger.error(f"Failed to initialize database engine: {e}")
            raise DatabaseError(
                message="Database initialization failed",
                context={"database_url": database_url, "error": str(e)}
            )
    
    def _add_event_listeners(self):
        """Добавление event listeners для мониторинга"""
        
        @event.listens_for(self.engine, "connect")
        def receive_connect(dbapi_connection, connection_record):
            logger.debug("Database connection established")
        
        @event.listens_for(self.engine, "checkout")
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            logger.debug("Connection checked out from pool")
        
        @event.listens_for(self.engine, "checkin")
        def receive_checkin(dbapi_connection, connection_record):
            logger.debug("Connection checked in to pool")
        
        @event.listens_for(self.engine, "close")
        def receive_close(dbapi_connection, connection_record):
            logger.debug("Database connection closed")
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Получение сессии с автоматическим управлением"""
        session = scoped_session(self.session_factory)
        
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            ErrorHandler.log_error(e, {"operation": "database_session"})
            raise DatabaseError(
                message="Database operation failed",
                query=str(e) if hasattr(e, 'statement') else None,
                context={"error": str(e)}
            )
        finally:
            session.close()
    
    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[Session, None]:
        """Асинхронное получение сессии"""
        session = scoped_session(self.session_factory)
        
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            ErrorHandler.log_error(e, {"operation": "async_database_session"})
            raise DatabaseError(
                message="Async database operation failed",
                query=str(e) if hasattr(e, 'statement') else None,
                context={"error": str(e)}
            )
        finally:
            session.close()
    
    def create_tables(self):
        """Создание всех таблиц"""
        try:
            Base.metadata.create_all(self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            ErrorHandler.log_error(e, {"operation": "create_tables"})
            raise DatabaseError(
                message="Failed to create database tables",
                context={"error": str(e)}
            )
    
    def get_engine_info(self) -> dict:
        """Получение информации о состоянии engine"""
        pool = self.engine.pool
        
        if hasattr(pool, 'size'):
            return {
                "pool_type": type(pool).__name__,
                "size": getattr(pool, 'size', 0),
                "checked_in": getattr(pool, 'checkedin', 0),
                "checked_out": getattr(pool, 'checkedout', 0),
                "overflow": getattr(pool, 'overflow', 0),
                "invalid": getattr(pool, 'invalid', 0)
            }
        return {"pool_type": "N/A"}
    
    def close_all_connections(self):
        """Закрытие всех соединений с базой данных"""
        try:
            self.engine.dispose()
            logger.info("All database connections closed")
        except Exception as e:
            ErrorHandler.log_error(e, {"operation": "close_connections"})
            raise DatabaseError(
                message="Failed to close database connections",
                context={"error": str(e)}
            )

# Глобальный экземпляр database manager
db_manager = DatabaseManager()

def get_db() -> Session:
    """Получение сессии базы данных (backward compatibility)"""
    session = db_manager.session_factory()
    return session

def create_tables():
    """Создание таблиц (backward compatibility)"""
    db_manager.create_tables()

@contextmanager
def database_session() -> Generator[Session, None, None]:
    """Контекстный менеджер для работы с базой данных"""
    with db_manager.get_session() as session:
        yield session