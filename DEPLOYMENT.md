# 🐳 Docker Deployment Guide

## Quick Start

### Option 1: CPU-Only (Recommended for testing)
```bash
# Build the image
docker build -f Dockerfile.cpu -t ai-transcriber-bot-cpu .

# Run with docker-compose
docker-compose -f docker-compose.cpu.yml up -d
```

### Option 2: GPU Version (If available)
```bash
# Build the image (requires Docker with GPU support)
docker build -f Dockerfile -t ai-transcriber-bot .

# Run with docker-compose
docker-compose up -d
```

## Configuration

1. **Create .env file:**
```bash
cp .env.example .env
# Edit .env with your bot token
TELEGRAM_BOT_TOKEN=your_actual_bot_token_here
```

2. **Get Bot Token:**
   - Message @BotFather on Telegram
   - Create new bot with `/newbot`
   - Copy the token

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | Required | Your bot token from @BotFather |
| `WHISPER_MODEL` | `base` | Whisper model size (tiny/base/small/medium/large) |
| `LOG_LEVEL` | `INFO` | Logging level |
| `MAX_IMAGE_SIZE` | `20` | Max image size in MB |
| `DEFAULT_LANGUAGE` | `ru` | Recognition language |

## Managing the Bot

### View Logs
```bash
docker-compose logs -f telegram-bot
```

### Stop Bot
```bash
docker-compose down
```

### Update Bot
```bash
git pull
docker-compose build --no-cache
docker-compose up -d
```

## Troubleshooting

### Common Issues

1. **"manifest not found" error**
   - Use `Dockerfile.cpu` instead of `Dockerfile`
   - CPU version is more stable and widely compatible

2. **Bot doesn't respond**
   - Check bot token in .env
   - Verify internet connectivity
   - Check logs: `docker-compose logs telegram-bot`

3. **Memory issues**
   - Use smaller Whisper model: `WHISPER_MODEL=tiny`
   - Increase Docker memory limit
   - Use CPU version instead of GPU

4. **Tesseract errors**
   - CPU version includes Tesseract
   - For GPU version, ensure system dependencies are installed

### Performance Tips

- **For faster processing:** Use `WHISPER_MODEL=base` or `tiny`
- **For better accuracy:** Use `WHISPER_MODEL=medium` or `large` (slower)
- **CPU vs GPU:** GPU is faster but requires more setup

## Production Deployment

### Health Checks
The bot includes built-in health checks:
```bash
docker ps  # Shows health status
```

### Backup Data
```bash
# Backup logs and database
docker-compose exec telegram-bot tar -czf /backup/$(date +%Y%m%d).tar.gz /app/logs /app/downloads
```

### Monitoring
```bash
# Resource usage
docker stats ai-transcriber-bot-cpu

# Bot activity
docker-compose logs -f telegram-bot | grep "INFO"
```

## Support

1. Check logs first: `docker-compose logs telegram-bot`
2. Verify configuration in .env
3. Ensure system requirements are met
4. Check GitHub Issues for known problems

## Features

✅ **Image → Audio:** OCR + Text-to-Speech
✅ **Audio → Text:** Speech Recognition  
✅ **Admin Panel:** User management via Telegram
✅ **Database:** SQLAlchemy with SQLite
✅ **Logging:** Comprehensive error tracking
✅ **Docker:** Ready for production deployment