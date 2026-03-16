import logging
from typing import List, Optional
from datetime import datetime

from sqlalchemy import Column, String, Integer, Text, DateTime, Index, create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import sessionmaker, Session

from .database import get_database_url

logger = logging.getLogger(__name__)

Base = None


def get_base():
    global Base
    if Base is None:
        from sqlalchemy.ext.declarative import declarative_base
        Base = declarative_base()
    return Base


class TaskQueueItem(get_base()):
    __tablename__ = 'task_queue'
    
    task_id = Column(String(255), primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    task_type = Column(String(50), nullable=False)
    status = Column(String(20), default='pending', index=True)
    priority = Column(Integer, default=0, index=True)
    prompt = Column(Text)
    metadata = Column(JSONB)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    __table_args__ = (
        Index('idx_task_queue_priority', 'priority', desc=True),
    )


def get_task_queue_session() -> Session:
    engine = create_engine(get_database_url())
    Session = sessionmaker(bind=engine)
    return Session()


def add_task(task_id: str, user_id: int, task_type: str, prompt: str = None, 
             metadata: dict = None, priority: int = 0) -> bool:
    try:
        session = get_task_queue_session()
        task = TaskQueueItem(
            task_id=task_id,
            user_id=user_id,
            task_type=task_type,
            prompt=prompt,
            metadata=metadata,
            priority=priority,
            status='pending'
        )
        session.add(task)
        session.commit()
        session.close()
        logger.info(f"Task {task_id} added to queue")
        return True
    except Exception as e:
        logger.error(f"Failed to add task to queue: {e}")
        return False


def get_user_tasks(user_id: int, limit: int = 20) -> List[TaskQueueItem]:
    try:
        session = get_task_queue_session()
        tasks = session.query(TaskQueueItem).filter(
            TaskQueueItem.user_id == user_id
        ).order_by(TaskQueueItem.priority.desc(), TaskQueueItem.created_at.desc()).limit(limit).all()
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
    return update_task_status(task_id, 'cancelled')


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


def get_pending_tasks(limit: int = 50) -> List[TaskQueueItem]:
    try:
        session = get_task_queue_session()
        tasks = session.query(TaskQueueItem).filter(
            TaskQueueItem.status == 'pending'
        ).order_by(TaskQueueItem.priority.desc(), TaskQueueItem.created_at.asc()).limit(limit).all()
        session.close()
        return tasks
    except Exception as e:
        logger.error(f"Failed to get pending tasks: {e}")
        return []
