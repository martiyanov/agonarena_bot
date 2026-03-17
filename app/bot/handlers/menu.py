from aiogram import F, Router
from aiogram.types import Message

from app.db.session import AsyncSessionLocal
from app.services import DuelService, ScenarioService

router = Router()


@router.message(F.text == "📚 Сценарии")
async def show_scenarios(message: Message) -> None:
    async with AsyncSessionLocal() as session:
        scenarios = await ScenarioService().list_active(session)

    if not scenarios:
        await message.answer("Сценарии пока не загружены.")
        return

    lines = ["Доступные сценарии:"]
    for item in scenarios:
        lines.append(f"• {item.title} — `{item.code}`")
    await message.answer("\n".join(lines), parse_mode="Markdown")


@router.message(F.text == "⚔️ Начать поединок")
async def start_duel_from_menu(message: Message) -> None:
    async with AsyncSessionLocal() as session:
        scenarios = await ScenarioService().list_active(session)
        if not scenarios:
            await message.answer("Нет доступных сценариев для старта поединка.")
            return

        scenario = scenarios[0]
        duel = await DuelService().create_duel(session, telegram_user_id=message.from_user.id, scenario=scenario)
        rounds = await DuelService().get_duel_rounds(session, duel.id)

    lines = [
        f"Поединок создан: #{duel.id}",
        f"Сценарий: {scenario.title}",
        f"Раунд 1: вы — {rounds[0].user_role}, AI — {rounds[0].ai_role}",
        f"Стартовая реплика: {rounds[0].opening_line}",
        "",
        "Дальше подключу пошаговый duel flow поверх этого старта.",
    ]
    await message.answer("\n".join(lines))


@router.message(F.text == "ℹ️ Как это работает")
async def how_it_works(message: Message) -> None:
    await message.answer(
        "Формат MVP: 2 раунда, во втором раунде смена ролей, итог выносят 3 судьи: собственник, команда и отправляющий на переговоры."
    )
