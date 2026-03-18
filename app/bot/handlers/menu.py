from __future__ import annotations

import random
import tempfile
from html import escape
from pathlib import Path

from aiogram import F, Router
from aiogram.types import Message

from app.db.session import AsyncSessionLocal
from app.services import (
    DuelService,
    JudgeService,
    OpponentService,
    OpponentTurnContext,
    ScenarioService,
    TranscriptionService,
)

router = Router()

START_BUTTON = "⚔️ Начать поединок"
SCENARIOS_BUTTON = "📚 Сценарии"
RESULTS_BUTTON = "🏆 Результаты"
RESULTS_BUTTON_LEGACY = "🏆 Мои результаты"
RULES_BUTTON = "ℹ️ Правила"
RULES_BUTTON_LEGACY = "ℹ️ Как это работает"
TURN_BUTTON = "✍️ Отправить реплику"
TURN_BUTTON_LEGACY = "✍️ Сделать ход"
NEXT_ROUND_BUTTON = "⏭️ Следующий раунд"
FINISH_BUTTON = "🏁 Завершить поединок"

MENU_TEXTS = {
    START_BUTTON,
    SCENARIOS_BUTTON,
    RESULTS_BUTTON,
    RESULTS_BUTTON_LEGACY,
    RULES_BUTTON,
    RULES_BUTTON_LEGACY,
    TURN_BUTTON,
    TURN_BUTTON_LEGACY,
    NEXT_ROUND_BUTTON,
    FINISH_BUTTON,
}


def _timer_hint(seconds: int) -> str:
    return f"⏱ На раунд: {seconds} сек."


@router.message(F.text == SCENARIOS_BUTTON)
async def show_scenarios(message: Message) -> None:
    async with AsyncSessionLocal() as session:
        scenarios = await ScenarioService().list_active(session)

    if not scenarios:
        await message.answer("Сценариев пока нет. Добавьте их в базу и попробуйте снова.")
        return

    blocks = [
        "<b>Сценарии</b>",
        "Выберите код сценария из списка или нажмите <b>«Начать поединок»</b>.",
    ]
    for item in scenarios:
        blocks.append(
            "\n".join(
                [
                    f"• <b>{escape(item.title)}</b>",
                    f"Код: <code>{escape(item.code)}</code>",
                    f"{escape(item.description)}",
                    f"Роли: {escape(item.role_a_name)} ↔ {escape(item.role_b_name)}",
                ]
            )
        )

    await message.answer("\n\n".join(blocks), parse_mode="HTML")


async def _start_duel(message: Message, scenario_code: str | None = None) -> None:
    async with AsyncSessionLocal() as session:
        duel_service = DuelService()
        if scenario_code:
            scenario = await duel_service.get_scenario_by_code(session, scenario_code)
        else:
            scenarios = await ScenarioService().list_active(session)
            scenario = random.choice(scenarios) if scenarios else None

        if scenario is None:
            await message.answer("Не смог подобрать сценарий для старта. Попробуйте ещё раз позже.")
            return

        duel = await duel_service.create_duel(session, telegram_user_id=message.from_user.id, scenario=scenario)
        rounds = await duel_service.get_duel_rounds(session, duel.id)

    round_1 = rounds[0]
    text = "\n".join(
        [
            f"<b>Поединок #{duel.id}</b>",
            f"Сценарий: <b>{escape(scenario.title)}</b>",
            _timer_hint(duel.turn_time_limit_sec),
            f"Раунд 1: вы — <b>{escape(round_1.user_role)}</b>, соперник — <b>{escape(round_1.ai_role)}</b>",
            "",
            "<b>Первая реплика соперника</b>",
            escape(round_1.opening_line),
            "",
            "<b>Что дальше</b>",
            f"1. Нажмите <b>«{escape(TURN_BUTTON)}»</b>.",
            "2. Пришлите текст или голосовое.",
            "3. После ответа можно продолжить раунд или перейти дальше.",
        ]
    )
    await message.answer(text, parse_mode="HTML")


