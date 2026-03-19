import logging
from typing import Any

from sqlalchemy import BigInteger, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from .database import Base, get_db

logger = logging.getLogger(__name__)


class UserSettings(Base):
    __tablename__ = "user_settings"

    user_id = Column(BigInteger, primary_key=True)
    image_model = Column(String(20), default="sdxl")
    image_style = Column(String(30), nullable=True)
    aspect_ratio = Column(String(10), default="1:1")
    num_variations = Column(Integer, default=1)
    negative_prompt = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "image_model": self.image_model,
            "image_style": self.image_style,
            "aspect_ratio": self.aspect_ratio,
            "num_variations": self.num_variations,
            "negative_prompt": self.negative_prompt,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ImageGenerationHistory(Base):
    __tablename__ = "image_generation_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    prompt = Column(Text, nullable=False)
    model = Column(String(20), nullable=False)
    style = Column(String(30), nullable=True)
    aspect_ratio = Column(String(10), nullable=True)
    file_path = Column(String(500), nullable=True)
    status = Column(String(20), default="success")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


def get_user_settings(user_id: int) -> UserSettings | None:
    try:
        with get_db() as db:
            return db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
    except Exception as e:
        logger.error(f"Error getting user settings: {e}")
        return None


def get_or_create_user_settings(user_id: int) -> UserSettings:
    try:
        with get_db() as db:
            settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
            if not settings:
                settings = UserSettings(user_id=user_id)
                db.add(settings)
                db.commit()
                db.refresh(settings)
            return settings
    except Exception as e:
        logger.error(f"Error getting/creating user settings: {e}")
        return UserSettings(user_id=user_id)


def update_user_settings(user_id: int, **kwargs) -> UserSettings | None:
    valid_fields = [
        "image_model",
        "image_style",
        "aspect_ratio",
        "num_variations",
        "negative_prompt",
    ]
    update_data = {k: v for k, v in kwargs.items() if k in valid_fields}

    if not update_data:
        return get_user_settings(user_id)

    try:
        with get_db() as db:
            settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
            if not settings:
                settings = UserSettings(user_id=user_id, **update_data)
                db.add(settings)
            else:
                for key, value in update_data.items():
                    setattr(settings, key, value)
            db.commit()
            db.refresh(settings)
            return settings
    except Exception as e:
        logger.error(f"Error updating user settings: {e}")
        return None


def reset_user_settings(user_id: int) -> bool:
    try:
        with get_db() as db:
            settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
            if settings:
                settings.image_model = "sdxl"
                settings.image_style = None
                settings.aspect_ratio = "1:1"
                settings.num_variations = 1
                settings.negative_prompt = None
                db.commit()
            return True
    except Exception as e:
        logger.error(f"Error resetting user settings: {e}")
        return False


def add_image_generation_history(
    user_id: int,
    prompt: str,
    model: str,
    style: str | None = None,
    aspect_ratio: str | None = None,
    file_path: str | None = None,
    status: str = "success",
    error_message: str | None = None,
) -> ImageGenerationHistory | None:
    try:
        with get_db() as db:
            history = ImageGenerationHistory(
                user_id=user_id,
                prompt=prompt,
                model=model,
                style=style,
                aspect_ratio=aspect_ratio,
                file_path=file_path,
                status=status,
                error_message=error_message,
            )
            db.add(history)
            db.commit()
            db.refresh(history)
            return history
    except Exception as e:
        logger.error(f"Error adding image generation history: {e}")
        return None


def get_user_image_history(user_id: int, limit: int = 10) -> list:
    try:
        with get_db() as db:
            return (
                db.query(ImageGenerationHistory)
                .filter(ImageGenerationHistory.user_id == user_id)
                .order_by(ImageGenerationHistory.created_at.desc())
                .limit(limit)
                .all()
            )
    except Exception as e:
        logger.error(f"Error getting user image history: {e}")
        return []
