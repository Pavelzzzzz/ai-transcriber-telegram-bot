# 🤖 AI Transcriber - Telegram Bot

**Multi-service Telegram bot with Kafka-based architecture for AI-powered content processing**

## 📋 Описание проекта

AI Transcriber - это микросервисный Telegram-бот, использующий передовые AI технологии для обработки контента. Архитектура построена на Apache Kafka для асинхронного взаимодействия между сервисами.

### 🎯 Основные возможности

- 📸 **OCR** - Распознавание текста из изображений (RapidOCR с ONNX Runtime)
  - Поддержка GPU (NVIDIA, AMD)
  - Автоматическое препроцессирование изображений ( grayscale, контраст, шумоподавление)
  - Ленивая инициализация для быстрого старта
- 🎤 **Транскрибация** - Преобразование голоса в текст (Whisper)
  - Модель small по умолчанию
  - Подавление шума с ffmpeg
  - Параметры beam_size=5, best_of=5
- 🔊 **TTS** - Синтез речи из текста (gTTS)
- 🎨 **Генерация изображений** - Текст в изображение (Stable Diffusion XL / FLUX / SD 1.5)
  - Выбор модели: SD 1.5, SDXL, FLUX
  - Стили с автоподстановкой negative prompt: Фотореализм, Аниме, Арт, 3D
  - Соотношения сторон: 1:1, 16:9, 9:16, 4:3, 3:2, 2:3
  - Количество вариаций: 1-4
  - Negative prompt
- 🧾 **Товарные чеки WB** - Генерация товарных чеков для Wildberries (РБ)
  - Ввод товаров по артикулам или ссылкам WB
  - Редактирование названий товаров в предпросмотре
  - Генерация PDF в формате товарного чека РБ
  - Сохранение истории чеков
  - Асинхронная обработка через Kafka
- ⚡ **Масштабируемость** - Независимое масштабирование сервисов
- 🌍 **Мультиязычность** - Поддержка русского, английского и других языков
- 🔔 **Уведомления** - Kafka topic для push-уведомлений пользователям

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
│  │ tasks.ocr   │ │tasks.trans- │ │ tasks.tts   │ │tasks.image  │  │
│  │             │ │   cribe     │ │             │ │    _gen     │  │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘  │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐  │
│  │tasks.receipt│ │             │ │             │ │             │  │
│  └─────────────┘ │results.ocr  │ │results.tts  │ │results.ima- │  │
│  ┌─────────────┐ │             │ │             │ │    ge_gen   │  │
│  │results.re-  │ │results.tran│ │             │ │             │  │
│  │   ceipt     │ │   scribe   │ │             │ │             │  │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘  │
│                               ┌─────────────┐                       │
│                               │ notifications │                      │
│                               │  (push/email)  │                      │
│                               └─────────────┘                       │
└─────────────────────────────────────────────────────────────────────┘
    │               │               │               │               │
    ▼               ▼               ▼               ▼               ▼
┌──────────┐  ┌──────────────┐  ┌──────────┐  ┌──────────────┐  ┌──────────┐
│   OCR    │  │ TRANSCRIBE  │  │   TTS    │  │ IMAGE_GEN   │  │ RECEIPT  │
│ Service  │  │  Service    │  │ Service  │  │  Service    │  │ Service  │
│(RapidOCR)│  │ (Whisper)   │  │  (gTTS)  │  │(SD/FLUX)    │  │ (PDF)    │
└──────────┘  └──────────────┘  └──────────┘  └──────────────┘  └──────────┘
                                    │
                                    ▼
                            ┌──────────────┐
                            │ PostgreSQL   │
                            │ (user_settings, receipt_history)│
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
│   │   ├── receipt_handlers.py  # Обработчики товарных чеков
│   │   └── tests/
│   ├── ocr_service/             # OCR (RapidOCR)
│   ├── transcription_service/   # Whisper
│   ├── tts_service/             # gTTS
│   ├── image_gen_service/       # Stable Diffusion / FLUX
│   │   ├── main.py
│   │   ├── processor.py        # Мультимодельная генерация
│   │   └── kafka_consumer.py
│   ├── receipt_service/          # Товарные чеки WB
│   │   ├── main.py
│   │   ├── processor.py         # Логика обработки (JSON вход)
│   │   ├── receipt_generator.py # Генерация PDF
│   │   └── kafka_consumer.py
│   └── common/                  # Общие модули
│       ├── base_service.py      # Базовый класс сервиса
│       ├── schemas.py           # Kafka сообщения
│       ├── kafka_config.py      # Конфигурация
│       ├── database.py          # PostgreSQL подключение
│       ├── user_settings_repo.py # Настройки пользователей
│       ├── hardware.py          # GPU detection
│       └── exceptions.py
├── db/                          # Миграции (init.sh)
│   ├── Dockerfile
│   └── init.sh
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
| `cpu` | CPU only | SD 1.5 |

