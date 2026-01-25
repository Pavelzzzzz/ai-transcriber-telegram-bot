# Оптимизированный Dockerfile для AI Транскрибатора (Linux)
FROM python:3.11-slim

# Метаданные образа
LABEL maintainer="AI Transcriber Team" \
      description="AI-powered Telegram bot for text transcription" \
      version="1.0.0" \
      name="ai-transcriber-bot"

# Установка системных зависимостей
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-rus \
    tesseract-ocr-eng \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgl1 \
    libglib2.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Создание рабочего каталога
WORKDIR /app

# Создание non-root пользователя
RUN useradd --create-home --shell /bin/bash app

# Настройка переменных окружения для pip
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Копирование и установка зависимостей
COPY --chown=app:app requirements.txt .
USER app
RUN pip install --user --upgrade pip \
    && pip install --user torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu \
    && pip install --user -r requirements.txt

# Переключение на root для копирования файлов
USER root

# Копирование исходного кода
COPY --chown=app:app . .

# Создание необходимых директорий с правами
RUN mkdir -p downloads logs \
    && chown -R app:app /app \
    && chmod -R 755 downloads logs

# Настройка PATH для user packages
ENV PATH="/home/app/.local/bin:$PATH"

# Переключение на пользователя app
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Запуск бота
CMD ["python", "-u", "main.py"]