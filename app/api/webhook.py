from fastapi import APIRouter, HTTPException, Request
from aiogram import Bot
from aiogram.types import Update

from app.bot import build_dispatcher
from app.config import settings
from app.utils.locks import duel_lock_manager

router = APIRouter(prefix="/telegram")
dp = build_dispatcher()


@router.on_event("startup")
async def startup_event():
    """Start background cleanup task for duel locks."""
    duel_lock_manager.start_cleanup()


@router.on_event("shutdown")
async def shutdown_event():
    """Stop background cleanup task for duel locks."""
    duel_lock_manager.stop_cleanup()


@router.post("/webhook")
async def telegram_webhook(request: Request) -> dict:
    if not settings.telegram_bot_token:
        raise HTTPException(status_code=503, detail="Telegram bot token is not configured")

    payload = await request.json()
    bot = Bot(token=settings.telegram_bot_token)
    update = Update.model_validate(payload)
    await dp.feed_update(bot, update)
    return {"ok": True}
