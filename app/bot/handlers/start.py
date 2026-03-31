from pathlib import Path

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.bot.keyboards.main_menu import build_main_menu
from app.db import session as db_session
from app.services.duel_service import DuelService

router = Router()


def _get_version() -> str:
    """Get version from VERSION file or git."""
    # Try multiple paths for different environments
    paths = [
        Path("/app/VERSION"),  # Docker container
        Path(__file__).parent.parent.parent.parent / "VERSION",  # Development
        Path.cwd() / "VERSION",  # Current directory
    ]
    for version_file in paths:
        if version_file.exists():
            return version_file.read_text().strip()
    return "unknown"


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    # Check if user has active duel
    async with db_session.AsyncSessionLocal() as session:
        duel_service = DuelService()
        duel = await duel_service.get_latest_duel_for_user(
            session, telegram_user_id=message.from_user.id
        )
        has_active_duel = duel and duel.status not in ("finished", "cancelled")
    
    version = _get_version()
    version_line = f"\n\n🤖 Agon Arena v{version}"

    if has_active_duel:
        # Text for in_duel state
        menu_text = (
            "Поединок уже идёт.\n\n"
            "Продолжайте отвечать текстом или голосом.\n"
            "Когда раунд завершён, нажмите «🏁 Завершить раунд»."
        )
    else:
        # Text for idle state
        menu_text = (
            "Добро пожаловать в Agon Arena.\n\n"
            "Здесь можно тренировать управленческие поединки:\n"
            "— 2 раунда\n"
            "— смена ролей\n"
            "— разбор от 3 судей\n\n"
            "Выберите сценарий или начните случайный поединок."
        )
    
    menu_text += version_line

    await message.answer(
        menu_text,
        reply_markup=build_main_menu(has_active_duel=has_active_duel),
    )
