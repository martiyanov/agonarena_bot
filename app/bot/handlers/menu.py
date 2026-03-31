from __future__ import annotations

import json
import logging
import random
import tempfile
from html import escape
from pathlib import Path
from time import time
from typing import Union

from aiogram import F, Router

logger = logging.getLogger(__name__)
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

START_BUTTON = "🎯 Сценарии"
RANDOM_SCENARIO_BUTTON = "🎲 Случайный"
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
FEEDBACK_BUTTON = "💬 Отзыв"

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
    FEEDBACK_BUTTON,
}

# Пользовательские сценарии: после нажатия кнопки ждём одно следующее сообщение
PENDING_CUSTOM_SCENARIO_USERS: set[int] = set()
ACTION_IN_PROGRESS_USERS: set[int] = set()
# Отслеживание пользователей, которые нажали кнопку обратной связи
FEEDBACK_REQUEST_USERS: set[int] = set()


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
            
            # Add round-specific comments if available
            if hasattr(v, 'round1_comment') and v.round1_comment:
                lines.append(f"  Раунд 1: {escape(v.round1_comment)}")
            if hasattr(v, 'round2_comment') and v.round2_comment:
                lines.append(f"  Раунд 2: {escape(v.round2_comment)}")

    return "\n".join(lines)


async def _send_scenario_picker(message: Message) -> None:
    async with db_session.AsyncSessionLocal() as session:
        scenarios = await ScenarioService().list_active(session)

    if not scenarios:
        await message.answer("Сценариев пока нет. Добавьте их в базу и попробуйте снова.")
        return

    # Pagination: 5 scenarios per page
    PAGE_SIZE = 5
    page = 1  # Default to first page
    
    # Calculate total pages
    total_pages = (len(scenarios) + PAGE_SIZE - 1) // PAGE_SIZE
    
    # Get scenarios for current page
    start_idx = (page - 1) * PAGE_SIZE
    end_idx = start_idx + PAGE_SIZE
    page_scenarios = scenarios[start_idx:end_idx]
    
    # Format scenario list for display
    scenario_lines = []
    for i, item in enumerate(page_scenarios, start_idx + 1):
        roles_line = f"{escape(item.role_a_name)} ↔ {escape(item.role_b_name)}"
        difficulty = f" | {item.difficulty}" if item.difficulty else ""
        scenario_lines.append(f"{i}. {escape(item.title)}\n{roles_line}{difficulty}")

    # Form message with scenario list
    scenarios_text = "\n\n".join(scenario_lines)
    
    # Create compact keyboard: 5 scenario buttons + navigation + random + custom
    keyboard_rows = []
    
    # First 5 scenario buttons (numbers only for cleaner UX)
    scenario_buttons = []
    for i, scenario in enumerate(page_scenarios, start_idx + 1):
        scenario_buttons.append(InlineKeyboardButton(text=f"[{i}]", callback_data=f"pick_scenario:{scenario.id}"))
    
    # Add scenario buttons in rows of 5
    for i in range(0, len(scenario_buttons), 5):
        keyboard_rows.append(scenario_buttons[i:i+5])
    
    # Navigation buttons: ← | 1/2 | →
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="←", callback_data=f"scenarios_page:{page-1}"))
    
    nav_buttons.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data=f"scenarios_page:{page}"))
    
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="→", callback_data=f"scenarios_page:{page+1}"))
    
    keyboard_rows.append(nav_buttons)
    
    # Bottom row: 🎲 Случайный, 🎭 Свой сценарий
    bottom_buttons = [
        InlineKeyboardButton(text="🎲 Случайный", callback_data="pick_scenario:random"),
        InlineKeyboardButton(text="🎭 Свой сценарий", callback_data="custom_scenario")
    ]
    keyboard_rows.append(bottom_buttons)
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    
    # Page title based on page number
    if page == 1:
        page_title = "🎯 Выберите сценарий\n\n"
    else:
        page_title = f"Страница {page}\n\n"
    
    await message.answer(
        f"{page_title}{scenarios_text}\n\n", 
        parse_mode="HTML", 
        reply_markup=markup
    )


