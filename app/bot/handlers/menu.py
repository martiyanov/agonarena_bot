from __future__ import annotations

import json
import random
import tempfile
from html import escape
from pathlib import Path
from time import time

from aiogram import F, Router
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery

from app.db.models import Scenario
from app.db import session as db_session
from app.services import (
    DuelService,
    JudgeService,
    LLMService,
    OpponentService,
    OpponentTurnContext,
    ScenarioService,
    TranscriptionService,
)
from app.services.round_timer_service import round_timer_service

router = Router()

START_BUTTON = "🎯 Выбрать сценарий"
RANDOM_SCENARIO_BUTTON = "🎲 Случайный сценарий"
START_BUTTON_LEGACY = "⚔️ Начать поединок"
CUSTOM_SCENARIO_BUTTON = "🎭 Свой сценарий"
SCENARIOS_BUTTON = "📚 Сценарии"
RESULTS_BUTTON = "🏆 Итоги"
RESULTS_BUTTON_LEGACY = "🏆 Результаты"
RESULTS_BUTTON_LEGACY_2 = "🏆 Мои результаты"
RULES_BUTTON = "ℹ️ Справка"
RULES_BUTTON_LEGACY = "ℹ️ Как это работает"
TURN_BUTTON = "✍️ Ход"
TURN_BUTTON_LEGACY = "✍️ Реплика"
TURN_BUTTON_LEGACY_2 = "✍️ Отправить реплику"
TURN_BUTTON_LEGACY_3 = "✍️ Сделать ход"
END_ROUND_BUTTON = "🏁 Завершить раунд"
NEXT_ROUND_BUTTON = "⏭️ Раунд 2"
NEXT_ROUND_BUTTON_LEGACY = "⏭️ Следующий раунд"
FINISH_BUTTON = "🏁 Завершить"
FINISH_BUTTON_LEGACY = "🏁 Завершить поединок"

MENU_TEXTS = {
    START_BUTTON,
    START_BUTTON_LEGACY,
    CUSTOM_SCENARIO_BUTTON,
    SCENARIOS_BUTTON,
    RESULTS_BUTTON,
    RESULTS_BUTTON_LEGACY,
    RESULTS_BUTTON_LEGACY_2,
    RULES_BUTTON,
    RULES_BUTTON_LEGACY,
    TURN_BUTTON,
    TURN_BUTTON_LEGACY,
    TURN_BUTTON_LEGACY_2,
    TURN_BUTTON_LEGACY_3,
    END_ROUND_BUTTON,
    NEXT_ROUND_BUTTON,
    NEXT_ROUND_BUTTON_LEGACY,
    FINISH_BUTTON,
    FINISH_BUTTON_LEGACY,
}

# Пользовательские сценарии: после нажатия кнопки ждём одно следующее сообщение
PENDING_CUSTOM_SCENARIO_USERS: set[int] = set()
ACTION_IN_PROGRESS_USERS: set[int] = set()


def _timer_hint(seconds: int) -> str:
    if seconds % 60 == 0:
        minutes = seconds // 60
        unit = "минута" if minutes == 1 else "минуты" if minutes in {2, 3, 4} else "минут"
        return f"⏱ На раунд: {minutes} {unit}."
    return f"⏱ На раунд: {seconds} сек."


def _format_final_verdict(judge_service: JudgeService, verdicts: list, final_verdict: str) -> str:
    lines: list[str] = [
        "<b>Поединок завершён</b>",
    ]

    if final_verdict:
        lines.extend(["", escape(final_verdict)])

    if verdicts:
        lines.append("\n<b>Мнение судей</b>")
        labels = JudgeService.JUDGE_LABELS
        for v in verdicts:
            label = labels.get(v.judge_type, v.judge_type)
            lines.append(f"• <b>{escape(label.title())}</b>: {escape(v.comment)}")

    return "\n".join(lines)


async def _send_scenario_picker(message: Message) -> None:
    async with db_session.AsyncSessionLocal() as session:
        scenarios = await ScenarioService().list_active(session)

    if not scenarios:
        await message.answer("Сценариев пока нет. Добавьте их в базу и попробуйте снова.")
        return

    await message.answer("<b>Выберите готовый сценарий для поединка</b>", parse_mode="HTML")

    for item in scenarios[:10]:
        parts = [
            f"<b>{escape(item.title)}</b>",
            escape(item.description),
        ]
        roles_line = f"{escape(item.role_a_name)} ↔ {escape(item.role_b_name)}"
        if len(roles_line) <= 80:
            parts.append(f"Роли: {roles_line}")

        markup = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Начать сценарий", callback_data=f"start_scenario:{item.code}")]]
        )
        await message.answer("\n".join(parts), parse_mode="HTML", reply_markup=markup)


