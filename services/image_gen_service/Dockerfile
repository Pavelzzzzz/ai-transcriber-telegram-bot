# ============================================
# Stage 1: Builder - установка зависимостей
# ============================================
FROM python:3.12-slim as builder

ARG GPU_TYPE=nvidia
ENV GPU_TYPE=${GPU_TYPE}

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    curl \
    ca-certificates \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip

COPY services/image_gen_service/requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r /app/requirements.txt

# ============================================
# Stage 2: Runtime - минимальный образ
# ============================================
FROM python:3.12-slim

ARG GPU_TYPE=nvidia
ENV GPU_TYPE=${GPU_TYPE}

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    ca-certificates \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY services/ services/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=10s \
    CMD curl -f http://localhost:8080/ || exit 1

CMD ["python", "-m", "services.image_gen_service.main"]
