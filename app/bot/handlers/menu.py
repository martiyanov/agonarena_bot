from aiogram import F, Router
from aiogram.types import Message

from app.db.session import AsyncSessionLocal
from app.services import DuelService, JudgeService, OpponentService, OpponentTurnContext, ScenarioService

router = Router()
MENU_TEXTS = {
    "⚔️ Начать поединок",
    "📚 Сценарии",
    "🏆 Мои результаты",
    "ℹ️ Как это работает",
    "✍️ Сделать ход",
    "⏭️ Следующий раунд",
    "🏁 Завершить поединок",
}


@router.message(F.text == "📚 Сценарии")
async def show_scenarios(message: Message) -> None:
    async with AsyncSessionLocal() as session:
        scenarios = await ScenarioService().list_active(session)

    if not scenarios:
        await message.answer("Сценарии пока не загружены.")
        return

    lines = ["Доступные сценарии:"]
    for item in scenarios:
        lines.append(
            f"• {item.title} — `{item.code}`\n"
            f"  {item.description}\n"
            f"  Роли: {item.role_a_name} ↔ {item.role_b_name}"
        )
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
        f"Стартовая реплика AI: {rounds[0].opening_line}",
        "",
        "Дальше: нажмите «✍️ Сделать ход», отправьте свою реплику, затем при желании перейдите в следующий раунд кнопкой «⏭️ Следующий раунд».",
    ]
    await message.answer("\n".join(lines))


@router.message(F.text == "⚔️ Начать поединок")
async def start_duel_from_menu(message: Message) -> None:
    await _start_duel(message)


@router.message(F.text.regexp(r"^[a-z_]+$") & ~F.text.in_(MENU_TEXTS))
async def start_duel_by_scenario_code(message: Message) -> None:
    await _start_duel(message, scenario_code=message.text.strip())


@router.message(F.text == "✍️ Сделать ход")
async def make_turn_prompt(message: Message) -> None:
    await message.answer("Отправьте текст своего хода следующим сообщением — я отвечу от лица AI-оппонента.")


@router.message(F.text == "⏭️ Следующий раунд")
async def go_to_next_round(message: Message) -> None:
    async with AsyncSessionLocal() as session:
        duel_service = DuelService()
        duel = await duel_service.get_latest_duel_for_user(session, telegram_user_id=message.from_user.id)
        if duel is None:
            await message.answer("У вас нет активного поединка. Нажмите «⚔️ Начать поединок». ")
            return
        if duel.current_round_number != 1:
            await message.answer("Вы уже во втором раунде. Когда будете готовы — завершайте поединок кнопкой «🏁 Завершить поединок». ")
            return

        round_1 = await duel_service.get_round(session, duel.id, 1)
        round_2 = await duel_service.get_round(session, duel.id, 2)
        if round_1 is None or round_2 is None:
            await message.answer("Не удалось найти раунды поединка.")
            return

        await duel_service.complete_round(duel, round_1)
        await duel_service.ensure_round_started(duel, round_2)
        await session.commit()

    await message.answer(
        "Раунд 1 завершён. Начинаем раунд 2 со сменой ролей.\n"
        f"Теперь вы — {round_2.user_role}, AI — {round_2.ai_role}.\n"
        f"Стартовая реплика AI: {round_2.opening_line}"
    )