@router.message(F.text == SCENARIOS_BUTTON)
async def show_scenarios(message: Message) -> None:
    await _send_scenario_picker(message)


async def _start_duel(message: Message, scenario_code: str | None = None) -> None:
    async with db_session.AsyncSessionLocal() as session:
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
            "1. Просто отправьте текст или голосовое сообщение.",
            "2. Дождитесь ответа соперника.",
            "3. Когда раунд завершён, нажмите «Завершить раунд».",
        ]
    )
    await message.answer(text, parse_mode="HTML")


async def _build_custom_scenario_from_text(raw_text: str) -> dict:
    clean = raw_text.strip()
    llm = LLMService()
    system_prompt = (
        "Ты — аналитический ассистент по разбору конфликтных и управленческих ситуаций.\n\n"
        "На вход тебе поступает текст, полученный из голосового сообщения (возможны ошибки распознавания, обрывки фраз, разговорная речь, лишние слова).\n\n"
        "Твоя задача — восстановить смысл ситуации и преобразовать её в сценарий управленческого поединка.\n\n"
        "Всегда возвращай ТОЛЬКО один JSON-объект без пояснений до или после, без markdown и без лишнего текста.\n\n"
        "Структура JSON строго такая:\n"
        "{\n"
        "  \"title\": string,\n"
        "  \"description\": string,\n"
        "  \"role_a_name\": string,\n"
        "  \"role_a_goal\": string,\n"
        "  \"role_b_name\": string,\n"
        "  \"role_b_goal\": string,\n"
        "  \"opening_line_a\": string,\n"
        "  \"opening_line_b\": string\n"
        "}\n\n"
        "⚙️ Правила обработки\n"
        "1. Нормализация текста\n"
        " • Исправь очевидные ошибки распознавания (ASR), если они мешают пониманию\n"
        " • Убери паразитные слова и повторы\n"
        " • Восстанови логическую последовательность событий\n"
        "2. Определение сторон\n"
        " • role_a_name — сторона, которая инициирует конфликт (обычно клиент / заявитель)\n"
        " • role_b_name — сторона, к которой предъявляется претензия (исполнитель / менеджер / сервис)\n"
        " • Названия ролей — короткие и конкретные (2–4 слова)\n"
        "3. Цели сторон\n"
        " • role_a_goal — конкретное требование или интерес (например: \"получить компенсацию за задержку\")\n"
        " • role_b_goal — защитная или управленческая цель (например: \"избежать компенсации и сохранить клиента\")\n"
        " • Формулируй чётко, без абстракций\n"
        "4. Название (title)\n"
        " • Краткое (до ~8 слов), отражает суть конфликта\n"
        "5. Описание (description)\n"
        " • 1–3 предложения, только факты ситуации, без оценок и эмоций\n"
        "6. Реплики (диалог)\n"
        " • opening_line_b — первая реакция стороны B (исполнителя), 1–2 предложения, без агрессии, но с попыткой оправдаться или объяснить\n"
        " • opening_line_a — ответ стороны A на позицию B, 1–2 предложения, усиливает конфликт или давление\n"
        "7. Ограничения\n"
        " • Не выдумывай факты, которых нет — допускается разумное обобщение\n"
        " • Не используй канцелярит\n"
        " • Не добавляй ничего вне JSON\n"
        " • Все поля должны быть заполнены."
    )
    user_prompt = (
        "Пользователь описал ситуацию для управленческого поединка.\n"
        "Текст получен из голосового сообщения и может содержать ошибки.\n\n"
        "Проанализируй описание, восстанови смысл и заполни JSON строго в указанной структуре.\n\n"
        f"Описание пользователя:\n{clean}"
    )

    raw = await llm.generate_text(system_prompt=system_prompt, user_prompt=user_prompt, temperature=0.3)
    data = json.loads(raw)

    def _get(key: str, default: str = "") -> str:
        value = data.get(key, default) or default
        return str(value).strip()

    return {
        "title": _get("title", "Свободный поединок"),
        "description": _get("description", clean),
        "role_a_name": _get("role_a_name", "Сторона A"),
        "role_a_goal": _get("role_a_goal", ""),
        "role_b_name": _get("role_b_name", "Сторона B"),
        "role_b_goal": _get("role_b_goal", ""),
        "opening_line_a": _get("opening_line_a", ""),
        "opening_line_b": _get("opening_line_b", ""),
    }