async def _run_turn(message: Message, user_text: str, *, recognized_from_voice: bool = False) -> None:
    clean_text = user_text.strip()
    if not clean_text:
        await message.answer("Не получилось прочитать реплику. Попробуйте ещё раз.")
        return

    async with AsyncSessionLocal() as session:
        duel_service = DuelService()
        opponent_service = OpponentService()

        duel = await duel_service.get_latest_duel_for_user(session, telegram_user_id=message.from_user.id)
        if duel is None:
            await message.answer(f"Сейчас у вас нет активного поединка. Нажмите «{START_BUTTON}».")
            return
        if duel.status == "finished":
            await message.answer(f"Последний поединок уже завершён. Чтобы начать заново, нажмите «{START_BUTTON}».")
            return

        scenario = await duel_service.get_scenario_by_id(session, duel.scenario_id)
        round_obj = await duel_service.get_round(session, duel_id=duel.id, round_number=duel.current_round_number)
        if round_obj is None:
            await message.answer("Не нашёл текущий раунд. Лучше начать новый поединок.")
            return

        await duel_service.ensure_round_started(duel, round_obj)
        if duel_service.is_round_expired(duel, round_obj):
            await duel_service.complete_round(duel, round_obj)
            await session.commit()
            if round_obj.round_number == 1:
                await message.answer(f"⏱ Время первого раунда вышло. Нажмите «{NEXT_ROUND_BUTTON}», чтобы продолжить.")
            else:
                await message.answer(f"⏱ Время второго раунда вышло. Нажмите «{FINISH_BUTTON}», чтобы получить разбор судей.")
            return

        await duel_service.add_message(
            session,
            duel_id=duel.id,
            round_number=round_obj.round_number,
            author="user",
            content=clean_text,
        )

        history = await duel_service.list_messages_for_round(session, duel_id=duel.id, round_number=round_obj.round_number)
        context = OpponentTurnContext(
            scenario_title=scenario.title if scenario else "",
            scenario_description=scenario.description if scenario else "",
            round_number=round_obj.round_number,
            user_role=round_obj.user_role,
            ai_role=round_obj.ai_role,
            opening_line=round_obj.opening_line,
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

    if recognized_from_voice:
        await message.answer(f"<b>Распознал так:</b> {escape(clean_text)}\n\n{escape(ai_reply)}", parse_mode="HTML")
        return

    await message.answer(ai_reply)


async def _download_telegram_file(message: Message) -> Path:
    file_id = None
    suffix = ".bin"

    if message.voice:
        file_id = message.voice.file_id
        suffix = ".oga"
    elif message.audio:
        file_id = message.audio.file_id
        suffix = Path(message.audio.file_name or "audio.mp3").suffix or ".mp3"

    if file_id is None:
        raise RuntimeError("Unsupported media type for transcription")

    telegram_file = await message.bot.get_file(file_id)
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp_path = Path(tmp.name)

    await message.bot.download_file(telegram_file.file_path, destination=tmp_path)
    return tmp_path


@router.message(F.text == START_BUTTON)
async def start_duel_from_menu(message: Message) -> None:
    await _start_duel(message)


@router.message(F.text.regexp(r"^[a-z_]+$") & ~F.text.in_(MENU_TEXTS))
async def start_duel_by_scenario_code(message: Message) -> None:
    await _start_duel(message, scenario_code=message.text.strip())


@router.message(F.text.in_({TURN_BUTTON, TURN_BUTTON_LEGACY}))
async def make_turn_prompt(message: Message) -> None:
    await message.answer("Пришлите следующим сообщением текст или голосовое. Я распознаю сообщение и отвечу от лица соперника.")


@router.message(F.text == NEXT_ROUND_BUTTON)
async def go_to_next_round(message: Message) -> None:
    async with AsyncSessionLocal() as session:
        duel_service = DuelService()
        duel = await duel_service.get_latest_duel_for_user(session, telegram_user_id=message.from_user.id)
        if duel is None:
            await message.answer(f"Сейчас у вас нет активного поединка. Нажмите «{START_BUTTON}».")
            return
        if duel.current_round_number != 1:
            await message.answer(f"Вы уже во втором раунде. Когда будете готовы, нажмите «{FINISH_BUTTON}».")
            return

        round_1 = await duel_service.get_round(session, duel.id, 1)
        round_2 = await duel_service.get_round(session, duel.id, 2)
        if round_1 is None or round_2 is None:
            await message.answer("Не смог найти раунды этого поединка.")
            return

        await duel_service.complete_round(duel, round_1)
        await duel_service.ensure_round_started(duel, round_2)
        await session.commit()

    text = "\n".join(
        [
            "<b>Раунд 1 завершён</b>",
            "Переходим ко второму раунду со сменой ролей.",
            _timer_hint(duel.turn_time_limit_sec),
            f"Теперь вы — <b>{escape(round_2.user_role)}</b>, соперник — <b>{escape(round_2.ai_role)}</b>.",
            "",
            "<b>Первая реплика соперника</b>",
            escape(round_2.opening_line),
        ]
    )
    await message.answer(text, parse_mode="HTML")


@router.message(F.text == FINISH_BUTTON)
async def finish_duel_from_menu(message: Message) -> None:
    async with AsyncSessionLocal() as session:
        duel_service = DuelService()
        judge_service = JudgeService()

        duel = await duel_service.get_latest_duel_for_user(session, telegram_user_id=message.from_user.id)
        if duel is None:
            await message.answer("Сейчас нечего завершать: активного поединка нет.")
            return
        if duel.status == "finished":
            await message.answer(f"Этот поединок уже завершён.\n\n{duel.final_verdict or ''}")
            return

        round_1 = await duel_service.get_round(session, duel.id, 1)
        round_2 = await duel_service.get_round(session, duel.id, 2)
        scenario = await duel_service.get_scenario_by_id(session, duel.scenario_id)
        if round_1 is None or round_2 is None or scenario is None:
            await message.answer("Не смог собрать данные для завершения поединка.")
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

    await message.answer(f"<b>Поединок завершён</b>\n\n{escape(final_verdict)}", parse_mode="HTML")


@router.message(F.text.in_({RESULTS_BUTTON, RESULTS_BUTTON_LEGACY}))
async def my_results(message: Message) -> None:
    async with AsyncSessionLocal() as session:
        duel_service = DuelService()
        duel = await duel_service.get_latest_duel_for_user(session, telegram_user_id=message.from_user.id)
        if duel is None:
            await message.answer("Пока нет сохранённых результатов.")
            return

        rounds = await duel_service.get_duel_rounds(session, duel.id)
        judge_results = await duel_service.list_judge_results(session, duel.id)

    lines = [
        f"<b>Последний поединок: #{duel.id}</b>",
        f"Статус: {escape(duel.status)}",
        f"Текущий раунд: {duel.current_round_number}",
        escape(_timer_hint(duel.turn_time_limit_sec)),
    ]
    for round_obj in rounds:
        lines.append(
            f"• Раунд {round_obj.round_number}: {escape(round_obj.status)} ({escape(round_obj.user_role)} vs {escape(round_obj.ai_role)})"
        )
    if judge_results:
        lines.append("\n<b>Вердикты судей</b>")
        for item in judge_results:
            lines.append(f"• {escape(item.judge_type)}: {escape(item.winner)} — {escape(item.comment)}")
    if duel.final_verdict:
        lines.append(f"\n<b>Итог</b>\n{escape(duel.final_verdict)}")

    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(F.text.in_({RULES_BUTTON, RULES_BUTTON_LEGACY}))
async def how_it_works(message: Message) -> None:
    await message.answer(
        "<b>Как проходит поединок</b>\n\n"
        "• Поединок состоит из двух раундов.\n"
        "• Во втором раунде роли меняются.\n"
        "• После завершения три судьи дают итоговый разбор.\n\n"
        "<b>Как действовать</b>\n"
        f"1. Нажмите <b>«{escape(START_BUTTON)}»</b>.\n"
        f"2. Отправляйте реплики через <b>«{escape(TURN_BUTTON)}»</b> текстом или голосом.\n"
        f"3. Перейдите через <b>«{escape(NEXT_ROUND_BUTTON)}»</b> ко второму раунду.\n"
        f"4. Завершите поединок кнопкой <b>«{escape(FINISH_BUTTON)}»</b>.\n\n"
        "На каждый раунд даётся 3 минуты.\n\n"
        "<b>Обратная связь</b>\n"
        "Если хотите оставить отзыв или предложить улучшение, напишите одним сообщением с префиксом <code>Обратная связь:</code>.\n\n"
        "<b>Поддержать проект</b>\n"
        "https://t.me/tribute/app?startapp=dHaW",
        parse_mode="HTML",
    )


@router.message(F.voice)
async def process_voice_turn(message: Message) -> None:
    transcription_service = TranscriptionService()
    if not transcription_service.is_configured():
        await message.answer("Распознавание голоса пока не настроено. Отправьте сообщение текстом.")
        return

    temp_path: Path | None = None
    try:
        await message.answer("Голосовое получил. Распознаю…")
        temp_path = await _download_telegram_file(message)
        transcript = await transcription_service.transcribe(temp_path, language="ru")
    except Exception:
        await message.answer("Не удалось распознать голосовое. Попробуйте ещё раз или отправьте текст.")
        return
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)

    await _run_turn(message, transcript, recognized_from_voice=True)


@router.message(F.audio)
async def process_audio_turn(message: Message) -> None:
    transcription_service = TranscriptionService()
    if not transcription_service.is_configured():
        await message.answer("Распознавание аудио пока не настроено. Отправьте сообщение текстом.")
        return

    temp_path: Path | None = None
    try:
        await message.answer("Аудио получил. Распознаю…")
        temp_path = await _download_telegram_file(message)
        transcript = await transcription_service.transcribe(temp_path, language="ru")
    except Exception:
        await message.answer("Не удалось распознать аудио. Попробуйте ещё раз или отправьте текст.")
        return
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)

    await _run_turn(message, transcript, recognized_from_voice=True)


@router.message(F.text & ~F.text.in_(MENU_TEXTS))
async def process_turn(message: Message) -> None:
    await _run_turn(message, message.text)
