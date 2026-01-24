# Оптимизированный Dockerfile для AI Транскрибатора
FROM python:3.11-slim

# Метки образа
LABEL maintainer="AI Transcriber Team"
LABEL description="AI-powered Telegram bot for text transcription from images and audio"
LABEL version="1.0.0"
LABEL name="telegram_ai-transcriber_bot"

# Устанавливаем системные зависимости за один RUN
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-rus \
    tesseract-ocr-eng \
    ffmpeg \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libglib2.0-0 \
    libgl1 \
    wget \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Создаем рабочую директорию и переключаемся на нее
WORKDIR /app

# Используем non-root пользователя
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app

# Устанавливаем переменные окружения для pip
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore

# Копируем requirements.txt и устанавливаем зависимости от имени app
COPY --chown=app:app requirements.txt .
USER app

# Устанавливаем зависимости
RUN pip install --user --upgrade pip \
    && pip install --user torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu \
    && pip install --user -r requirements.txt

# Переключаемся обратно на root для копирования файлов
USER root

# Копируем исходный код
COPY --chown=app:app . .

# Создаем директории с правильными правами
RUN mkdir -p downloads logs \
    && chmod 755 downloads logs

# Устанавливаем переменные окружения
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/home/app/.local/bin:$PATH"

# Переключаемся на пользователя app
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Запуск бота
CMD ["python", "main.py"]
