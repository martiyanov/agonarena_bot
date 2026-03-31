#!/usr/bin/env python3
"""
Script to run bot in polling mode instead of webhook
"""

import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.bot.router import build_dispatcher
from app.config import settings


async def main():
    """Run bot in polling mode."""
    if not settings.telegram_bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not configured")
        return
    
    print("🤖 Starting bot in polling mode...")
    print(f"📡 Bot username: {settings.telegram_bot_username}")
    
    # Configure bot
    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Get dispatcher
    dp = build_dispatcher()
    
    try:
        # Clear previous webhook (if any)
        await bot.delete_webhook(drop_pending_updates=True)
        print("🧹 Webhook cleared")
        
        # Start polling
        print("👂 Listening for updates...")
        await dp.start_polling(bot, skip_updates=True)
        
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"💥 Error running bot: {e}")
        raise
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())