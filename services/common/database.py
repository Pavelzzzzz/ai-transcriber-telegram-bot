import os
import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.pool import NullPool

logger = logging.getLogger(__name__)

Base = declarative_base()

DATABASE_URL = os.getenv(
    'DATABASE_URL',
    f"postgresql://{os.getenv('DB_USER', 'bot')}:{os.getenv('DB_PASSWORD', 'secret')}@"
    f"{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME', 'ai_transcriber')}"
)

if 'postgres' in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://')

try:
    engine = create_engine(
        DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        echo=False
    )
except Exception as e:
    logger.warning(f"Failed to create database engine: {e}. Using NullPool (no connection pooling)")
    engine = create_engine(DATABASE_URL, poolclass=NullPool)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    try:
        with engine.connect() as conn:
            pass
        logger.info("Database connection established")
    except Exception as e:
        logger.warning(f"Database connection failed: {e}")


def check_db_health() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
