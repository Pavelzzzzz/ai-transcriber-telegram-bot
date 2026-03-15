from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
import json
import uuid


class TaskType(str, Enum):
    OCR = "ocr"
    TRANSCRIBE = "transcribe"
    IMAGE_GEN = "image_gen"


class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class TaskMessage:
    task_id: str
    task_type: TaskType
    user_id: int
    chat_id: int
    timestamp: datetime
    file_path: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.task_id:
            self.task_id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = datetime.now()
    
    def to_json(self) -> str:
        data = asdict(self)
        data['task_type'] = self.task_type.value
        data['timestamp'] = self.timestamp.isoformat()
        return json.dumps(data, ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'TaskMessage':
        data = json.loads(json_str)
        data['task_type'] = TaskType(data['task_type'])
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


@dataclass
class ResultMessage:
    task_id: str
    status: TaskStatus
    result_type: str
    result_data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_json(self) -> str:
        data = asdict(self)
        data['status'] = self.status.value
        data['timestamp'] = self.timestamp.isoformat()
        return json.dumps(data, ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ResultMessage':
        data = json.loads(json_str)
        data['status'] = TaskStatus(data['status'])
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)
