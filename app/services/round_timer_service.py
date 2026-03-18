from __future__ import annotations

import asyncio
from collections.abc import Awaitable

from aiogram import Bot

from app.config import settings
from app.db.session import AsyncSessionLocal
from app.services.duel_service import DuelService


class RoundTimerService:
    def __init__(self) -> None:
        self._tasks: dict[tuple[int, int], asyncio.Task] = {}

    def schedule(self, *, chat_id: int, duel_id: int, round_number: int, delay_seconds: int) -> None:
        if delay_seconds <= 0:
            return

        key = (duel_id, round_number)
        old_task = self._tasks.get(key)
        if old_task and not old_task.done():
            old_task.cancel()

        self._tasks[key] = asyncio.create_task(
            self._run_timeout(chat_id=chat_id, duel_id=duel_id, round_number=round_number, delay_seconds=delay_seconds)
        )

    async def _run_timeout(self, *, chat_id: int, duel_id: int, round_number: int, delay_seconds: int) -> None:
        try:
            await asyncio.sleep(delay_seconds)

            async with AsyncSessionLocal() as session:
                duel_service = DuelService()
                duel = await duel_service.get_duel(session, duel_id)
                round_obj = await duel_service.get_round(session, duel_id, round_number)

                if duel is None or round_obj is None:
                    return
                if round_obj.status != "in_progress":
                    return
                if not duel_service.is_round_expired(duel, round_obj):
                    return

                await duel_service.complete_round(duel, round_obj)
                await session.commit()

            if not settings.telegram_bot_token:
                return

            bot = Bot(token=settings.telegram_bot_token)
            try:
                if round_number == 1:
                    text = "⏱ Время первого раунда вышло. Нажмите «⏭️ Раунд 2», чтобы продолжить."
                else:
                    text = "⏱ Время второго раунда вышло. Нажмите «🏁 Завершить», чтобы получить итог."
                await bot.send_message(chat_id=chat_id, text=text)
            finally:
                await bot.session.close()
        except asyncio.CancelledError:
            return
        finally:
            self._tasks.pop((duel_id, round_number), None)


round_timer_service = RoundTimerService()
