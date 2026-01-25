# 🚀 Quick Start Guide

## ⚡ Быстрый запуск

```bash
# 🐳 Docker (рекомендуется)
docker-compose up -d

# 📊 Проверка статуса
docker-compose logs -f ai-transcriber-bot
```

## 🎯 Основные команды

### 👤 Пользовательские команды
- `/start` - Запуск бота
- `/help` - Помощь
- `/mode` - Выбор режима работы
- `/status` - Статус

### 🔐 Админ команды  
- `/admin` - Панель администратора
- `/stats` - Статистика
- `/users` - Пользователи
- `/logs` - Логи

## 🔄 Режимы работы

1. **📸 Фото → Текст** (OCR)
2. **🎤 Голос → Текст** (Whisper)
3. **📝 Текст → Голос** (TTS)
4. **💬 Текст → Ответ** (AI)

## 🛠️ Разработка

```bash
# 🚀 Локальный запуск
python main_simple.py

# 🧪 Запуск тестов
pytest

# 📊 Покрытие кода
pytest --cov=src --cov=utils
```

## 📁 Ключевые файлы

```
main_simple.py              # 🚀 Точка входа (рабочая)
config/settings.py           # ⚙️ Конфигурация
src/core/bot_core.py       # 🤖 Ядро бота
src/services/user_service.py # 👥 Сервис пользователей
database/models.py          # 🗄️ Модели БД
```

## 🔧 Конфигурация

```env
TELEGRAM_BOT_TOKEN=your_token
ADMIN_USERNAMES=admin1,admin2
WHISPER_MODEL=tiny
LOG_LEVEL=INFO
```

## 🐛 Частые проблемы

```bash
# ❌ Cannot write to logs directory
sudo chown -R $USER:$USER logs/

# ❌ Bot token not found
echo "TELEGRAM_BOT_TOKEN=your_token" >> .env

# ❌ Port already in use
docker-compose down && docker-compose up -d
```

## 📊 Диагностика

```bash
# ✅ Проверка импортов
python -c "import telegram, whisper; print('OK')"

# ✅ Проверка токена
curl -X GET "https://api.telegram.org/bot$TOKEN/getMe"

# ✅ Проверка Docker
docker ps
```

---

🎉 **Бот готов к использованию! Отправьте `/start` в Telegram**