@router.message(F.text == SCENARIOS_BUTTON)
async def show_scenarios(message: Message) -> None:
    await _send_scenario_picker(message)


async def _start_duel(message: Message, scenario_code: Union[str, None] = None) -> None:
    async with db_session.AsyncSessionLocal() as session:
        duel_service = DuelService()
        
        # Check if user already has an active duel
        existing_duel = await duel_service.get_latest_duel_for_user(
            session, telegram_user_id=message.from_user.id
        )
        if existing_duel and existing_duel.status not in ("finished", "cancelled"):
            from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
            
            # Get duel details
            scenario = await duel_service.get_scenario_by_id(session, existing_duel.scenario_id)
            rounds = await duel_service.get_duel_rounds(session, existing_duel.id)
            current_round = next((r for r in rounds if r.round_number == existing_duel.current_round_number), None)
            
            # Count turns in current round
            messages = await duel_service.list_messages_for_round(
                session, duel_id=existing_duel.id, round_number=existing_duel.current_round_number
            )
            turn_count = len([m for m in messages if m.author == "user"])
            
            # Build duel details text
            scenario_title = escape(scenario.title) if scenario else "Неизвестный сценарий"
            round_info = f"Раунд {existing_duel.current_round_number} из 2"
            role_info = f"Роль: {escape(current_round.user_role) if current_round else 'N/A'}"
            turns_info = f"Сделано ходов: {turn_count}"
            
            reset_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✓ Да, начать новый", callback_data=f"reset_and_start:{existing_duel.id}:{scenario_code or 'random'}")],
                [InlineKeyboardButton(text="✗ Нет, продолжить текущий", callback_data=f"continue_current:{existing_duel.id}")]
            ])
            await message.answer(
                "⚠️ <b>У вас уже есть активный поединок</b>\n\n"
                f"<b>Текущий поединок:</b>\n"
                f"• Сценарий: {scenario_title}\n"
                f"• {round_info}\n"
                f"• {role_info}\n"
                f"• {turns_info}\n\n"
                f"Начать новый поединок с выбранным сценарием?",
                parse_mode="HTML",
                reply_markup=reset_keyboard
            )
            return
        
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
    # Single message with all duel start information
    start_text = "\n".join([
        "🏁 <b>Поединок начался</b>",
        f"Сценарий: {escape(scenario.title)}",
        f"Раунд 1 из 2",
        "",
        f"Вы — {escape(round_1.user_role)}",
        f"Соперник — {escape(round_1.ai_role)}",
        "",
        "Первая реплика соперника:",
        f'"{escape(round_1.opening_line)}"',
        "",
        "Ответьте текстом или голосом от своей роли.",
    ])
    
    # Use the in_duel keyboard for the newly started duel
    from app.bot.keyboards.main_menu import build_main_menu
    markup = build_main_menu(has_active_duel=True)
    
    await message.answer(start_text, parse_mode="HTML", reply_markup=markup)


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

    # Removed timer from turn messages according to UX requirements
    # Keep track of seconds_left for potential use in other parts of the function
    # but don't include it in the response message

    if recognized_from_voice:
        await message.answer(
            "<b>Раунд {round_number}</b>\n\n"
            "Вы — {user_role}:\n"
            '"{user_text}"\n\n'
            "Соперник — {ai_role}:\n"
            '"{ai_reply}"\n\n'
            "Продолжайте раунд:\n"
            "— ответьте текстом или голосом\n"
            "— либо нажмите «🏁 Завершить раунд»".format(
                round_number=round_obj.round_number,
                user_role=escape(round_obj.user_role),
                user_text=escape(clean_text),
                ai_role=escape(round_obj.ai_role),
                ai_reply=escape(ai_reply)
            ),
            parse_mode="HTML",
        )
        return

    await message.answer(
        "<b>Раунд {round_number}</b>\n\n"
        "Вы — {user_role}:\n"
        '"{user_text}"\n\n'
        "Соперник — {ai_role}:\n"
        '"{ai_reply}"\n\n'
        "Продолжайте раунд:\n"
        "— ответьте текстом или голосом\n"
        "— либо нажмите «🏁 Завершить раунд»".format(
            round_number=round_obj.round_number,
            user_role=escape(round_obj.user_role),
            user_text=escape(clean_text),
            ai_role=escape(round_obj.ai_role),
            ai_reply=escape(ai_reply)
        ),
        parse_mode="HTML",
    )


