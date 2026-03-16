# 🤖 AI Transcriber - Telegram Bot

**Multi-service Telegram bot with Kafka-based architecture for AI-powered content processing**

## 📋 Описание проекта

AI Transcriber - это микросервисный Telegram-бот, использующий передовые AI технологии для обработки контента. Архитектура построена на Apache Kafka для асинхронного взаимодействия между сервисами.

### 🎯 Основные возможности

- 📸 **OCR** - Распознавание текста из изображений (Tesseract)
- 🎤 **Транскрибация** - Преобразование голоса в текст (Whisper)
- 🔊 **TTS** - Синтез речи из текста (gTTS)
- 🎨 **Генерация изображений** - Текст в изображение (Stable Diffusion XL / FLUX / SD 1.5)
  - Выбор модели: SD 1.5, SDXL, FLUX
  - Стили: Фотореализм, Аниме, Арт, 3D
  - Соотношения сторон: 1:1, 16:9, 9:16, 4:3
  - Количество вариаций: 1-4
  - Negative prompt
- ⚡ **Масштабируемость** - Независимое масштабирование сервисов
- 🌍 **Мультиязычность** - Поддержка русского, английского и других языков

## 🏗️ Архитектура

```
┌─────────────────────────────────────────────────────────────────────┐
│                         TELEGRAM BOT                                 │
│              (bot_service - производитель и потребитель задач)       │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          KAFKA CLUSTER                              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐  │
│  │ tasks.ocr  │ │tasks.trans- │ │ tasks.tts  │ │tasks.image │  │
│  │             │ │   cribe    │ │             │ │    _gen    │  │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘  │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐  │
│  │results.ocr  │ │results.tran│ │results.tts  │ │results.ima-│  │
│  │             │ │   scribe   │ │             │ │    ge_gen  │  │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
    │               │               │               │
    ▼               ▼               ▼               ▼
┌──────────┐  ┌──────────────┐  ┌──────────┐  ┌──────────────┐
│   OCR    │  │ TRANSCRIBE  │  │   TTS    │  │ IMAGE_GEN   │
│ Service  │  │  Service    │  │ Service  │  │  Service    │
│(Tesseract│  │ (Whisper)   │  │  (gTTS)  │  │(SD/FLUX)    │
└──────────┘  └──────────────┘  └──────────┘  └──────────────┘
                                    │
                                    ▼
                            ┌──────────────┐
                            │ PostgreSQL   │
                            │ (user_settings)│
                            └──────────────┘
```

### 📁 Структура проекта

```
├── services/                    # Микросервисы
│   ├── bot_service/             # Telegram бот
│   │   ├── main.py
│   │   ├── kafka_producer.py
│   │   ├── kafka_consumer.py
│   │   ├── settings_handlers.py
│   │   └── tests/
│   ├── ocr_service/             # OCR (Tesseract)
│   ├── transcription_service/   # Whisper
│   ├── tts_service/             # gTTS
│   ├── image_gen_service/       # Stable Diffusion / FLUX
│   │   ├── main.py
│   │   ├── processor.py        # Мультимодельная генерация
│   │   └── kafka_consumer.py
│   └── common/                  # Общие модули
│       ├── base_service.py      # Базовый класс сервиса
│       ├── schemas.py           # Kafka сообщения
│       ├── kafka_config.py      # Конфигурация
│       ├── database.py          # PostgreSQL подключение
│       ├── user_settings_repo.py # Настройки пользователей
│       ├── hardware.py          # GPU detection
│       └── exceptions.py
├── db/                          # Миграции Liquibase
│   ├── Dockerfile
│   └── changelog/
├── docker-compose.yml            # Orchestration
├── requirements.txt              # Python зависимости
└── .env.example                 # Пример конфигурации
```

## 🚀 Быстрый старт

### Предварительные требования

- Docker и Docker Compose
- Telegram бот токен (получить у @BotFather)

### Запуск

```bash
# 1. Клонируйте репозиторий
git clone <repository-url>
cd ai-transcriber-telegram-bot

# 2. Настройте переменные окружения
cp .env.example .env
# Отредактируйте .env файл

# 3. Запустите все сервисы
docker-compose up -d

# 4. Проверьте статус
docker-compose ps

# 5. Просмотр логов
docker-compose logs -f
```

### Остановка

```bash
docker-compose down
```

## ⚙️ Конфигурация

### Переменные окружения (.env)

```env
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_here
ADMIN_USERNAMES=admin1,admin2

# PostgreSQL Database
DB_NAME=ai_transcriber
DB_USER=bot
DB_PASSWORD=secret

# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka:29092

# GPU для генерации изображений (intel/nvidia/amd)
GPU_TYPE=intel

# Stable Diffusion модели
SDXL_MODEL_ID=stabilityai/stable-diffusion-xl-base-1.0
SD15_MODEL_ID=runwayml/stable-diffusion-v1-5
FLUX_MODEL_ID=black-forest-labs/FLUX.1-dev

# Whisper
WHISPER_MODEL=base
WHISPER_DEVICE=cpu

# TTS
TTS_LANGUAGE=ru
```

### GPU Конфигурация

| Тип GPU | Описание | Модели |
|----------|----------|--------|
| `intel` | Intel встройка/дискретная (по умолчанию) | SD 1.5, SDXL |
| `nvidia` | NVIDIA GPU (CUDA) | SD 1.5, SDXL, FLUX |
| `amd` | AMD GPU (ROCm) | SD 1.5, SDXL, FLUX |

### Kafka Topics

| Topic | Направление | Сервис |
|-------|-------------|--------|
| `tasks.ocr` | → | ocr_service |
| `tasks.transcribe` | → | transcription_service |
| `tasks.tts` | → | tts_service |
| `tasks.image_gen` | → | image_gen_service |
| `results.ocr` | → | bot_service |
| `results.transcribe` | → | bot_service |
| `results.tts` | → | bot_service |
| `results.image_gen` | → | bot_service |

## 🎮 Использование

### Команды бота

- `/start` - Запуск бота
- `/help` - Помощь
- `/mode` - Выбор режима работы
- `/settings` - Настройки генерации изображений
- `/status` - Статус сервисов

### Режимы работы

1. **📸 Изображение → Текст** - Отправьте фото для OCR
2. **🎤 Аудио → Текст** - Отправьте голосовое для транскрипции
3. **🔊 Текст → Аудио** - Напишите текст для TTS
4. **🖼️ Текст → Изображение** - Напишите текст для генерации

### Настройки генерации (/settings)

- 🎨 **Модель**: SD 1.5 / SDXL / FLUX
- 🎭 **Стиль**: Без / Фотореализм / Аниме / Арт / 3D
- 📐 **Размер**: 1:1 / 16:9 / 9:16 / 4:3
- 🔢 **Вариаций**: 1-4
- 📝 **Negative prompt**

## 🧪 Тестирование

```bash
# Установите зависимости
pip install -r requirements.txt

# Запустите тесты
pytest services/ -v
```

## 🛠️ Технологический стек

- **Python 3.12** - Основной язык
- **Apache Kafka** - Message broker
- **PostgreSQL** - База данных (настройки пользователей)
- **Liquibase** - Миграции БД
- **python-telegram-bot** - Telegram API
- **Tesseract OCR** - Распознавание текста
- **OpenAI Whisper** - Транскрибация
- **gTTS** - Синтез речи
- **Stable Diffusion XL / FLUX** - Генерация изображений
- **Docker** - Контейнеризация
- **Multi-stage builds** - Оптимизация образов

## 📄 Лицензия

MIT License
