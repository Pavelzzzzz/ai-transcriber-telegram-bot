"""
Configuration management for AI Transcriber Bot
"""

import os
from typing import List, Optional
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class DatabaseConfig:
    """Database configuration"""
    url: str = field(default_factory=lambda: os.getenv('DATABASE_URL', 'sqlite:///./bot.db'))
    echo: bool = field(default_factory=lambda: os.getenv('DB_ECHO', 'false').lower() == 'true')
    pool_size: int = field(default_factory=lambda: int(os.getenv('DB_POOL_SIZE', '10')))
    max_overflow: int = field(default_factory=lambda: int(os.getenv('DB_MAX_OVERFLOW', '20')))


@dataclass
class AIModelsConfig:
    """AI models configuration"""
    whisper_model: str = field(default_factory=lambda: os.getenv('WHISPER_MODEL', 'tiny'))
    whisper_device: str = field(default_factory=lambda: os.getenv('WHISPER_DEVICE', 'cpu'))
    ocr_languages: List[str] = field(default_factory=lambda: 
        os.getenv('OCR_LANGUAGES', 'rus,eng').split(',') if os.getenv('OCR_LANGUAGES') else ['rus', 'eng']
    )
    tts_language: str = field(default_factory=lambda: os.getenv('TTS_LANGUAGE', 'ru'))


@dataclass
class SecurityConfig:
    """Security configuration"""
    telegram_token: str = field(default_factory=lambda: os.getenv('TELEGRAM_BOT_TOKEN', ''))
    admin_usernames: List[str] = field(default_factory=lambda: 
        [name.strip() for name in os.getenv('ADMIN_USERNAMES', '').split(',') if name.strip()]
    )
    admin_ids: List[int] = field(default_factory=lambda: 
        [int(id_) for id_ in os.getenv('ADMIN_IDS', '').split(',') if id_.strip().isdigit()]
    )
    max_file_size_mb: int = field(default_factory=lambda: int(os.getenv('MAX_FILE_SIZE_MB', '20')))
    rate_limit_per_minute: int = field(default_factory=lambda: int(os.getenv('RATE_LIMIT_PER_MINUTE', '10')))
    rate_limit_per_hour: int = field(default_factory=lambda: int(os.getenv('RATE_LIMIT_PER_HOUR', '1000')))


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = field(default_factory=lambda: os.getenv('LOG_LEVEL', 'INFO'))
    format: str = field(default_factory=lambda: os.getenv(
        'LOG_FORMAT', 
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    file_path: Optional[str] = field(default_factory=lambda: os.getenv('LOG_FILE_PATH'))
    max_file_size: int = field(default_factory=lambda: int(os.getenv('LOG_MAX_FILE_SIZE', '10485760')))  # 10MB
    backup_count: int = field(default_factory=lambda: int(os.getenv('LOG_BACKUP_COUNT', '5')))


@dataclass
class PerformanceConfig:
    """Performance configuration"""
    worker_threads: int = field(default_factory=lambda: int(os.getenv('WORKER_THREADS', '4')))
    cache_ttl: int = field(default_factory=lambda: int(os.getenv('CACHE_TTL', '3600')))  # 1 hour
    max_concurrent_requests: int = field(default_factory=lambda: int(os.getenv('MAX_CONCURRENT_REQUESTS', '100')))
    request_timeout: int = field(default_factory=lambda: int(os.getenv('REQUEST_TIMEOUT', '30')))  # seconds


@dataclass
class PathConfig:
    """Path configuration"""
    base_dir: Path = field(default_factory=lambda: Path.cwd())
    downloads_dir: Path = field(default_factory=lambda: Path(os.getenv('DOWNLOADS_DIR', './downloads')))
    logs_dir: Path = field(default_factory=lambda: Path(os.getenv('LOGS_DIR', './logs')))
    temp_dir: Path = field(default_factory=lambda: Path(os.getenv('TEMP_DIR', './temp')))
    
    def __post_init__(self):
        """Ensure all paths are absolute and directories exist"""
        self.base_dir = Path(self.base_dir).resolve()
        self.downloads_dir = self.base_dir / self.downloads_dir.relative_to(self.base_dir) if not self.downloads_dir.is_absolute() else self.downloads_dir
        self.logs_dir = self.base_dir / self.logs_dir.relative_to(self.base_dir) if not self.logs_dir.is_absolute() else self.logs_dir
        self.temp_dir = self.base_dir / self.temp_dir.relative_to(self.base_dir) if not self.temp_dir.is_absolute() else self.temp_dir
        
        # Create directories if they don't exist
        for dir_path in [self.downloads_dir, self.logs_dir, self.temp_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)


@dataclass
class BotConfig:
    """Main bot configuration"""
    name: str = field(default='AI Transcriber Bot')
    version: str = field(default='2.0.0')
    description: str = field(default='AI-powered Telegram bot for text transcription and processing')
    
    # Sub-configurations
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    ai_models: AIModelsConfig = field(default_factory=AIModelsConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    paths: PathConfig = field(default_factory=PathConfig)
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []
        
        # Validate security
        if not self.security.telegram_token:
            errors.append("TELEGRAM_BOT_TOKEN is required")
        
        if not self.security.admin_usernames and not self.security.admin_ids:
            errors.append("At least one admin (ADMIN_USERNAMES or ADMIN_IDS) is required")
        
        # Validate paths
        if not self.paths.base_dir.exists():
            errors.append(f"Base directory does not exist: {self.paths.base_dir}")
        
        # Validate performance
        if self.performance.worker_threads < 1:
            errors.append("WORKER_THREADS must be at least 1")
        
        if self.security.max_file_size_mb < 1:
            errors.append("MAX_FILE_SIZE_MB must be at least 1")
        
        return errors
    
    @classmethod
    def from_env(cls) -> 'BotConfig':
        """Create configuration from environment variables"""
        return cls()


# Global configuration instance
config = BotConfig.from_env()