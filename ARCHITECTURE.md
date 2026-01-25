# 🏗️ Архитектура проекта (v2.0)

## 📋 Обзор архитектуры

После полного рефакторинга проект имеет чистую модульную архитектуру с разделением ответственности.

### 🎯 Принципы архитектуры

1. **Single Responsibility** - Каждый модуль имеет одну задачу
2. **Type Safety** - Full типизация с Pydantic и SQLAlchemy
3. **Separation of Concerns** - Четкое разделение на слои
4. **Dependency Injection** - Внедрение зависимостей через конструкторы
5. **Error Handling** - Структурированная обработка исключений

## 🏛️ Структура модулей

```
📦 AI Transcriber Bot Architecture
├── 📂 config/                    # 🔧 Конфигурация
│   ├── __init__.py
│   └── settings.py              # Type-safe конфигурация
│
├── 📂 src/                      # 🚀 Основной код
│   ├── 📂 core/                  # ⚡ Ядро системы
│   │   ├── __init__.py
│   │   ├── bot_core.py          # 🤖 Основной класс бота
│   │   ├── handlers.py           # 📱 Обработчики команд
│   │   ├── admin_handlers.py     # 🔐 Администрирование
│   │   ├── exceptions.py         # ⚠️ Типизированные исключения
│   │   └── user_manager.py      # 👥 Управление пользователями
│   │
│   ├── 📂 services/              # 💼 Бизнес-логика
│   │   ├── __init__.py
│   │   └── user_service.py      # 📊 Сервис пользователей
│   │
│   └── 📂 bot.py                # 🔄 Simple fallback бот
│
├── 📂 utils/                    # 🛠️ Утилиты
│   ├── __init__.py
│   ├── whisper_transcriber.py   # 🎤 Whisper AI
│   ├── image_processor.py       # 📸 OCR обработка
│   └── multilingual_processor.py # 🌍 Мультиязычность
│
├── 📂 database/                 # 🗄️ База данных
│   ├── __init__.py
│   └── models.py               # 📋 SQLAlchemy модели
│
├── 📂 tests/                    # 🧪 Тесты
├── 📄 main_simple.py            # 🚀 Рабочая точка входа
├── 📄 main.py                   # 📝 Полная точка входа
└── 📄 requirements.txt           # 📦 Зависимости
```

## 🔧 Компоненты архитектуры

### 📂 config/ - Конфигурация

#### settings.py
```python
@dataclass(frozen=True)
class BotConfig:
    """Type-safe конфигурация бота"""
    security: SecurityConfig
    ai: AIConfig
    logging: LoggingConfig
    
    def validate(self) -> List[str]:
        """Валидация конфигурации с детальными ошибками"""
```

**Особенности:**
- ✅ Type-safe с Pydantic
- ✅ Валидация при старте
- ✅ Environment variables
- ✅ Nested конфигурация

### 📂 src/core/ - Ядро системы

#### bot_core.py
```python
class BotCore:
    """Основной класс бота с dependency injection"""
    
    def __init__(self):
        self.config = config
        self.user_manager = UserManager(self.config)
        self.command_handlers = CommandHandlers(self.config, self.user_manager)
        # ... другие компоненты
```

**Ответственность:**
- 🤖 Оркестрация всех компонентов
- 🔄 Жизненный цикл бота
- 📡 Telegram API интеграция
- ⚠️ Глобальная обработка ошибок

#### handlers.py
```python
class CommandHandlers:
    """Обработчики команд пользователей"""
    
    def __init__(self, config: BotConfig, user_service: UserService):
        self.config = config
        self.user_service = user_service
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /start"""
```

**Ответственность:**
- 📱 Команды пользователей (/start, /help, /mode)
- 🔍 Валидация входных данных
- 📊 Форматирование ответов
- 🛡️ Проверка прав доступа

