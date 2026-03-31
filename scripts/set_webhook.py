#!/usr/bin/env python3
"""
Script to set webhook for Telegram bot
"""

import asyncio
import aiohttp
from app.config import settings


async def set_webhook():
    """Set webhook for Telegram bot."""
    if not settings.telegram_bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not configured")
        return False
    
    if not settings.app_base_url:
        print("❌ APP_BASE_URL not configured")
        return False
    
    webhook_url = f"{settings.app_base_url}/telegram/webhook"
    telegram_api_url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/setWebhook"
    
    print(f"🔧 Setting webhook to: {webhook_url}")
    print(f"📡 Telegram API: {telegram_api_url}")
    
    async with aiohttp.ClientSession() as session:
        try:
            data = {
                "url": webhook_url,
                "secret_token": settings.telegram_webhook_secret or "",
                "max_connections": 40,
                "allowed_updates": ["message", "callback_query", "inline_query"]
            }
            async with session.post(telegram_api_url, json=data) as response:
                result = await response.json()
                
                if result.get("ok"):
                    print(f"✅ Webhook successfully set to: {webhook_url}")
                    
                    # Verify webhook info
                    info_url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/getWebhookInfo"
                    async with session.get(info_url) as info_response:
                        info = await info_response.json()
                        print(f"📋 Current webhook info: {info}")
                        
                        if info.get("result", {}).get("url") == webhook_url:
                            print("✅ Webhook verification successful")
                            return True
                        else:
                            print("❌ Webhook verification failed")
                            return False
                else:
                    print(f"❌ Failed to set webhook: {result}")
                    return False
        except Exception as e:
            print(f"❌ Error setting webhook: {e}")
            return False


if __name__ == "__main__":
    success = asyncio.run(set_webhook())
    if success:
        print("🎉 Webhook setup completed successfully!")
    else:
        print("💥 Webhook setup failed!")
        exit(1)