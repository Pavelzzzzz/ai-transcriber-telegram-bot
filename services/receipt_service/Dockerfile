FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

COPY services/receipt_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/receipt_service/ ./services/receipt_service/
COPY services/common/ ./services/common/

RUN mkdir -p /app/downloads/receipts

ENV PYTHONPATH=/app
ENV OUTPUT_DIR=/app/downloads/receipts

CMD ["python", "-m", "services.receipt_service.main"]