async def _send_feedback_to_owner(message: Message, feedback_text: str) -> None:
    """Send feedback message to the bot owner"""
    # Get the owner user ID from environment variable
    import os
    owner_user_id = os.getenv("FEEDBACK_OWNER_USER_ID")
    
    if not owner_user_id:
        # If no owner ID is configured, send a message to the user
        await message.answer(
            "⚠️ К сожалению, я не могу отправить вашу обратную связь, "
            "так как не настроен ID владельца бота."
        )
        return
    
    try:
        owner_user_id = int(owner_user_id)
        
        # Format the feedback message with user info
        user_info = f"Пользователь: {message.from_user.full_name} (@{message.from_user.username or 'не указан'})\nID: {message.from_user.id}\n\n"
        feedback_content = f"💬 Обратная связь:\n\n{feedback_text}"
        full_message = user_info + feedback_content
        
        # Use the message tool to send the feedback to the owner
        import asyncio
        # We need to use the message tool to send to the owner
        # Since we're in a subagent context, we'll send the message via the message tool
        from openclaw.tool_client import ToolClient
        client = ToolClient()
        await client.call_tool("message", {
            "action": "send",
            "target": str(owner_user_id),
            "message": full_message
        })
        
        # Confirm to the user that feedback was sent
        await message.answer("✅ Ваша обратная связь успешно отправлена владельцу бота!")
        
    except ValueError:
        await message.answer(
            "⚠️ Ошибка: некорректный ID владельца бота в настройках."
        )
    except Exception as e:
        await message.answer(
            f"❌ Не удалось отправить обратную связь: {str(e)}"
        )


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
async def handle_start_button(message: Message) -> None:
    # Кнопка "🎯 Сценарии" должна показывать выбор сценариев, а не главное меню
    await _send_scenario_picker(message)

@router.callback_query(F.data == "start_duel")
async def start_duel_from_menu(callback: CallbackQuery) -> None:
    await callback.answer(text="OK")
    await _send_scenario_picker(callback.message)


@router.callback_query(F.data.startswith("start_scenario:"))
async def start_duel_from_scenario_button(callback: CallbackQuery) -> None:
    scenario_code = callback.data.split(":", 1)[1]
    await callback.answer(text="OK")
    await _start_duel(callback.message, scenario_code=scenario_code)


@router.callback_query(F.data.startswith("pick_scenario:"))
async def start_duel_from_pick_scenario(callback: CallbackQuery) -> None:
    scenario_selector = callback.data.split(":", 1)[1]
    await callback.answer(text="OK")
    
    # Если выбран случайный сценарий
    if scenario_selector == "random":
        await _start_duel(callback.message)
        return
    
    # Если выбран ID сценария
    try:
        scenario_id = int(scenario_selector)
        async with db_session.AsyncSessionLocal() as session:
            scenario = await DuelService().get_scenario_by_id(session, scenario_id)
            if scenario and scenario.is_active:
                await _start_duel(callback.message, scenario_code=scenario.code)
            else:
                await callback.message.answer("Выбранный сценарий больше не доступен.")
    except ValueError:
        await callback.message.answer("Ошибка при выборе сценария.")