#### exceptions.py
```python
class BotError(Exception):
    """Базовое исключение бота с контекстом"""
    
    def __init__(self, message: str, *, is_critical: bool = False, user_id: Optional[int] = None):
        self.message = message
        self.is_critical = is_critical
        self.user_id = user_id
        super().__init__(message)

class DatabaseError(BotError):
    """Ошибка базы данных"""
    def __init__(self, message: str, *, operation: str, **kwargs):
        super().__init__(message, **kwargs)
        self.operation = operation
```

**Особенности:**
- 🏷️ Структурированные исключения
- 📊 Контекст ошибки (user_id, operation)
- 🔄 Уровень критичности
- 📝 Логирование с контекстом

### 📂 src/services/ - Бизнес-логика

#### user_service.py
```python
class UserService:
    """Сервис управления пользователями и статистикой"""
    
    def __init__(self, config: BotConfig):
        self.config = config
    
    async def get_or_create_user(self, telegram_id: int, **kwargs) -> User:
        """Получить или создать пользователя с обработкой ошибок"""
        
    async def get_global_stats(self) -> Dict[str, Any]:
        """Получить глобальную статистику бота"""
```

**Ответственность:**
- 👥 Управление пользователями
- 📊 Статистика и аналитика
- 🗄️ Работа с базой данных
- 🔧 Бизнес-правила

### 📂 utils/ - Утилиты

#### whisper_transcriber.py
```python
class WhisperTranscriber:
    """Интеграция с OpenAI Whisper"""
    
    def __init__(self, model: str = "base", device: str = "cpu"):
        self.model = whisper.load_model(model, device=device)
    
    async def transcribe_audio(self, audio_path: str) -> Dict[str, Any]:
        """Транскрибировать аудио в текст"""
```

#### image_processor.py
```python
class ImageProcessor:
    """Обработка изображений и OCR"""
    
    async def extract_text_from_image(self, image_path: str) -> str:
        """Извлечь текст из изображения"""
```

## 🔄 Потоки данных

### 🚀 Запуск бота
```
main_simple.py
    ↓
setup_logging()
    ↓
BotCore.__init__()
    ↓
CommandHandlers.__init__()
    ↓
UserService.__init__()
    ↓
Application.builder().build()
    ↓
application.run_polling()
```

### 📱 Обработка команды
```
Telegram API
    ↓
BotCore._setup_handlers()
    ↓
CommandHandlers.command_method()
    ↓
UserService.business_method()
    ↓
Database (SQLAlchemy)
    ↓
Response to Telegram
```

### ⚠️ Обработка ошибок
```
Exception occurs
    ↓
try/except block
    ↓
BotError (structured)
    ↓
logger.error() with context
    ↓
Error message to user
    ↓
Continue operation (if not critical)
```

## 🛡️ Безопасность

### 🔐 Аутентификация и авторизация

```python
def _is_admin(self, user_id: int, username: Optional[str] = None) -> bool:
    """Проверка прав администратора"""
    if username and username.lower() in self.config.security.admin_usernames:
        return True
    if user_id in self.config.security.admin_ids:
        return True
    return False
```

### 🚦 Rate limiting (запланировано)

```python
class RateLimiter:
    """Ограничитель частоты запросов"""
    
    async def check_limit(self, user_id: int) -> bool:
        """Проверить лимит запросов"""
```

## 📊 Мониторинг и логирование

### 📝 Структурированное логирование

```python
logger.info(
    "User action completed",
    extra={
        "user_id": user_id,
        "action": "transcription_completed",
        "duration": processing_time,
        "file_type": "audio"
    }
)
```

### 📈 Статистика в реальном времени

```python
async def get_global_stats(self) -> Dict[str, Any]:
    """Статистика с кэшированием"""
    # Базовые метрики
    total_users = session.execute(select(func.count(User.id))).scalar() or 0
    # ... другая статистика
```

## 🧪 Тестирование

### 🏗️ Архитектура тестов

```
tests/
├── unit/                          # 🧪 Юнит-тесты
│   ├── test_bot_core.py
│   ├── test_user_service.py
│   └── test_handlers.py
├── integration/                   # 🔗 Интеграционные тесты
│   ├── test_full_flow.py
│   └── test_database.py
├── e2e/                          # 🎯 End-to-end тесты
│   └── test_bot_scenarios.py
└── conftest.py                   # 🛠️ Конфигурация pytest
```