async def _start_custom_duel(message: Message, user_text: str) -> None:
    clean_text = user_text.strip()
    if not clean_text:
        await message.answer(
            "Не получилось прочитать описание ситуации. Попробуйте ещё раз, "
            "пару предложений: кто вы, кто вторая сторона и о чём спор."
        )
        return

    async with db_session.AsyncSessionLocal() as session:
        duel_service = DuelService()

        try:
            payload = await _build_custom_scenario_from_text(clean_text)
        except Exception:
            await message.answer(
                "Я не смог оформить эту ситуацию в сценарий. Попробуйте описать её чуть конкретнее: "
                "кто вы, кто вторая сторона и что именно хотите отработать.\n\n"
                "Просто ответьте следующим сообщением — кнопку «🎭 Свой сценарий» нажимать ещё раз не нужно."
            )
            return

        scenario = Scenario(
            code=f"custom_{message.from_user.id}_{int(time())}",
            title=payload["title"],
            description=payload["description"],
            category="custom",
            difficulty="normal",
            role_a_name=payload["role_a_name"],
            role_a_goal=payload["role_a_goal"],
            role_b_name=payload["role_b_name"],
            role_b_goal=payload["role_b_goal"],
            opening_line_a=payload["opening_line_a"] or "",
            opening_line_b=payload["opening_line_b"] or "",
            is_active=True,
        )
        session.add(scenario)
        await session.flush()

        duel = await duel_service.create_duel(session, telegram_user_id=message.from_user.id, scenario=scenario)
        rounds = await duel_service.get_duel_rounds(session, duel.id)

    round_1 = rounds[0]
    text = "\n".join(
        [
            f"<b>Поединок #{duel.id}</b>",
            f"🎭 <b>Своя ситуация:</b> {escape(scenario.title)}",
            escape(scenario.description),
            _timer_hint(duel.turn_time_limit_sec),
            f"Роли:\n• Вы: <b>{escape(round_1.user_role)}</b>\n• Соперник (AI): <b>{escape(round_1.ai_role)}</b>",
            "",
            "<b>Первая реплика соперника (AI)</b>",
            escape(round_1.opening_line),
            "",
            "<b>Что дальше</b>",
            "1. Ответьте текстом или голосовым от лица вашей роли.",
            "2. Дождитесь ответа соперника.",
            "3. Когда раунд завершён, нажмите «Завершить раунд».",
        ]
    )
    # Успешно стартовали пользовательский сценарий — выходим из режима ожидания описания
    if message.from_user:
        PENDING_CUSTOM_SCENARIO_USERS.discard(message.from_user.id)

    await message.answer(text, parse_mode="HTML")


async def _run_turn(message: Message, user_text: str, *, recognized_from_voice: bool = False) -> None:
    clean_text = user_text.strip()
    if not clean_text:
        await message.answer("Не получилось прочитать реплику. Попробуйте ещё раз.")
        return

    async with db_session.AsyncSessionLocal() as session:
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
        await session.commit()

        seconds_left = duel_service.get_seconds_left(duel, round_obj)
        if seconds_left is not None and seconds_left > 0:
            round_timer_service.schedule(
                chat_id=message.chat.id,
                duel_id=duel.id,
                round_number=round_obj.round_number,
                delay_seconds=seconds_left,
            )

        if duel_service.is_round_expired(duel, round_obj):
            await duel_service.complete_round(duel, round_obj)
            await session.commit()
            if round_obj.round_number == 1:
                await message.answer(f"⏱ Время первого раунда вышло. Нажмите «{END_ROUND_BUTTON}», чтобы завершить раунд и перейти дальше.")
            else:
                await message.answer(f"⏱ Время второго раунда вышло. Нажмите «{END_ROUND_BUTTON}», чтобы завершить раунд и получить итог.")
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
        seconds_left = duel_service.get_seconds_left(duel, round_obj)

        await duel_service.add_message(
            session,
            duel_id=duel.id,
            round_number=round_obj.round_number,
            author="ai",
            content=ai_reply,
        )
        await session.commit()

    timer_line = f"⏱ До конца раунда: {seconds_left or 0} сек."

    if recognized_from_voice:
        await message.answer(
            "<b>Ваша реплика</b>\n"
            f"{escape(clean_text)}\n\n"
            "<b>Ответ соперника</b>\n"
            f"{escape(ai_reply)}\n\n"
            f"{escape(timer_line)}",
            parse_mode="HTML",
        )
        return

    await message.answer(f"{ai_reply}\n\n{timer_line}")


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
    await _send_scenario_picker(message)