@router.callback_query(F.data.startswith("scenarios_page:"))
async def show_scenarios_page(callback: CallbackQuery) -> None:
    try:
        page_num = int(callback.data.split(":", 1)[1])
        await callback.answer(text="OK")
        
        async with db_session.AsyncSessionLocal() as session:
            scenarios = await ScenarioService().list_active(session)

        if not scenarios:
            await callback.message.edit_text("Сценариев пока нет. Добавьте их в базу и попробуйте снова.")
            return

        # Pagination: 5 scenarios per page
        PAGE_SIZE = 5
        total_pages = (len(scenarios) + PAGE_SIZE - 1) // PAGE_SIZE
        
        # Ensure page number is valid
        if page_num < 1:
            page_num = 1
        elif page_num > total_pages:
            page_num = total_pages
            
        # Get scenarios for current page
        start_idx = (page_num - 1) * PAGE_SIZE
        end_idx = start_idx + PAGE_SIZE
        page_scenarios = scenarios[start_idx:end_idx]
        
        # Format scenario list for display
        scenario_lines = []
        for i, item in enumerate(page_scenarios, start_idx + 1):
            roles_line = f"{escape(item.role_a_name)} ↔ {escape(item.role_b_name)}"
            difficulty = f" | {item.difficulty}" if item.difficulty else ""
            scenario_lines.append(f"{i}. {escape(item.title)}\n{roles_line}{difficulty}")

        # Form message with scenario list
        scenarios_text = "\n\n".join(scenario_lines)
        
        # Create compact keyboard: 5 scenario buttons + navigation + random + custom
        keyboard_rows = []
        
        # First 5 scenario buttons (numbers only for cleaner UX)
        scenario_buttons = []
        for i, scenario in enumerate(page_scenarios, start_idx + 1):
            scenario_buttons.append(InlineKeyboardButton(text=f"[{i}]", callback_data=f"pick_scenario:{scenario.id}"))
        
        # Add scenario buttons in rows of 5
        for i in range(0, len(scenario_buttons), 5):
            keyboard_rows.append(scenario_buttons[i:i+5])
        
        # Navigation buttons: ← | 1/2 | →
        nav_buttons = []
        if page_num > 1:
            nav_buttons.append(InlineKeyboardButton(text="←", callback_data=f"scenarios_page:{page_num-1}"))
        
        nav_buttons.append(InlineKeyboardButton(text=f"{page_num}/{total_pages}", callback_data=f"scenarios_page:{page_num}"))
        
        if page_num < total_pages:
            nav_buttons.append(InlineKeyboardButton(text="→", callback_data=f"scenarios_page:{page_num+1}"))
        
        keyboard_rows.append(nav_buttons)
        
        # Bottom row: 🎲 Случайный, 🎭 Свой сценарий
        bottom_buttons = [
            InlineKeyboardButton(text="🎲 Случайный", callback_data="pick_scenario:random"),
            InlineKeyboardButton(text="🎭 Свой сценарий", callback_data="custom_scenario")
        ]
        keyboard_rows.append(bottom_buttons)
        
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
        
        # Page title based on page number
        if page_num == 1:
            page_title = "🎯 Выберите сценарий\n\n"
        else:
            page_title = f"Страница {page_num}\n\n"
        
        await callback.message.edit_text(
            f"{page_title}{scenarios_text}\n\n", 
            parse_mode="HTML", 
            reply_markup=markup
        )
    except ValueError:
        await callback.message.answer("Ошибка при переключении страницы.")


@router.callback_query(F.data == "custom_scenario")
async def start_custom_scenario_from_picker(callback: CallbackQuery) -> None:
    await callback.answer(text="OK")
    await start_custom_scenario_prompt(callback.message)


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
async def handle_end_round_button(message: Message) -> None:
    await _process_end_round(message)

@router.callback_query(F.data == "end_round")
async def end_round_or_finish_duel(callback: CallbackQuery) -> None:
    await callback.answer(text="OK")
    await _process_end_round(callback.message)

