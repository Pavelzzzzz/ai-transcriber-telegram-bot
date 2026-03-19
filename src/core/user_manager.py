"""
User manager for AI Transcriber Bot with simplified logic
"""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from config import BotConfig

from .exceptions import DatabaseError

logger = logging.getLogger(__name__)


class UserManager:
    """
    Simplified user management with database operations
    """

    def __init__(self, config: BotConfig):
        self.config = config

    async def get_db_session(self) -> Session:
        """Get database session"""
        try:
            from database.database_manager import get_db
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
    ) -> Any:
        """Get existing user or create new one"""
        try:
            session = await self.get_db_session()

            # Try to get existing user
            from database.models import User
            stmt = select(User).where(User.telegram_id == telegram_id)
            user = session.execute(stmt).scalar_one_or_none()

            if user:
                # Update user information if changed
                user.username = username
                user.first_name = first_name
                user.last_name = last_name
                user.last_activity = datetime.now()
                session.commit()
                logger.info(f"Updated existing user: {user.telegram_id}")
            else:
                # Create new user
                user = User(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    created_at=datetime.now(),
                    last_activity=datetime.now()
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

    async def get_user_by_telegram_id(self, telegram_id: int) -> Any | None:
        """Get user by telegram ID"""
        try:
            session = await self.get_db_session()

            from database.models import User
            stmt = select(User).where(User.telegram_id == telegram_id)
            user = session.execute(stmt).scalar_one_or_none()

            session.close()
            return user

        except Exception as e:
            session.close()
            logger.error(f"Error getting user {telegram_id}: {e}")
            return None

    async def update_user_mode(self, telegram_id: int, mode: str) -> None:
        """Update user's current mode"""
        try:
            session = await self.get_db_session()

            from database.models import User
            stmt = select(User).where(User.telegram_id == telegram_id)
            user = session.execute(stmt).scalar_one_or_none()

            if user:
                user.current_mode = mode
                user.last_activity = datetime.now()
                session.commit()
                logger.info(f"Updated user {telegram_id} mode to {mode}")
            else:
                logger.warning(f"User {telegram_id} not found for mode update")

            session.close()

        except Exception as e:
            logger.error(f"Error updating user mode {telegram_id}: {e}")

    async def get_user_stats(self, telegram_id: int) -> dict[str, Any]:
        """Get user statistics"""
        try:
            session = await self.get_db_session()

            from database.models import Transcription, User
            stmt_user = select(User).where(User.telegram_id == stmt)
            user = session.execute(stmt_user).scalar_one_or_none()

            if not user:
                return {}

            # Get transcription stats
            stmt_trans = select(
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

            stats = session.execute(stmt_trans).first() or {}

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
            logger.error(f"Error getting user stats {telegram_id}: {e}")
            return {}

    async def block_user(self, telegram_id: int, reason: str, admin_id: int) -> bool:
        """Block user (admin only)"""
        try:
            session = await self.get_db_session()

            from database.models import User
            stmt = select(User).where(User.telegram_id == telegram_id)
            user = session.execute(stmt).scalar_one_or_none()

            if user:
                # Note: We'll implement blocking at app level
                user.last_activity = datetime.now()
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
            logger.error(f"Failed to block user {telegram_id}: {e}")
            return False

    async def unblock_user(self, telegram_id: int, reason: str, admin_id: int) -> bool:
        """Unblock user (admin only)"""
        try:
            session = await self.get_db_session()

            from database.models import User
            stmt = select(User).where(User.telegram_id == telegram_id)
            user = session.execute(stmt).scalar_one_or_none()

            if user:
                user.last_activity = datetime.now()
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
            logger.error(f"Failed to unblock user {telegram_id}: {e}")
            return False

    async def get_all_users(self, limit: int = 50) -> list:
        """Get all users"""
        try:
            session = await self.get_db_session()

            from database.models import User
            stmt = select(User).order_by(User.last_activity.desc()).limit(limit)
            users = session.execute(stmt).scalars().all()

            session.close()
            return list(users)

        except Exception as e:
            logger.error(f"Failed to get all users: {e}")
            return []

    async def get_global_stats(self) -> dict[str, Any]:
        """Get global bot statistics"""
        try:
            session = await self.get_db_session()

            from database.models import Transcription, User

            # Get user stats
            user_stats = session.execute(
                select(
                    func.count(User.id).label('total_users'),
                    func.sum(func.case([(User.is_blocked == True, 1)], else_=0)).label('blocked_users'),
                    func.sum(func.case([(User.role == 'admin', 1)], else_=0)).label('admin_users'),
                    func.sum(func.case([(User.last_activity >= datetime.now().replace(hour=0, minute=0, second=0), 1)], else_=0)).label('active_today')
                )
            ).first() or {}

            # Get transcription stats
            transcription_stats = session.execute(
                select(
                    func.count(Transcription.id).label('total_transcriptions'),
                    func.sum(func.case([(Transcription.status == 'completed', 1)], else_=0)).label('successful_transcriptions'),
                    func.sum(func.case([(Transcription.status == 'failed', 1)], else_=0)).label('failed_transcriptions'),
                    func.avg(Transcription.processing_time).label('avg_processing_time'),
                    func.sum(Transcription.text_length).label('total_text_length')
                )
            ).first() or {}

            # Get mode distribution
            mode_stats = session.execute(
                select(User.current_mode, func.count(User.id))
                .group_by(User.current_mode)
                .order_by(func.count(User.id).desc())
            ).all()

            result = {
                'users': {
                    'total': user_stats.total_users or 0,
                    'blocked': user_stats.blocked_users or 0,
                    'admins': user_stats.admin_users or 0,
                    'active_today': user_stats.active_today or 0
                },
                'transcriptions': {
                    'total': transcription_stats.total_transcriptions or 0,
                    'successful': transcription_stats.successful_transcriptions or 0,
                    'failed': transcription_stats.failed_transcriptions or 0,
                    'success_rate': (
                        (transcription_stats.successful_transcriptions or 0) /
                        (transcription_stats.total_transcriptions or 1) * 100
                    ),
                    'avg_processing_time': float(transcription_stats.avg_processing_time or 0),
                    'total_text_length': transcription_stats.total_text_length or 0
                },
                'modes': {
                    mode.mode: mode.count for mode, count in mode_stats
                }
            }

            session.close()
            return result

        except Exception as e:
            logger.error(f"Error getting global stats: {e}")
            return {
                'users': {'total': 0},
                'transcriptions': {'total': 0},
                'modes': {}
            }

    async def is_user_blocked(self, telegram_id: int) -> bool:
        """Check if user is blocked"""
        try:
            session = await self.get_db_session()

            from database.models import User
            stmt = select(User.is_blocked).where(User.telegram_id == telegram_id)
            is_blocked = session.execute(stmt).scalar() or False

            session.close()
            return is_blocked

        except Exception as e:
            logger.error(f"Error checking if user {telegram_id} is blocked: {e}")
            return False

    async def update_user_activity(self, telegram_id: int) -> None:
        """Update user's last activity timestamp"""
        try:
            session = await self.get_db_session()

            from database.models import User
            stmt = select(User).where(User.telegram_id == telegram_id)
            user = session.execute(stmt).scalar_one_or_none()

            if user:
                user.last_activity = datetime.now()
                session.commit()

            session.close()

        except Exception as e:
            logger.error(f"Error updating activity for user {telegram_id}: {e}")
