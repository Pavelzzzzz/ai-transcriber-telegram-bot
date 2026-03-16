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

# Install PyTorch based on GPU type
RUN pip install --no-cache-dir torch && \
    pip install --no-cache-dir -r requirements.txt

# ============================================
# Stage 2: Runtime - минимальный образ
# ============================================
FROM python:3.12-slim

ARG GPU_TYPE=nvidia
ENV GPU_TYPE=${GPU_TYPE}

WORKDIR /app

# Install runtime dependencies based on GPU type
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch (CPU version as default, will be overridden at runtime if needed)
RUN pip install --no-cache-dir torch torchvision

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /install /usr/local

COPY services/ services/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

CMD ["python", "-m", "services.image_gen_service.main"]