@router.callback_query(F.data.startswith("duel:v1:end:"))
async def end_round_v1_callback(callback: CallbackQuery) -> None:
    """Handle new inline button format: duel:v1:end:{duel_id}:{round_no}"""
    try:
        # Parse callback data
        parts = callback.data.split(":")
        if len(parts) != 5:
            await callback.answer(text="⚠️ Ошибка: неверный формат кнопки")
            logger.warning(f"Invalid callback format: {callback.data}")
            return
        
        duel_id = int(parts[3])
        round_no = int(parts[4])
        
        # Verify duel exists and belongs to user
        async with db_session.AsyncSessionLocal() as session:
            duel_service = DuelService()
            duel = await duel_service.get_duel(session, duel_id)
            
            if duel is None:
                await callback.answer(text="⚠️ Поединок не найден")
                await callback.message.edit_text(
                    "⚠️ <b>Поединок устарел</b>\n\nЭтот поединок больше не существует.",
                    parse_mode="HTML"
                )
                return
            
            if duel.user_telegram_id != callback.from_user.id:
                await callback.answer(text="⚠️ Это не ваш поединок")
                return
            
            if duel.status == "finished":
                await callback.answer(text="✅ Поединок уже завершён")
                return
        
        # Show processing feedback
        await callback.answer(text="⏳ Завершаю раунд...")
        await _process_end_round(callback.message)
        
    except ValueError as e:
        await callback.answer(text="⚠️ Ошибка данных")
        logger.error(f"ValueError in end_round_v1_callback: {e}")
    except Exception as e:
        await callback.answer(text="⚠️ Произошла ошибка")
        logger.exception(f"Error in end_round_v1_callback: {e}")

@router.callback_query(F.data == "continue_duel")
async def continue_duel_callback(callback: CallbackQuery) -> None:
    """Handle continue duel button from /start"""
    await callback.answer(text="▶️ Продолжаем")
    await callback.message.delete()
    
    # Show current duel status
    async with db_session.AsyncSessionLocal() as session:
        duel_service = DuelService()
        duel = await duel_service.get_latest_duel_for_user(
            session, telegram_user_id=callback.from_user.id
        )
        
        if duel and duel.status not in ("finished", "cancelled"):
            await callback.message.answer(
                f"🎮 <b>Поединок #{duel.id}</b>\n"
                f"Статус: <i>{duel.status}</i>\n\n"
                f"Отправьте сообщение или голосовое, чтобы сделать ход.",
                parse_mode="HTML"
            )
        else:
            await show_main_menu(callback.message)

@router.callback_query(F.data == "reset_and_new")
async def reset_and_new_callback(callback: CallbackQuery) -> None:
    """Handle reset and new duel button"""
    await callback.answer(text="🗑 Сбрасываю")
    
    async with db_session.AsyncSessionLocal() as session:
        duel_service = DuelService()
        duel = await duel_service.get_latest_duel_for_user(
            session, telegram_user_id=callback.from_user.id
        )
        
        if duel and duel.status not in ("finished", "cancelled"):
            duel.status = "finished"
            await session.commit()
    
    await callback.message.edit_text(
        "✅ <b>Поединок сброшен</b>\n\nВыберите сценарий для нового поединка:",
        parse_mode="HTML"
    )
    await _send_scenario_picker(callback.message)


@router.callback_query(F.data.startswith("reset_and_start:"))
async def reset_and_start_duel(callback: CallbackQuery) -> None:
    """Handle reset and start new duel with selected scenario"""
    try:
        parts = callback.data.split(":")
        if len(parts) != 3:
            await callback.answer(text="⚠️ Ошибка: неверный формат данных")
            return
        
        duel_id = int(parts[1])
        scenario_code = parts[2]
    except (ValueError, IndexError):
        await callback.answer(text="⚠️ Ошибка: неверные данные")
        return
    
    await callback.answer(text="🗑 Сбрасываю и начинаю новый...")
    
    async with db_session.AsyncSessionLocal() as session:
        duel_service = DuelService()
        
        # Reset old duel
        duel = await duel_service.get_duel(session, duel_id)
        if duel and duel.status not in ("finished", "cancelled"):
            duel.status = "finished"
            await session.commit()
    
    # Delete the confirmation message
    await callback.message.delete()
    
    # Start new duel with selected scenario
    if scenario_code == "random":
        await _start_duel(callback.message)
    else:
        await _start_duel(callback.message, scenario_code=scenario_code)