@router.message(F.text == "🏁 Завершить поединок")
async def finish_duel_from_menu(message: Message) -> None:
    async with AsyncSessionLocal() as session:
        duel_service = DuelService()
        judge_service = JudgeService()

        duel = await duel_service.get_latest_duel_for_user(session, telegram_user_id=message.from_user.id)
        if duel is None:
            await message.answer("У вас нет поединка для завершения.")
            return
        if duel.status == "finished":
            await message.answer(f"Этот поединок уже завершён.\n\n{duel.final_verdict or ''}")
            return

        round_1 = await duel_service.get_round(session, duel.id, 1)
        round_2 = await duel_service.get_round(session, duel.id, 2)
        scenario = await duel_service.get_scenario_by_id(session, duel.scenario_id)
        if round_1 is None or round_2 is None or scenario is None:
            await message.answer("Не удалось собрать данные для завершения поединка.")
            return

        if round_2.status != "finished":
            await duel_service.complete_round(duel, round_2)

        contexts = judge_service.build_contexts_for_duel(
            duel=duel,
            scenario_code=scenario.code,
            round1_messages=await duel_service.list_messages_for_round(session, duel.id, 1),
            round2_messages=await duel_service.list_messages_for_round(session, duel.id, 2),
        )
        verdicts = await judge_service.run_all_judges(contexts)
        for verdict in verdicts:
            session.add(await judge_service.save_verdict(duel, verdict))

        final_verdict = judge_service.summarize_final_verdict(verdicts)
        await duel_service.finish_duel(duel, final_verdict)
        await session.commit()

    await message.answer(f"Поединок завершён.\n\n{final_verdict}")


@router.message(F.text == "🏆 Мои результаты")
async def my_results(message: Message) -> None:
    async with AsyncSessionLocal() as session:
        duel_service = DuelService()
        duel = await duel_service.get_latest_duel_for_user(session, telegram_user_id=message.from_user.id)
        if duel is None:
            await message.answer("Пока нет сохранённых поединков.")
            return

        rounds = await duel_service.get_duel_rounds(session, duel.id)
        judge_results = await duel_service.list_judge_results(session, duel.id)

    lines = [
        f"Последний поединок: #{duel.id}",
        f"Статус: {duel.status}",
        f"Текущий раунд: {duel.current_round_number}",
    ]
    for round_obj in rounds:
        lines.append(f"- Раунд {round_obj.round_number}: {round_obj.status} ({round_obj.user_role} vs {round_obj.ai_role})")
    if judge_results:
        lines.append("\nВердикты судей:")
        for item in judge_results:
            lines.append(f"- {item.judge_type}: {item.winner} — {item.comment}")
    if duel.final_verdict:
        lines.append(f"\nИтог:\n{duel.final_verdict}")

    await message.answer("\n".join(lines))


@router.message(F.text == "ℹ️ Как это работает")
async def how_it_works(message: Message) -> None:
    await message.answer(
        "Формат MVP: 2 раунда, во втором раунде смена ролей, затем три судьи выносят итог. "
        "Поток такой: старт поединка → ходы в раунде 1 → «Следующий раунд» → ходы в раунде 2 → «Завершить поединок»."
    )


@router.message(F.text & ~F.text.in_(MENU_TEXTS))
async def process_turn(message: Message) -> None:
    async with AsyncSessionLocal() as session:
        duel_service = DuelService()
        opponent_service = OpponentService()

        duel = await duel_service.get_latest_duel_for_user(session, telegram_user_id=message.from_user.id)
        if duel is None:
            await message.answer("У вас пока нет активных поединков. Нажмите «⚔️ Начать поединок». ")
            return
        if duel.status == "finished":
            await message.answer("Последний поединок уже завершён. Начните новый кнопкой «⚔️ Начать поединок». ")
            return

        scenario = await duel_service.get_scenario_by_id(session, duel.scenario_id)
        round_obj = await duel_service.get_round(session, duel_id=duel.id, round_number=duel.current_round_number)
        if round_obj is None:
            await message.answer("Не удалось найти текущий раунд поединка. Попробуйте начать новый поединок.")
            return

        await duel_service.ensure_round_started(duel, round_obj)
        await duel_service.add_message(
            session,
            duel_id=duel.id,
            round_number=round_obj.round_number,
            author="user",
            content=message.text,
        )

        history = await duel_service.list_messages_for_round(session, duel_id=duel.id, round_number=round_obj.round_number)
        context = OpponentTurnContext(
            scenario_title=scenario.title if scenario else "",
            scenario_description=scenario.description if scenario else "",
            round=round_obj,
            history=history,
        )
        ai_reply = await opponent_service.generate_reply(context)

        await duel_service.add_message(
            session,
            duel_id=duel.id,
            round_number=round_obj.round_number,
            author="ai",
            content=ai_reply,
        )
        await session.commit()

    await message.answer(ai_reply)
