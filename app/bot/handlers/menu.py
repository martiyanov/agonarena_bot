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


async def _start_duel(message: Message, scenario_code: str | None = None) -> None:
    async with AsyncSessionLocal() as session:
        duel_service = DuelService()
        if scenario_code:
            scenario = await duel_service.get_scenario_by_code(session, scenario_code)
        else:
            scenarios = await ScenarioService().list_active(session)
            scenario = scenarios[0] if scenarios else None

        if scenario is None:
            await message.answer("Не удалось подобрать сценарий для старта поединка.")
            return

        duel = await duel_service.create_duel(session, telegram_user_id=message.from_user.id, scenario=scenario)
        rounds = await duel_service.get_duel_rounds(session, duel.id)

    lines = [
        f"Поединок создан: #{duel.id}",
        f"Сценарий: {scenario.title}",
        f"Раунд 1: вы — {rounds[0].user_role}, AI — {rounds[0].ai_role}",
        f"Стартовая реплика: {rounds[0].opening_line}",
        "",
        "Дальше подключу пошаговый duel flow поверх этого старта.",
    ]
    await message.answer("\n".join(lines))


@router.message(F.text == "⚔️ Начать поединок")
async def start_duel_from_menu(message: Message) -> None:
    await _start_duel(message)


@router.message(F.text.regexp(r"^[a-z_]+$"))
async def start_duel_by_scenario_code(message: Message) -> None:
    await _start_duel(message, scenario_code=message.text.strip())


@router.message(F.text == "ℹ️ Как это работает")
async def how_it_works(message: Message) -> None:
    await message.answer(
        "Формат MVP: 2 раунда, во втором раунде смена ролей, итог выносят 3 судьи: собственник, команда и отправляющий на переговоры."
    )
