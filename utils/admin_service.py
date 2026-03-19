from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from database.models import (
    AdminLog,
    BotStatistics,
    Transcription,
    TranscriptionType,
    User,
    UserRole,
)


class AdminService:
    """Сервис для административных функций"""

    def __init__(self, db: Session):
        self.db = db

    def is_admin(self, telegram_id: int) -> bool:
        """Проверка является ли пользователь администратором"""
        user = self.db.query(User).filter(User.telegram_id == telegram_id).first()
        return bool(user and user.is_admin())

    def get_admin_users(self) -> list[User]:
        """Получение списка всех администраторов"""
        return self.db.query(User).filter(User.role == UserRole.ADMIN).all()

    def get_user_statistics(self) -> dict[str, Any]:
        """Получение статистики по пользователям"""
        total_users = self.db.query(User).count()

        # Активные пользователи: last_activity не None и в последние 7 дней
        week_ago = datetime.now(UTC) - timedelta(days=7)
        active_users = (
            self.db.query(User)
            .filter(
                User.last_activity.isnot(None),
                User.last_activity >= week_ago,
                User.is_blocked == False,
            )
            .count()
        )

        blocked_users = self.db.query(User).filter(User.is_blocked == True).count()
        admin_users = self.db.query(User).filter(User.role == UserRole.ADMIN).count()

        return {
            "total_users": total_users,
            "active_users": active_users,
            "blocked_users": blocked_users,
            "admin_users": admin_users,
        }

    def get_transcription_statistics(self) -> dict[str, Any]:
        """Получение статистики по транскрипциям"""
        total_transcriptions = self.db.query(Transcription).count()
        successful_transcriptions = (
            self.db.query(Transcription).filter(Transcription.status == "completed").count()
        )
        failed_transcriptions = (
            self.db.query(Transcription).filter(Transcription.status == "failed").count()
        )

        # Статистика по типам транскрипций
        text_to_audio_count = (
            self.db.query(Transcription)
            .filter(Transcription.transcription_type == TranscriptionType.TEXT_TO_AUDIO)
            .count()
        )
        audio_to_text_count = (
            self.db.query(Transcription)
            .filter(Transcription.transcription_type == TranscriptionType.AUDIO_TO_TEXT)
            .count()
        )

        # Среднее время обработки
        avg_processing_time = (
            self.db.query(Transcription.processing_time)
            .filter(Transcription.status == "completed", Transcription.processing_time.isnot(None))
            .all()
        )

        avg_time = (
            sum([time[0] for time in avg_processing_time]) / len(avg_processing_time)
            if avg_processing_time
            else 0
        )

        return {
            "total_transcriptions": total_transcriptions,
            "successful_transcriptions": successful_transcriptions,
            "failed_transcriptions": failed_transcriptions,
            "success_rate": round((successful_transcriptions / total_transcriptions * 100), 2)
            if total_transcriptions > 0
            else 0,
            "avg_processing_time": round(avg_time, 2),
            "text_to_audio_count": text_to_audio_count,
            "audio_to_text_count": audio_to_text_count,
        }

    def get_users_list(self, limit: int = 50, offset: int = 0) -> list[User]:
        """Получение списка пользователей"""
        return (
            self.db.query(User).order_by(User.created_at.desc()).offset(offset).limit(limit).all()
        )

    def block_user(self, admin_telegram_id: int, target_user_id: int, reason: str = None) -> bool:
        """Блокировка пользователя"""
        # Проверка прав администратора
        if not self.is_admin(admin_telegram_id):
            return False

        # Поиск администратора
        admin = self.db.query(User).filter(User.telegram_id == admin_telegram_id).first()

        # Блокировка пользователя
        user = self.db.query(User).filter(User.telegram_id == target_user_id).first()
        if user:
            user.is_blocked = True

            # Логирование действия
            log = AdminLog(
                admin_id=admin.id,
                action="block_user",
                target_user_id=user.id,
                description=f"Заблокирован пользователь {user.get_full_name()}. Причина: {reason or 'Не указана'}",
            )
            self.db.add(log)
            self.db.commit()
            return True
        return False

    def unblock_user(
        self, admin_telegram_id: int, target_user_id: int, reason: str | None = None
    ) -> bool:
        """Разблокировка пользователя"""
        # Проверка прав администратора
        if not self.is_admin(admin_telegram_id):
            return False

        # Поиск администратора
        admin = self.db.query(User).filter(User.telegram_id == admin_telegram_id).first()

        # Разблокировка пользователя
        user = self.db.query(User).filter(User.telegram_id == target_user_id).first()
        if user:
            user.is_blocked = False

            # Логирование действия
            log = AdminLog(
                admin_id=admin.id,
                action="unblock_user",
                target_user_id=user.id,
                description=f"Разблокирован пользователь {user.get_full_name()}. Причина: {reason or 'Не указана'}",
            )
            self.db.add(log)
            self.db.commit()
            return True
        return False

    def get_user_info(self, user_id: int) -> User | None:
        """Получение информации о пользователе"""
        return self.db.query(User).filter(User.telegram_id == user_id).first()

    def get_user_transcriptions(self, user_id: int, limit: int = 10) -> list[Transcription]:
        """Получение транскрипций пользователя"""
        user = self.db.query(User).filter(User.telegram_id == user_id).first()
        if user:
            return (
                self.db.query(Transcription)
                .filter(Transcription.user_id == user.id)
                .order_by(Transcription.created_at.desc())
                .limit(limit)
                .all()
            )
        return []

    def get_admin_logs(self, limit: int = 50) -> list[AdminLog]:
        """Получение логов действий администраторов"""
        return self.db.query(AdminLog).order_by(AdminLog.created_at.desc()).limit(limit).all()

    def get_daily_statistics(self, days: int = 7) -> list[BotStatistics]:
        """Получение дневной статистики"""
        start_date = datetime.now(UTC) - timedelta(days=days)
        return (
            self.db.query(BotStatistics)
            .filter(BotStatistics.date >= start_date)
            .order_by(BotStatistics.date.desc())
            .all()
        )

    def update_user_activity(self, user_id: int):
        """Обновление времени последней активности пользователя"""
        user = self.db.query(User).filter(User.telegram_id == user_id).first()
        if user:
            user.last_activity = datetime.now(UTC)
            self.db.commit()

    def create_or_update_user(
        self,
        telegram_id: int,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> User:
        """Создание или обновление пользователя"""
        user = self.db.query(User).filter(User.telegram_id == telegram_id).first()

        if not user:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                role=UserRole.USER,
            )
            self.db.add(user)
        else:
            # Обновление данных существующего пользователя
            if username is not None:
                user.username = username
            if first_name is not None:
                user.first_name = first_name
            if last_name is not None:
                user.last_name = last_name

        # Обновляем время последней активности
        user.last_activity = datetime.now(UTC)
        self.db.commit()
        return user

    def log_transcription(
        self,
        user_id: int,
        status: str,
        transcription_type: TranscriptionType = TranscriptionType.TEXT_TO_AUDIO,
        processing_time: int = None,
        error_message: str = None,
        text_length: int = 0,
        input_text: str = None,
        input_audio_path: str = None,
        output_audio_path: str = None,
        audio_duration: float = None,
    ):
        """Логирование транскрипции"""
        user = self.db.query(User).filter(User.telegram_id == user_id).first()
        if user:
            transcription = Transcription(
                user_id=user.id,
                transcription_type=transcription_type,
                status=status,
                processing_time=processing_time,
                error_message=error_message,
                text_length=text_length,
                input_text=input_text,
                input_audio_path=input_audio_path,
                output_audio_path=output_audio_path,
                audio_duration=audio_duration,
            )
            self.db.add(transcription)
            self.db.commit()

    def log_text_to_audio_transcription(
        self,
        user_id: int,
        status: str,
        processing_time: int | None = None,
        error_message: str | None = None,
        text_length: int = 0,
        input_text: str | None = None,
        output_audio_path: str | None = None,
    ):
        """Логирование преобразования текста в аудио"""
        self.log_transcription(
            user_id=user_id,
            status=status,
            transcription_type=TranscriptionType.TEXT_TO_AUDIO,
            processing_time=processing_time,
            error_message=error_message,
            text_length=text_length,
            input_text=input_text,
            output_audio_path=output_audio_path,
        )

    def log_audio_to_text_transcription(
        self,
        user_id: int,
        status: str,
        processing_time: int | None = None,
        error_message: str | None = None,
        text_length: int = 0,
        input_audio_path: str | None = None,
        recognized_text: str | None = None,
        audio_duration: float | None = None,
    ):
        """Логирование преобразования аудио в текст"""
        self.log_transcription(
            user_id=user_id,
            status=status,
            transcription_type=TranscriptionType.AUDIO_TO_TEXT,
            processing_time=processing_time,
            error_message=error_message,
            text_length=text_length,
            input_audio_path=input_audio_path,
            input_text=recognized_text,
            audio_duration=audio_duration,
        )