### OCR GPU Конфигурация

| Тип | Описание |
|------|----------|
| `nvidia` | NVIDIA GPU (CUDA) - включено |
| `amd` | AMD GPU (ROCm) - включено |
| `intel` | Intel GPU - не поддерживается |
| `cpu` | CPU only (по умолчанию) |

### Kafka Topics

| Topic | Направление | Сервис |
|-------|-------------|--------|
| `tasks.ocr` | → | ocr_service |
| `tasks.transcribe` | → | transcription_service |
| `tasks.tts` | → | tts_service |
| `tasks.image_gen` | → | image_gen_service |
| `tasks.receipt` | → | receipt_service |
| `results.ocr` | → | bot_service |
| `results.transcribe` | → | bot_service |
| `results.tts` | → | bot_service |
| `results.image_gen` | → | bot_service |
| `results_receipt` | → | bot_service |
| `notifications` | → | bot_service |

## 🎮 Использование

### Команды бота

- `/start` - Запуск бота
- `/help` - Помощь
- `/mode` - Выбор режима работы
- `/settings` - Настройки генерации изображений
- `/receipt` - Товарные чеки WB
- `/queue` - Ваша очередь задач
- `/status` - Статус сервисов

### Режимы работы

1. **📸 Изображение → Текст** - Отправьте фото для OCR
2. **🎤 Аудио → Текст** - Отправьте голосовое для транскрипции
3. **🔊 Текст → Аудио** - Напишите текст для TTS
4. **🖼️ Текст → Изображение** - Напишите текст для генерации
5. **🧾 Товарный чек** - Создание чека по товарам WB

### Товарные чеки (/receipt)

Создание товарных чеков для Wildberries в формате РБ:

**Формат ввода:**
- Артикул: `178601980 x 2`
- Ссылка WB: `https://wildberries.ru/catalog/12345678/detail.aspx x 1`

**Пример:**
```
178601980 x 2
99999999 x 1
https://wildberries.ru/catalog/11111111/detail.aspx x 3
```

**Возможности:**
- Ввод товаров по артикулам или ссылкам WB
- Предпросмотр чека перед подтверждением
- ✏️ Редактирование названий товаров в предпросмотре
- ➕ Добавление и удаление товаров
- Генерация PDF в формате товарного чека РБ
- Асинхронная обработка через Kafka
- Сохранение истории чеков

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

# Запустите unit-тесты
pytest --ignore=services/transcription_service/ -v

# Запустите все тесты (включая интеграционные)
pytest --run-integration --ignore=services/transcription_service/ -v

# Запустите линтинг
ruff check .
ruff check . --fix  # автоисправление
```

## 🛠️ Технологический стек

- **Python 3.12+** - Основной язык
- **Apache Kafka** - Message broker
- **PostgreSQL** - База данных (настройки пользователей, init.sh миграции)
- **python-telegram-bot** - Telegram API
- **RapidOCR** - Распознавание текста (ONNX Runtime, GPU support)
- **OpenAI Whisper** - Транскрибация
- **gTTS** - Синтез речи
- **Stable Diffusion XL / FLUX** - Генерация изображений
- **Docker** - Контейнеризация
- **Multi-stage builds** - Оптимизация образов
- **ruff** - Линтинг и форматирование

## 📄 Лицензия

MIT License
