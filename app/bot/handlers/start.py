from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.bot.keyboards.main_menu import build_main_menu

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "**Agon Arena**\n\nТренажёр управленческих поединков.\n\n• 2 раунда\n• смена ролей во втором раунде\n• 3 судьи с итоговым разбором\n\nВыберите действие в меню ниже. Кнопки стали короче, чтобы нормально выглядеть и на десктопе.",
        reply_markup=build_main_menu(),
        parse_mode="Markdown",
    )