@router.callback_query(F.data.startswith("start_scenario:"))
async def start_duel_from_scenario_button(callback: CallbackQuery) -> None:
    scenario_code = callback.data.split(":", 1)[1]
    await callback.answer()
    await _start_duel(callback.message, scenario_code=scenario_code)


@router.message(F.text == RANDOM_SCENARIO_BUTTON)
async def start_random_scenario_from_menu(message: Message) -> None:
    # Используем стандартный старт дуэли без кода сценария — он уже выбирает случайный активный сценарий.
    await _start_duel(message)


@router.message(F.text == CUSTOM_SCENARIO_BUTTON)
async def start_custom_scenario_prompt(message: Message) -> None:
    PENDING_CUSTOM_SCENARIO_USERS.add(message.from_user.id)
    await message.answer(
        "Опишите голосом или текстом ситуацию, роли и что хотите отработать. "
        "Можно парой абзацев, без строгого формата."
    )


@router.message(F.text.regexp(r"^[a-z_]+$") & ~F.text.in_(MENU_TEXTS))
async def start_duel_by_scenario_code(message: Message) -> None:
    await _start_duel(message, scenario_code=message.text.strip())


@router.message(F.text.in_({TURN_BUTTON, TURN_BUTTON_LEGACY, TURN_BUTTON_LEGACY_2, TURN_BUTTON_LEGACY_3}))
async def make_turn_prompt(message: Message) -> None:
    await message.answer("Пришлите следующим сообщением текст или голосовое. Я распознаю сообщение и отвечу от лица соперника.")


@router.message(F.text.in_({END_ROUND_BUTTON, NEXT_ROUND_BUTTON, NEXT_ROUND_BUTTON_LEGACY, FINISH_BUTTON, FINISH_BUTTON_LEGACY}))
async def end_round_or_finish_duel(message: Message) -> None:
    user_id = message.from_user.id
    if user_id in ACTION_IN_PROGRESS_USERS:
        await message.answer("Действие уже выполняется. Подождите пару секунд.")
        return

    ACTION_IN_PROGRESS_USERS.add(user_id)
    try:
        async with db_session.AsyncSessionLocal() as session:
            duel_service = DuelService()
            duel = await duel_service.get_latest_duel_for_user(session, telegram_user_id=user_id)
            if duel is None:
                await message.answer(f"Сейчас у вас нет активного поединка. Нажмите «{START_BUTTON}».")
                return

            round_1 = await duel_service.get_round(session, duel.id, 1)
            round_2 = await duel_service.get_round(session, duel.id, 2)
            if round_1 is None or round_2 is None:
                await message.answer("Не смог найти раунды этого поединка.")
                return

            if duel.status == "finished" or round_2.status == "finished":
                await message.answer("Действие уже выполнено: поединок завершён.")
                return

            if duel.current_round_number == 1 and round_2.status == "pending":
                if round_1.status != "finished":
                    await duel_service.complete_round(duel, round_1)
                await session.commit()

                text = "\n".join(
                    [
                        "<b>Раунд 1 завершён</b>",
                        "Переходим ко второму раунду со сменой ролей.",
                        _timer_hint(duel.turn_time_limit_sec),
                        f"Теперь вы — <b>{escape(round_2.user_role)}</b>, оппонент (AI) — <b>{escape(round_2.ai_role)}</b>.",
                        "",
                        "<b>Первая реплика оппонента (AI)</b>",
                        escape(round_2.opening_line),
                    ]
                )
                await message.answer(text, parse_mode="HTML")
                return

            if duel.current_round_number == 2 or round_2.status == "in_progress":
                await _finish_duel_from_menu(message)
                return

            await message.answer("Действие уже выполнено или сейчас недоступно.")
    finally:
        ACTION_IN_PROGRESS_USERS.discard(user_id)


async def _finish_duel_from_menu(message: Message) -> None:
    async with db_session.AsyncSessionLocal() as session:
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
        formatted = _format_final_verdict(judge_service, verdicts, final_verdict)
        await duel_service.finish_duel(duel, final_verdict)
        await session.commit()

    await message.answer(formatted, parse_mode="HTML")


@router.message(F.text.in_({RESULTS_BUTTON, RESULTS_BUTTON_LEGACY, RESULTS_BUTTON_LEGACY_2}))
async def my_results(message: Message) -> None:
    async with db_session.AsyncSessionLocal() as session:
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
        lines.append("\n<b>Мнение судей</b>")
        judge_labels = JudgeService.JUDGE_LABELS
        for item in judge_results:
            label = judge_labels.get(item.judge_type, item.judge_type)
            lines.append(f"• <b>{escape(label.title())}:</b> {escape(item.comment)}")
    if duel.final_verdict:
        lines.append(f"\n<b>Краткий итог</b>\n{escape(duel.final_verdict.splitlines()[0])}")

    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(F.text.in_({RULES_BUTTON, RULES_BUTTON_LEGACY, SCENARIOS_BUTTON}))