@router.callback_query(F.data.startswith("continue_current:"))
async def continue_current_duel(callback: CallbackQuery) -> None:
    """Handle continue current duel button - show duel state"""
    try:
        duel_id = int(callback.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer(text="⚠️ Ошибка: неверный ID поединка")
        return
    
    await callback.answer(text="▶️ Продолжаем")
    await callback.message.delete()
    
    # Show current duel status
    async with db_session.AsyncSessionLocal() as session:
        duel_service = DuelService()
        duel = await duel_service.get_duel(session, duel_id)
        
        if not duel or duel.status in ("finished", "cancelled"):
            await callback.message.answer(
                "⚠️ <b>Поединок не найден или уже завершён</b>",
                parse_mode="HTML"
            )
            return
        
        # Get duel details
        scenario = await duel_service.get_scenario_by_id(session, duel.scenario_id)
        rounds = await duel_service.get_duel_rounds(session, duel.id)
        current_round = next((r for r in rounds if r.round_number == duel.current_round_number), None)
        
        # Count turns in current round
        messages = await duel_service.list_messages_for_round(
            session, duel_id=duel.id, round_number=duel.current_round_number
        )
        turn_count = len([m for m in messages if m.author == "user"])
        
        scenario_title = escape(scenario.title) if scenario else "Неизвестный сценарий"
        
        status_text = (
            f"🎮 <b>Поединок #{duel.id}</b>\n\n"
            f"<b>Сценарий:</b> {scenario_title}\n"
            f"<b>Раунд:</b> {duel.current_round_number} из 2\n"
            f"<b>Ваша роль:</b> {escape(current_round.user_role) if current_round else 'N/A'}\n"
            f"<b>Сделано ходов:</b> {turn_count}\n\n"
            f"Отправьте сообщение или голосовое, чтобы сделать ход."
        )
        
        await callback.message.answer(status_text, parse_mode="HTML")

@router.callback_query(F.data.startswith("reset_duel:"))
async def reset_duel_callback(callback: CallbackQuery) -> None:
    """Handle duel reset button"""
    try:
        duel_id = int(callback.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer(text="Ошибка: неверный ID поединка")
        return
    
    async with db_session.AsyncSessionLocal() as session:
        duel_service = DuelService()
        duel = await duel_service.get_duel(session, duel_id)
        
        if duel is None:
            await callback.answer(text="Поединок не найден")
            await callback.message.edit_text(
                "⚠️ Поединок уже удалён или не существует.",
                reply_markup=None
            )
            return
        
        # Verify ownership
        if duel.user_telegram_id != callback.from_user.id:
            await callback.answer(text="Вы не можете сбросить чужой поединок")
            return
        
        # Mark as finished
        if duel.status not in ("finished", "cancelled"):
            duel.status = "finished"
            await session.commit()
        
        await callback.answer(text="Поединок сброшен")
        await callback.message.edit_text(
            "✅ <b>Поединок сброшен</b>\n\nТеперь вы можете начать новый поединок.",
            parse_mode="HTML",
            reply_markup=None
        )

@router.callback_query(F.data == "back_to_menu")
async def back_to_menu_callback(callback: CallbackQuery) -> None:
    """Handle back to menu button"""
    await callback.answer(text="OK")
    await callback.message.delete()
    await show_main_menu(callback.message)

async def _process_end_round(target_message: Message) -> None:
    user_id = target_message.from_user.id
    if user_id in ACTION_IN_PROGRESS_USERS:
        await target_message.answer("Действие уже выполняется. Подождите пару секунд.")
        return

    ACTION_IN_PROGRESS_USERS.add(user_id)
    try:
        async with db_session.AsyncSessionLocal() as session:
            duel_service = DuelService()
            duel = await duel_service.get_latest_duel_for_user(session, telegram_user_id=user_id)
            if duel is None:
                await target_message.answer(f"Сейчас у вас нет активного поединка. Нажмите «{START_BUTTON}».")
                return

            round_1 = await duel_service.get_round(session, duel.id, 1)
            round_2 = await duel_service.get_round(session, duel.id, 2)
            if round_1 is None or round_2 is None:
                await target_message.answer(
                    "⚠️ <b>Поединок устарел или повреждён</b>\n\n"
                    "Данные поединка не найдены. Начните новый поединок.",
                    parse_mode="HTML"
                )
                # Mark duel as finished to prevent further issues
                if duel and duel.status != "finished":
                    duel.status = "finished"
                    await session.commit()
                return

            if duel.status == "finished" or round_2.status == "finished":
                await target_message.answer("Действие уже выполнено: поединок завершён.")
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
                await target_message.answer(text, parse_mode="HTML")
                return

            if duel.current_round_number == 2 or round_2.status == "in_progress":
                await _finish_duel_from_menu(target_message)
                return

            await target_message.answer("Действие уже выполнено или сейчас недоступно.")
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
async def handle_results_button(message: Message) -> None:
    await _show_results(message)

@router.callback_query(F.data == "results")
async def my_results(callback: CallbackQuery) -> None:
    await callback.answer(text="OK")
    await _show_results(callback.message)

async def _show_results(target_message: Message) -> None:
    async with db_session.AsyncSessionLocal() as session:
        duel_service = DuelService()
        duel = await duel_service.get_latest_duel_for_user(session, telegram_user_id=target_message.from_user.id)
        if duel is None:
            await target_message.answer("Пока нет сохранённых результатов.")
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
            
            # Add round-specific comments if available
            if item.round1_comment:
                lines.append(f"  Раунд 1: {escape(item.round1_comment)}")
            if item.round2_comment:
                lines.append(f"  Раунд 2: {escape(item.round2_comment)}")
    if duel.final_verdict:
        lines.append(f"\n<b>Краткий итог</b>\n{escape(duel.final_verdict.splitlines()[0])}")

    await target_message.answer("\n".join(lines), parse_mode="HTML")


@router.message(F.text == FEEDBACK_BUTTON)
async def handle_feedback_button(message: Message) -> None:
    await _start_feedback(message)

@router.callback_query(F.data == "feedback")
async def start_feedback_flow(callback: CallbackQuery) -> None:
    await callback.answer(text="OK")
    await _start_feedback(callback.message)

async def _start_feedback(target_message: Message) -> None:
    FEEDBACK_REQUEST_USERS.add(target_message.from_user.id)
    
    await target_message.answer(
        "💬 Напишите сообщение для обратной связи.\n\n"
        "Чтобы выйти, просто выберите другой пункт меню.",
    )


@router.message(lambda msg: msg.from_user.id in FEEDBACK_REQUEST_USERS)
async def handle_feedback_message(message: Message) -> None:
    feedback_text = message.text.strip()
    
    # Validate non-empty
    if not feedback_text:
        await message.answer("Пустое сообщение. Напишите что-нибудь или просто выберите другой пункт меню.")
        return
    
    FEEDBACK_REQUEST_USERS.discard(message.from_user.id)
    
    # Try to forward
    try:
        from app.config import settings
        if settings.feedback_owner_user_id:
            from aiogram import Bot
            bot = Bot(token=settings.telegram_bot_token)
            try:
                owner_text = f"📨 Новая обратная связь\n\nОт: @{message.from_user.username or message.from_user.id}\n\n{feedback_text}"
                await bot.send_message(chat_id=settings.feedback_owner_user_id, text=owner_text)
                await message.answer("✅ Спасибо. Сообщение отправлено.")
            finally:
                await bot.session.close()
        else:
            # No owner configured — tell user honestly
            await message.answer("⚠️ Владелец не настроил получение обратной связи. Извините!")
            logger.warning("Feedback sent but feedback_owner_user_id not configured")
    except Exception as e:
        # Be honest about failure
        await message.answer("⚠️ Не удалось отправить сообщение. Попробуйте позже или напишите напрямую.")
        logger.error("Feedback delivery failed: %s", e)


async def show_main_menu(message: Message) -> None:
    # Check if user has active duel
    async with db_session.AsyncSessionLocal() as session:
        duel_service = DuelService()
        duel = await duel_service.get_latest_duel_for_user(
            session, telegram_user_id=message.from_user.id
        )
        has_active_duel = duel and duel.status not in ("finished", "cancelled")

    # Build keyboard dynamically
    from app.bot.keyboards.main_menu import build_main_menu
    markup = build_main_menu(has_active_duel=has_active_duel)
    
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
    
    await message.answer(
        menu_text,
        reply_markup=markup,
    )


@router.message(F.text == "/start")
@router.message(F.text == "Меню")
async def handle_start_command(message: Message) -> None:
    # Check for active duel and show options
    async with db_session.AsyncSessionLocal() as session:
        duel_service = DuelService()
        duel = await duel_service.get_latest_duel_for_user(
            session, telegram_user_id=message.from_user.id
        )
        
        if duel and duel.status not in ("finished", "cancelled"):
            # User has active duel — show options
            from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
            
            active_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="▶️ Продолжить поединок", callback_data="continue_duel")],
                [InlineKeyboardButton(text="🗑 Сбросить и начать новый", callback_data="reset_and_new")],
                [InlineKeyboardButton(text="📋 Главное меню", callback_data="back_to_menu")]
            ])
            
            await message.answer(
                f"⚠️ <b>У вас есть активный поединок</b> #{duel.id}\n"
                f"Статус: <i>{duel.status}</i>\n\n"
                f"Что хотите сделать?",
                parse_mode="HTML",
                reply_markup=active_keyboard
            )
            return
    
    # No active duel — show main menu
    await show_main_menu(message)


