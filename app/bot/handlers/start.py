from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.bot.keyboards.main_menu import build_main_menu

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "<b>Agon Arena</b>\n\n"
        "Тренажёр управленческих поединков.\n\n"
        "Нажмите <b>«⚔️ Поединок»</b>, чтобы начать.\n"
        "На каждый раунд даётся 3 минуты.\n"
        "После двух раундов вы получите разбор от трёх судей.",
        reply_markup=build_main_menu(),
        parse_mode="HTML",
    )
