from fastapi import APIRouter, HTTPException, Request
from aiogram import Bot
from aiogram.types import Update

from app.bot import build_dispatcher
from app.config import settings

router = APIRouter(prefix="/telegram")
dp = build_dispatcher()


@router.post("/webhook")
async def telegram_webhook(request: Request) -> dict:
    if not settings.telegram_bot_token:
        raise HTTPException(status_code=503, detail="Telegram bot token is not configured")

    payload = await request.json()
    bot = Bot(token=settings.telegram_bot_token)
    update = Update.model_validate(payload)
    await dp.feed_update(bot, update)
    return {"ok": True}
