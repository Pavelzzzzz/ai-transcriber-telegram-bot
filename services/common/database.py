import glob
import logging
import os
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import NullPool

logger = logging.getLogger(__name__)

Base = declarative_base()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{os.getenv('DB_USER', 'bot')}:{os.getenv('DB_PASSWORD', 'secret')}@"
    f"{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME', 'ai_transcriber')}",
)

if "postgres" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://")

try:
    engine = create_engine(
        DATABASE_URL, pool_size=5, max_overflow=10, pool_pre_ping=True, echo=False
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
        with engine.connect():
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


def init_schema_migrations_table() -> None:
    """Create schema_migrations table if it doesn't exist."""
    try:
        with engine.connect() as conn:
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version VARCHAR(10) PRIMARY KEY,
                    description TEXT,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            )
            conn.commit()
    except Exception as e:
        logger.warning(f"Could not create schema_migrations table: {e}")


def get_applied_migrations() -> set:
    """Get set of already applied migration versions."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version FROM schema_migrations"))
            return {row[0] for row in result}
    except Exception:
        return set()


def run_migrations() -> None:
    """Run all pending migrations automatically."""
    init_schema_migrations_table()
    applied = get_applied_migrations()

    migrations_dir = Path(__file__).parent.parent.parent / "db" / "migrations"
    migration_files = sorted(migrations_dir.glob("*.sql"))

    for migration_file in migration_files:
        version = migration_file.stem.split("_")[0]
        if version in applied:
            continue

        try:
            logger.info(f"Applying migration: {migration_file.name}")
            with open(migration_file) as f:
                sql = f.read()

            with engine.connect() as conn:
                conn.execute(text(sql))
                conn.commit()

            logger.info(f"Migration {version} applied successfully")
        except Exception as e:
            logger.error(f"Failed to apply migration {migration_file.name}: {e}")


try:
    run_migrations()
except Exception as e:
    logger.warning(f"Auto migration check failed (this is normal on first run): {e}")

try:
    from sqlalchemy import text

    with engine.connect() as conn:
        conn.execute(
            text("ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS company VARCHAR(100)")
        )
        conn.commit()
        logger.info("Ensured company column exists")
except Exception as e:
    logger.warning(f"Could not ensure company column: {e}")

# Fallback for chat_id column - ensures it exists even if migration fails
try:
    from sqlalchemy import text

    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE task_queue ADD COLUMN IF NOT EXISTS chat_id BIGINT"))
        conn.commit()
        logger.info("Ensured chat_id column in task_queue")
except Exception as e:
    logger.warning(f"Could not ensure chat_id column: {e}")

# Fallback for task_metadata column - ensures it exists (renamed from metadata)
try:
    from sqlalchemy import text

    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE task_queue ADD COLUMN IF NOT EXISTS task_metadata JSONB"))
        conn.commit()
        logger.info("Ensured task_metadata column in task_queue")
except Exception as e:
    logger.warning(f"Could not ensure task_metadata column: {e}")