async def how_it_works(message: Message) -> None:
    async with db_session.AsyncSessionLocal() as session:
        scenarios = await ScenarioService().list_active(session)

    scenario_lines: list[str] = []
    for item in scenarios:
        scenario_lines.append(
            "\n".join(
                [
                    f"• <b>{escape(item.title)}</b>",
                    f"Код: <code>{escape(item.code)}</code>",
                    f"Роли: {escape(item.role_a_name)} ↔ {escape(item.role_b_name)}",
                ]
            )
        )

    scenarios_block = "\n\n".join(scenario_lines) if scenario_lines else "Сценарии пока не добавлены."

    await message.answer(
        "<b>ℹ️ Справка</b>\n\n"
        "<b>Как проходит поединок</b>\n"
        "• Поединок состоит из двух раундов.\n"
        "• Во втором раунде роли меняются.\n"
        "• После завершения три судьи дают итоговый разбор.\n\n"
        "<b>Как действовать</b>\n"
        f"1. Нажмите <b>«{escape(START_BUTTON)}»</b>.\n"
        "2. Просто отправляйте реплики текстом или голосом.\n"
        f"3. В конце каждого раунда нажимайте <b>«{escape(END_ROUND_BUTTON)}»</b>.\n"
        "4. После первого нажатия начнётся второй раунд, после второго — завершится поединок.\n\n"
        "<b>Сценарии</b>\n"
        f"{scenarios_block}\n\n"
        "<b>Обратная связь</b>\n"
        "Если хотите оставить отзыв или предложить улучшение, начните сообщение с фразы <code>Обратная связь</code>.\n\n"
        "<b>Поддержать проект</b>\n"
        "<a href=\"https://t.me/tribute/app?startapp=dHaW\">Отблагодарить автора</a>",
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

    # === ЕДИНЫЙ ВХОД В DUEL-FLOW ===
    # Активный duel проверяется ПЕРВЫМ — это абсолютный приоритет
    async with db_session.AsyncSessionLocal() as session:
        duel_service = DuelService()
        duel = await duel_service.get_latest_duel_for_user(session, telegram_user_id=message.from_user.id)
        has_active_duel = duel is not None and duel.status not in ("finished", "cancelled")

    if has_active_duel:
        # Голосовое в активном duel → продолжаем текущий раунд
        # Игнорируем PENDING_CUSTOM_SCENARIO_USERS полностью
        await _run_turn(message, transcript, recognized_from_voice=True)
        return

    # Нет активного duel — проверяем pending custom scenario
    if message.from_user and message.from_user.id in PENDING_CUSTOM_SCENARIO_USERS:
        await _start_custom_duel(message, transcript)
        return

    # Голосовое без контекста — подсказка
    await message.answer("Сейчас у вас нет активного поединка. Нажмите «🎯 Выбрать сценарий» для старта.")


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

    # === ЕДИНЫЙ ВХОД В DUEL-FLOW ===
    # Активный duel проверяется ПЕРВЫМ — это абсолютный приоритет
    async with db_session.AsyncSessionLocal() as session:
        duel_service = DuelService()
        duel = await duel_service.get_latest_duel_for_user(session, telegram_user_id=message.from_user.id)
        has_active_duel = duel is not None and duel.status not in ("finished", "cancelled")

    if has_active_duel:
        # Аудио в активном duel → продолжаем текущий раунд
        # Игнорируем PENDING_CUSTOM_SCENARIO_USERS полностью
        await _run_turn(message, transcript, recognized_from_voice=True)
        return

    # Нет активного duel — проверяем pending custom scenario
    if message.from_user and message.from_user.id in PENDING_CUSTOM_SCENARIO_USERS:
        await _start_custom_duel(message, transcript)
        return

    # Аудио без контекста — подсказка
    await message.answer("Сейчас у вас нет активного поединка. Нажмите «🎯 Выбрать сценарий» для старта.")


@router.message(F.text & ~F.text.in_(MENU_TEXTS))
async def process_turn(message: Message) -> None:
    # Если ждём описание пользовательского сценария — используем текст как исходник
    if message.from_user and message.from_user.id in PENDING_CUSTOM_SCENARIO_USERS:
        await _start_custom_duel(message, message.text)
        return

    await _run_turn(message, message.text)