### 🎯 Пример теста

```python
async def test_start_command_handler():
    """Тест команды /start"""
    # Arrange
    update = MockUpdate()
    context = MockContext()
    handlers = CommandHandlers(config, user_service)
    
    # Act
    await handlers.start_command(update, context)
    
    # Assert
    update.message.reply_text.assert_called_once()
    assert "🚀 AI Транскрибатор" in call_args[0]
```

## 🚀 Развертывание

### 🐳 Docker архитектура

```dockerfile
# Multi-stage build
FROM python:3.11-slim as builder
# ... установка зависимостей

FROM python:3.11-slim as runtime
# ... копирование артефактов
USER app
CMD ["python", "-u", "main_simple.py"]
```

### 🌐 Production настройки

```yaml
# docker-compose.prod.yml
services:
  telegram-bot:
    image: ai-transcriber-bot:latest
    restart: unless-stopped
    environment:
      - LOG_LEVEL=WARNING
      - WHISPER_MODEL=base
    volumes:
      - ./logs:/app/logs
      - ./downloads:/app/downloads
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
```

## 🔄 Взаимодействие компонентов

### 📱 Sequence Diagram

```
User → Telegram API → BotCore → CommandHandlers → UserService → Database
                                   ↓
Response ← Telegram ← BotCore ← CommandHandlers ← UserService ← Database
```

### 🎯 Component Dependencies

```python
BotCore
├── CommandHandlers (depends on UserService)
├── MediaHandlers (depends on UserService)
├── AdminHandlers (depends on UserService)
├── CallbackHandlers (depends on UserService)
└── UserManager (depends on Database)

UserService
├── Database (SQLAlchemy)
├── Config (Pydantic)
└── Utils (Whisper, OCR)
```

## 🎯 Принципы SOLID

### S - Single Responsibility
Каждый класс имеет одну причину для изменения:
- `BotCore` - оркестрация
- `UserService` - бизнес-логика пользователей
- `CommandHandlers` - обработка команд

### O - Open/Closed
Классы открыты для расширения, закрыты для изменения:
- `CommandHandlers` можно расширять новыми командами
- `UserService` можно наследовать для другой БД

### L - Liskov Substitution
Подклассы заменяют базовые классы:
- `DatabaseError` → `BotError`
- `WhisperTranscriber` → `BaseTranscriber`

### I - Interface Segregation
Маленькие, специфичные интерфейсы:
- Команды разделены на `CommandHandlers`, `AdminHandlers`
- Сервисы разделены по ответственности

### D - Dependency Inversion
Зависимости от абстракций:
- `BotCore` зависит от `UserService` (интерфейс)
- Конфигурация через Pydantic dataclasses

## 🚀 Performance оптимизации

### ⚡ Асинхронность

```python
# Правильно - асинхронные операции
async def process_voice(self, update: Update):
    audio_data = await self.download_file(update.message.voice)
    transcription = await self.whisper.transcribe(audio_data)
    await self.reply_text(transcription)

# Неправильно - блокирующие операции
def process_voice_blocking(self, update: Update):
    audio_data = self.download_file_sync(update.message.voice)  # Блокирует!
```

### 🗄️ Оптимизация базы данных

```python
# Правильно - сессия с контекстом
async def get_user_stats(self, user_id: int):
    with self.get_db_session() as session:
        return session.execute(select(User).where(User.id == user_id)).scalar_one()

# Неправильно - утечка сессий
async def get_user_stats_wrong(self, user_id: int):
    session = self.create_session()  # Утечка!
    # ... операции без close()
```

---

Эта архитектура обеспечивает:
- 🏗️ **Масштабируемость** - Легко добавлять новые функции
- 🛡️ **Безопасность** - Type-safe и обработка ошибок  
- 🧪 **Тестируемость** - Чистое разделение зависимостей
- 🚀 **Производительность** - Асинхронность и оптимизация
- 🔧 **Поддерживаемость** - Читаемый и документированный код