@router.message(F.text.in_({RULES_BUTTON, RULES_BUTTON_LEGACY, SCENARIOS_BUTTON}))
async def handle_rules_button(message: Message) -> None:
    await _show_rules(message)

@router.callback_query(F.data == "rules")
async def how_it_works(callback: CallbackQuery) -> None:
    await callback.answer(text="OK")
    await _show_rules(callback.message)

async def _show_rules(target_message: Message) -> None:
    await target_message.answer(
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
        "<b>Обратная связь</b>\n"
        "Если хотите оставить отзыв или предложить улучшение, нажмите кнопку <b>«💬 Обратная связь»</b> в главном меню.\n\n"
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

    temp_path: Union[Path, None] = None
    try:
        # Show processing status immediately after receiving voice
        processing_msg = await message.answer("🎤 Голосовое получено. Распознаю речь…")
        temp_path = await _download_telegram_file(message)
        transcript = await transcription_service.transcribe(temp_path, language="ru")
        
        # After STT is done, show success message
        await message.answer("🤖 Ответ готов")
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
        # Игнорируем PENDING_CUSTOM_SCENARIO_USERS completely
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

    temp_path: Union[Path, None] = None
    try:
        # Show processing status immediately after receiving audio
        await message.answer("🎤 Голосовое получено. Распознаю речь…")
        temp_path = await _download_telegram_file(message)
        transcript = await transcription_service.transcribe(temp_path, language="ru")
        
        # After STT is done, show success message
        await message.answer("🤖 Ответ готов")
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
        # Аудио в активном duel → продолжаем текущий раунд
        # Игнорируем PENDING_CUSTOM_SCENARIO_USERS completely
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
    # Если пользователь находится в режиме отправки обратной связи
    if message.from_user and message.from_user.id in FEEDBACK_REQUEST_USERS:
        # Отправляем обратную связь владельцу и убираем пользователя из режима обратной связи
        FEEDBACK_REQUEST_USERS.discard(message.from_user.id)
        await _send_feedback_to_owner(message, message.text)
        return

    # Если ждём описание пользовательского сценария — используем текст как исходник
    if message.from_user and message.from_user.id in PENDING_CUSTOM_SCENARIO_USERS:
        await _start_custom_duel(message, message.text)
        return

    await _run_turn(message, message.text)

