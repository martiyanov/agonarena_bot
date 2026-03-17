from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.bot.keyboards.main_menu import build_main_menu

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "Agon Arena Bot\n\nТекстовые управленческие поединки: 2 раунда, смена ролей, 3 судьи.",
        reply_markup=build_main_menu(),
    )
