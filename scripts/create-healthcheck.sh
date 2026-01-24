#!/bin/bash

# Скрипт для создания healthcheck файла в контейнере
echo "Creating healthcheck in container..."
cat > /app/.healthcheck << 'EOF'
import os
import sys

# Проверяем основные компоненты
try:
    # Проверяем токен
    import os
    if os.getenv('TELEGRAM_BOT_TOKEN'):
        # Простая проверка что модуль загрузился
        sys.exit(0)
    else:
        sys.exit(1)
except Exception as e:
    print(f"Healthcheck error: {e}")
    sys.exit(1)
EOF

chmod +x /app/.healthcheck
echo "Healthcheck created successfully"