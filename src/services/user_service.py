"""
User service for managing user data and statistics
"""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from config import BotConfig
from database.models import Transcription, User, UserRole
from src.database_manager import get_db

from ..core.exceptions import DatabaseError

logger = logging.getLogger(__name__)


class UserService:
    """
    Service for managing users and their data
    """

    def __init__(self, config: BotConfig):
        self.config = config

    async def get_db_session(self) -> Session:
        """Get database session with error handling"""
        try:
            return next(get_db())
        except Exception as e:
            raise DatabaseError(
                f"Failed to get database session: {e}",
                operation="get_session"
            )

    async def get_or_create_user(
        self,
        telegram_id: int,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None
    ) -> User:
        """Get existing user or create new one"""
        try:
            session = await self.get_db_session()

            # Try to get existing user
            stmt = select(User).where(User.telegram_id == telegram_id)
            user = session.execute(stmt).scalar_one_or_none()

            if user:
                # Update user information if changed
                user.username = username
                user.first_name = first_name
                user.last_name = last_name
                user.last_activity = datetime.utcnow()
                session.commit()
                logger.info(f"Updated existing user: {user.telegram_id}")
            else:
                # Create new user
                user = User(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    role=UserRole.USER,  # Default role
                    created_at=datetime.utcnow(),
                    last_activity=datetime.utcnow()
                )

                session.add(user)
                session.commit()
                logger.info(f"Created new user: {user.telegram_id}")

            session.close()
            return user

        except Exception as e:
            session.close()
            raise DatabaseError(
                f"Failed to get or create user {telegram_id}: {e}",
                operation="get_or_create_user",
                user_id=telegram_id
            )

    async def get_user_by_telegram_id(self, telegram_id: int) -> User | None:
        """Get user by telegram ID"""
        try:
            session = await self.get_db_session()

            stmt = select(User).where(User.telegram_id == telegram_id)
            user = session.execute(stmt).scalar_one_or_none()

            session.close()
            return user

        except Exception as e:
            session.close()
            raise DatabaseError(
                f"Failed to get user {telegram_id}: {e}",
                operation="get_user_by_telegram_id",
                user_id=telegram_id
            )

    async def update_user_mode(self, telegram_id: int, mode: str) -> None:
        """Update user's current mode"""
        try:
            session = await self.get_db_session()

            stmt = select(User).where(User.telegram_id == telegram_id)
            user = session.execute(stmt).scalar_one_or_none()

            if user:
                user.current_mode = mode
                user.last_activity = datetime.utcnow()
                session.commit()
                logger.info(f"Updated user {telegram_id} mode to {mode}")
            else:
                logger.warning(f"User {telegram_id} not found for mode update")

            session.close()

        except Exception as e:
            session.close()
            raise DatabaseError(
                f"Failed to update user mode {telegram_id}: {e}",
                operation="update_user_mode",
                user_id=telegram_id
            )

    async def get_user_stats(self, telegram_id: int) -> dict[str, Any]:
        """Get user statistics"""
        try:
            session = await self.get_db_session()

            # Get user
            stmt = select(User).where(User.telegram_id == telegram_id)
            user = session.execute(stmt).scalar_one_or_none()

            if not user:
                return {}

            # Get transcription stats
            stmt = select(
                func.count(Transcription.id).label('total_messages'),
                func.sum(func.case([(Transcription.input_text.isnot(None), 1)], else_=0)).label('text_messages'),
                func.sum(func.case([(Transcription.file_path.like('%image%'), 1)], else_=0)).label('ocr_count'),
                func.sum(func.case([(Transcription.file_path.like('%audio%'), 1)], else_=0)).label('transcription_count'),
                func.sum(func.case([(Transcription.output_audio_path.isnot(None), 1)], else_=0)).label('tts_count'),
                func.sum(func.case([(Transcription.input_text.isnot(None), 1)], else_=0)).label('correction_count')
            ).where(
                Transcription.user_id == user.id,
                Transcription.status == 'completed'
            )

            stats = session.execute(stmt).first() or {}

            result = {
                'total_messages': stats.total_messages or 0,
                'text_messages': stats.text_messages or 0,
                'ocr_count': stats.ocr_count or 0,
                'transcription_count': stats.transcription_count or 0,
                'tts_count': stats.tts_count or 0,
                'correction_count': stats.correction_count or 0
            }

            session.close()
            return result

        except Exception as e:
            session.close()
            raise DatabaseError(
                f"Failed to get user stats {telegram_id}: {e}",
                operation="get_user_stats",
                user_id=telegram_id
            )

    async def block_user(self, telegram_id: int, reason: str, admin_id: int) -> bool:
        """Block user (admin only)"""
        try:
            session = await self.get_db_session()

            stmt = select(User).where(User.telegram_id == telegram_id)
            user = session.execute(stmt).scalar_one_or_none()

            if user:
                user.is_blocked = True
                user.block_reason = reason
                user.blocked_by = admin_id
                user.blocked_at = datetime.utcnow()
                user.last_activity = datetime.utcnow()
                session.commit()

                logger.info(f"User {telegram_id} blocked by {admin_id}, reason: {reason}")
                session.close()
                return True
            else:
                logger.warning(f"User {telegram_id} not found for blocking")
                session.close()
                return False

        except Exception as e:
            session.close()
            raise DatabaseError(
                f"Failed to block user {telegram_id}: {e}",
                operation="block_user",
                user_id=telegram_id
            )

    async def unblock_user(self, telegram_id: int, reason: str, admin_id: int) -> bool:
        """Unblock user (admin only)"""
        try:
            session = await self.get_db_session()

            stmt = select(User).where(User.telegram_id == telegram_id)
            user = session.execute(stmt).scalar_one_or_none()

            if user:
                user.is_blocked = False
                user.block_reason = None
                user.blocked_by = None
                user.blocked_at = None
                user.unblocked_by = admin_id
                user.unblocked_at = datetime.utcnow()
                user.last_activity = datetime.utcnow()
                session.commit()

                logger.info(f"User {telegram_id} unblocked by {admin_id}, reason: {reason}")
                session.close()
                return True
            else:
                logger.warning(f"User {telegram_id} not found for unblocking")
                session.close()
                return False

        except Exception as e:
            session.close()
            raise DatabaseError(
                f"Failed to unblock user {telegram_id}: {e}",
                operation="unblock_user",
                user_id=telegram_id
            )

    async def get_all_users(self, limit: int = 50) -> list[User]:
        """Get all users with pagination"""
        try:
            session = await self.get_db_session()

            stmt = select(User).order_by(User.last_activity.desc()).limit(limit)
            users = session.execute(stmt).scalars().all()

            session.close()
            return list(users)

        except Exception as e:
            session.close()
            raise DatabaseError(
                f"Failed to get all users: {e}",
                operation="get_all_users"
            )

    async def get_global_stats(self) -> dict[str, Any]:
        """Get global bot statistics - simplified working version"""
        try:
            session = await self.get_db_session()

            # Basic counts that should work
            total_users = session.execute(select(func.count(User.id))).scalar() or 0
            blocked_users = session.execute(
                select(func.count(User.id)).where(User.is_blocked == True)
            ).scalar() or 0
            total_transcriptions = session.execute(select(func.count(Transcription.id))).scalar() or 0

            result = {
                'users': {
                    'total': total_users,
                    'blocked': blocked_users,
                    'admins': 0,  # Simplified for now
                    'active_today': 0  # Simplified for now
                },
                'transcriptions': {
                    'total': total_transcriptions,
                    'successful': 0,  # Simplified for now
                    'failed': 0,
                    'success_rate': 0.0,
                    'avg_processing_time': 0.0,
                    'total_text_length': 0
                },
                'modes': {
                    'img_to_text': 0,
                    'audio_to_text': 0,
                    'text_to_audio': 0,
                    'text_to_text': 0
                }
            }

            session.close()
            return result

        except Exception as e:
            logger.error(f"Failed to get global stats: {e}")
            return {
                'users': {'total': 0, 'blocked': 0, 'admins': 0, 'active_today': 0},
                'transcriptions': {'total': 0, 'successful': 0, 'failed': 0, 'success_rate': 0, 'avg_processing_time': 0.0, 'total_text_length': 0},
                'modes': {'img_to_text': 0, 'audio_to_text': 0, 'text_to_audio': 0, 'text_to_text': 0}
            }

    async def is_user_blocked(self, telegram_id: int) -> bool:
        """Check if user is blocked"""
        try:
            session = await self.get_db_session()

            stmt = select(User.is_blocked).where(User.telegram_id == telegram_id)
            is_blocked = session.execute(stmt).scalar() or False

            session.close()
            return is_blocked

        except Exception as e:
            session.close()
            logger.error(f"Error checking if user {telegram_id} is blocked: {e}")
            return False  # Default to not blocked on error

    async def update_user_activity(self, telegram_id: int) -> None:
        """Update user's last activity timestamp"""
        try:
            session = await self.get_db_session()

            stmt = select(User).where(User.telegram_id == telegram_id)
            user = session.execute(stmt).scalar_one_or_none()

            if user:
                user.last_activity = datetime.utcnow()
                session.commit()

            session.close()

        except Exception as e:
            session.close()
            logger.error(f"Error updating activity for user {telegram_id}: {e}")
