import logging
from datetime import datetime

from sqlalchemy import Column, DateTime, Index, Integer, String, Text, create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session, sessionmaker

from .database import DATABASE_URL, Base

logger = logging.getLogger(__name__)


class TaskQueueItem(Base):
    __tablename__ = "task_queue"

    task_id = Column(String(255), primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    chat_id = Column(Integer, nullable=True, index=True)
    task_type = Column(String(50), nullable=False)
    status = Column(String(20), default="pending", index=True)
    priority = Column(Integer, default=0, index=True)
    prompt = Column(Text)
    task_metadata = Column(JSONB)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (Index("idx_task_queue_priority_priority", "priority"),)


def get_task_queue_session() -> Session:
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    return Session()


def add_task(
    task_id: str,
    user_id: int,
    task_type: str,
    prompt: str = None,
    metadata: dict = None,
    priority: int = 0,
    chat_id: int = None,
) -> bool:
    try:
        session = get_task_queue_session()
        task = TaskQueueItem(
            task_id=task_id,
            user_id=user_id,
            chat_id=chat_id,
            task_type=task_type,
            prompt=prompt,
            task_metadata=metadata,
            priority=priority,
            status="pending",
        )
        session.add(task)
        session.commit()
        session.close()
        logger.info(f"Task {task_id} added to queue")
        return True
    except Exception as e:
        logger.error(f"Failed to add task to queue: {e}")
        return False


def get_user_tasks(user_id: int, limit: int = 20) -> list[TaskQueueItem]:
    try:
        session = get_task_queue_session()
        tasks = (
            session.query(TaskQueueItem)
            .filter(TaskQueueItem.user_id == user_id)
            .order_by(TaskQueueItem.priority.desc(), TaskQueueItem.created_at.desc())
            .limit(limit)
            .all()
        )
        session.close()
        return tasks
    except Exception as e:
        logger.error(f"Failed to get user tasks: {e}")
        return []


def update_task_status(task_id: str, status: str) -> bool:
    try:
        session = get_task_queue_session()
        task = session.query(TaskQueueItem).filter(TaskQueueItem.task_id == task_id).first()
        if task:
            task.status = status
            task.updated_at = datetime.now()
            session.commit()
        session.close()
        return True
    except Exception as e:
        logger.error(f"Failed to update task status: {e}")
        return False


def cancel_task(task_id: str) -> bool:
    return update_task_status(task_id, "cancelled")


def update_task_priority(task_id: str, priority: int) -> bool:
    try:
        session = get_task_queue_session()
        task = session.query(TaskQueueItem).filter(TaskQueueItem.task_id == task_id).first()
        if task:
            task.priority = priority
            task.updated_at = datetime.now()
            session.commit()
        session.close()
        return True
    except Exception as e:
        logger.error(f"Failed to update task priority: {e}")
        return False


def get_pending_tasks(limit: int = 50) -> list[TaskQueueItem]:
    try:
        session = get_task_queue_session()
        tasks = (
            session.query(TaskQueueItem)
            .filter(TaskQueueItem.status == "pending")
            .order_by(TaskQueueItem.priority.desc(), TaskQueueItem.created_at.asc())
            .limit(limit)
            .all()
        )
        session.close()
        return tasks
    except Exception as e:
        logger.error(f"Failed to get pending tasks: {e}")
        return []


def get_pending_tasks_by_chat_id(chat_id: int) -> list[TaskQueueItem]:
    try:
        session = get_task_queue_session()
        tasks = (
            session.query(TaskQueueItem)
            .filter(TaskQueueItem.chat_id == chat_id, TaskQueueItem.status == "pending")
            .all()
        )
        session.close()
        return tasks
    except Exception as e:
        logger.error(f"Failed to get pending tasks by chat_id: {e}")
        return []


def delete_task(task_id: str) -> bool:
    try:
        session = get_task_queue_session()
        task = session.query(TaskQueueItem).filter(TaskQueueItem.task_id == task_id).first()
        if task:
            session.delete(task)
            session.commit()
            session.close()
            logger.info(f"Task {task_id} deleted from queue")
            return True
        session.close()
        return False
    except Exception as e:
        logger.error(f"Failed to delete task: {e}")
        return False
