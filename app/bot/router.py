from aiogram import Dispatcher

from app.bot.handlers.menu import router as menu_router
from app.bot.handlers.start import router as start_router


def build_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    dp.include_router(start_router)
    dp.include_router(menu_router)
    return dp
