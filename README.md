# 🤖 AI Transcriber - Telegram Bot

**Multi-service Telegram bot with Kafka-based architecture for AI-powered content processing**

## 📋 Описание проекта

AI Transcriber - это микросервисный Telegram-бот, использующий передовые AI технологии для обработки контента. Архитектура построена на Apache Kafka для асинхронного взаимодействия между сервисами.

### 🎯 Основные возможности

- 📸 **OCR ( распознавание текста)** - Извлечение текста из изображений через Tesseract
- 🎤 **Транскрибация** - Преобразование голосовых сообщений в текст через Whisper
- 🔊 **Синтез речи (TTS)** - Преобразование текста в аудио через gTTS
- 🎨 **Генерация изображений** - Создание изображений из текста через Stable Diffusion XL
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
│(Tesseract│  │ (Whisper)   │  │  (gTTS)  │  │(Stable Diff │
│  local)  │  │   local)    │  │  local)  │  │    XL)      │
└──────────┘  └──────────────┘  └──────────┘  └──────────────┘
```

### 📁 Структура проекта

```
├── services/                    # Микросервисы
│   ├── bot_service/             # Telegram бот + Kafka
│   │   ├── main.py
│   │   ├── kafka_producer.py
│   │   ├── kafka_consumer.py
│   │   ├── Dockerfile
│   │   └── tests/
│   ├── ocr_service/            # OCR (Tesseract)
│   │   ├── main.py
│   │   ├── processor.py
│   │   ├── kafka_consumer.py
│   │   ├── Dockerfile
│   │   └── tests/
│   ├── transcription_service/   # Whisper
│   │   ├── main.py
│   │   ├── processor.py
│   │   ├── kafka_consumer.py
│   │   ├── Dockerfile
│   │   └── tests/
│   ├── tts_service/            # gTTS
│   │   ├── main.py
│   │   ├── processor.py
│   │   ├── kafka_consumer.py
│   │   ├── Dockerfile
│   │   └── tests/
│   ├── image_gen_service/      # Stable Diffusion XL
│   │   ├── main.py
│   │   ├── processor.py
│   │   ├── kafka_consumer.py
│   │   ├── Dockerfile
│   │   └── tests/
│   └── common/                 # Общие модули
│       ├── schemas.py          # Kafka сообщения
│       ├── kafka_config.py     # Конфигурация
│       └── exceptions.py       # Исключения
├── config/                     # Конфигурация
├── utils/                      # Утилиты
├── database/                   # База данных
├── docker-compose.yml          # Docker Compose
├── requirements.txt            # Зависимости
└── .env.example              # Пример окружения
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

### Переменные окружения

```env
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_here
ADMIN_USERNAMES=admin1,admin2

# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka:29092

# Whisper (транскрибация)
WHISPER_MODEL=base
WHISPER_DEVICE=cpu

# TTS
TTS_LANGUAGE=ru

# Stable Diffusion XL
SDXL_MODEL_ID=stabilityai/stable-diffusion-xl-base-1.0
```

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
- `/status` - Статус сервисов

### Отправка контента

1. **Фото** → Бот распознает текст (OCR)
2. **Голосовое** → Бот транскрибирует речь
3. **Текст** → Бот синтезирует речь (TTS)
4. **Текст с командой /generate** → Бот сгенерирует изображение

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
- **python-telegram-bot** - Telegram API
- **Tesseract OCR** - Распознавание текста
- **OpenAI Whisper** - Транскрибация
- **gTTS** - Синтез речи
- **Stable Diffusion XL** - Генерация изображений
- **Docker** - Контейнеризация

## 📄 Лицензия

MIT License
