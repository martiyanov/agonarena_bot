from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.bot.keyboards.main_menu import build_main_menu
from app.db import session as db_session
from app.services.duel_service import DuelService

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    # Check if user has active duel
    async with db_session.AsyncSessionLocal() as session:
        duel_service = DuelService()
        duel = await duel_service.get_latest_duel_for_user(
            session, telegram_user_id=message.from_user.id
        )
        has_active_duel = duel and duel.status not in ("finished", "cancelled")
    
    await message.answer(
        "**Agon Arena**\n\nТренажёр управленческих поединков.\n\n• 2 раунда\n• смена ролей во втором раунде\n• 3 судьи с итоговым разбором\n\nВыберите действие в меню ниже.",
        reply_markup=build_main_menu(has_active_duel=has_active_duel),
        parse_mode="Markdown",
    )
