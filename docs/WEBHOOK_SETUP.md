# Webhook Setup Guide

This guide explains how to transition the AgonArena bot from polling mode to webhook mode with Let's Encrypt SSL.

## Overview

- **Domain**: `37-46-18-40.sslip.io`
- **SSL**: Let's Encrypt with auto-renewal
- **Security**: Secret token validation for webhook requests
- **Reverse Proxy**: Nginx

## Prerequisites

- Docker and Docker Compose installed
- Domain `37-46-18-40.sslip.io` pointing to your server (already configured)
- Root/sudo access for SSL certificate setup
- Telegram bot token

## Quick Start

### 1. Generate Webhook Secret

Generate a secure random secret:

```bash
openssl rand -hex 32
```

Copy the output and add it to your `.env` file.

### 2. Configure Environment

Update your `.env` file:

```bash
# Change from localhost to your domain
APP_BASE_URL=https://37-46-18-40.sslip.io

# Add the secret you generated
TELEGRAM_WEBHOOK_SECRET=your-generated-secret-here

# Ensure bot token is set
TELEGRAM_BOT_TOKEN=your-bot-token
```

### 3. Setup SSL Certificate

Run the automated SSL setup script:

```bash
sudo ./scripts/setup_ssl.sh
```

This script will:
- Install certbot if needed
- Obtain Let's Encrypt certificate for `37-46-18-40.sslip.io`
- Update nginx configuration
- Setup auto-renewal cron job (runs twice daily)
- Create symlinks for application compatibility

### 4. Start Services

Start the bot in webhook mode:

```bash
docker-compose -f docker-compose.webhook.yml up -d
```

### 5. Set Webhook

Register the webhook with Telegram:

```bash
python scripts/set_webhook.py
```

Expected output:
```
🔧 Setting webhook to: https://37-46-18-40.sslip.io/telegram/webhook
📡 Telegram API: https://api.telegram.org/bot<token>/setWebhook
✅ Webhook successfully set to: https://37-46-18-40.sslip.io/telegram/webhook
📋 Current webhook info: {...}
✅ Webhook verification successful
🎉 Webhook setup completed successfully!
```

## Verification

### Check Webhook Status

```bash
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
```

### Test Bot

Send a message to your bot in Telegram. It should respond normally.

### Check Logs

```bash
# Application logs
docker-compose -f docker-compose.webhook.yml logs -f app

# Nginx logs
docker-compose -f docker-compose.webhook.yml logs -f nginx
```

## Rollback to Polling Mode

If you need to rollback to polling mode:

### 1. Stop Webhook Services

```bash
docker-compose -f docker-compose.webhook.yml down
```

### 2. Delete Webhook

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/deleteWebhook"
```

### 3. Start Polling Mode

```bash
docker-compose up -d
```

## Security

### Webhook Secret Token

The bot validates the `X-Telegram-Bot-Api-Secret-Token` header on every webhook request. Requests without a valid secret token receive a 401 Unauthorized response.

This protects against:
- Unauthorized webhook calls
- Replay attacks
- Accidental webhook calls from other sources

### SSL/TLS

- TLS 1.2 and 1.3 only
- Strong cipher suites
- Let's Encrypt certificates with auto-renewal

## Maintenance

### Manual Certificate Renewal

```bash
sudo certbot renew
# Or use the renewal script
sudo ./scripts/renew_ssl.sh
```

### Test Auto-Renewal

```bash
sudo certbot renew --dry-run
```

### Update Webhook Settings

If you need to change webhook parameters:

```bash
python scripts/set_webhook.py
```

### View Certificate Info

```bash
sudo certbot certificates
```

## Troubleshooting

### Certificate Issues

**Problem**: Certificate not found
```bash
# Check certificate status
sudo certbot certificates

# Re-run setup
sudo ./scripts/setup_ssl.sh
```

### Webhook Not Receiving Updates

**Problem**: Bot not responding to messages

1. Check webhook info:
   ```bash
   curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"
   ```

2. Check last error date and message in the response

3. Verify secret token matches in `.env` and webhook settings

4. Check nginx and app logs:
   ```bash
   docker-compose -f docker-compose.webhook.yml logs
   ```

### Nginx Configuration Issues

**Problem**: Nginx fails to start

1. Test configuration:
   ```bash
   sudo nginx -t
   ```

2. Check for certificate file permissions

3. Verify paths in `ops/nginx/agonarena_bot.conf`

### Port Conflicts

**Problem**: Port 80 or 443 already in use

```bash
# Find what's using the port
sudo lsof -i :80
sudo lsof -i :443

# Stop conflicting service or change its port
```

## Architecture

```
┌─────────────────┐
│   Telegram API  │
└────────┬────────┘
         │ HTTPS + Secret Token
         ▼
┌─────────────────┐
│   Nginx (443)   │ SSL termination
└────────┬────────┘
         │ HTTP
         ▼
┌─────────────────┐
│  Bot App (8080) │ FastAPI + Aiogram
└─────────────────┘
```

## Files Reference

| File | Purpose |
|------|---------|
| `docker-compose.webhook.yml` | Docker Compose for webhook mode |
| `scripts/setup_ssl.sh` | SSL certificate automation |
| `scripts/renew_ssl.sh` | Certificate renewal (auto-created) |
| `scripts/set_webhook.py` | Webhook registration |
| `ops/nginx/agonarena_bot.conf` | Nginx configuration |
| `app/api/webhook.py` | Webhook endpoint with secret validation |

## Migration Checklist

- [ ] Generate `TELEGRAM_WEBHOOK_SECRET`
- [ ] Update `.env` with `APP_BASE_URL=https://37-46-18-40.sslip.io`
- [ ] Run `sudo ./scripts/setup_ssl.sh`
- [ ] Start services: `docker-compose -f docker-compose.webhook.yml up -d`
- [ ] Set webhook: `python scripts/set_webhook.py`
- [ ] Test bot functionality
- [ ] Verify auto-renewal cron job: `sudo crontab -l`
