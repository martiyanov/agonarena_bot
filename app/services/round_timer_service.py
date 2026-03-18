from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable

from aiogram import Bot

from app.config import settings
from app.db.session import AsyncSessionLocal
from app.services.duel_service import DuelService


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class RoundTimerService:
    def __init__(self) -> None:
        self._tasks: dict[tuple[int, int], asyncio.Task] = {}

    def schedule(self, *, chat_id: int, duel_id: int, round_number: int, delay_seconds: int) -> None:
        if delay_seconds <= 0:
            return

        key = (duel_id, round_number)
        old_task = self._tasks.get(key)
        if old_task and not old_task.done():
            logger.info("round timer: cancelling previous task for duel=%s round=%s", duel_id, round_number)
            old_task.cancel()

        logger.info(
            "round timer: scheduling timeout in %s sec for duel=%s round=%s",
            delay_seconds,
            duel_id,
            round_number,
        )

        self._tasks[key] = asyncio.create_task(
            self._run_timeout(chat_id=chat_id, duel_id=duel_id, round_number=round_number, delay_seconds=delay_seconds)
        )

    async def _run_timeout(self, *, chat_id: int, duel_id: int, round_number: int, delay_seconds: int) -> None:
        try:
            logger.info(
                "round timer: started background wait for duel=%s round=%s delay=%s",
                duel_id,
                round_number,
                delay_seconds,
            )
            await asyncio.sleep(delay_seconds)

            async with AsyncSessionLocal() as session:
                duel_service = DuelService()
                duel = await duel_service.get_duel(session, duel_id)
                round_obj = await duel_service.get_round(session, duel_id, round_number)

                if duel is None or round_obj is None:
                    return
                if round_obj.status != "in_progress":
                    logger.info(
                        "round timer: round already not in_progress (status=%s) for duel=%s round=%s",
                        round_obj.status,
                        duel_id,
                        round_number,
                    )
                    return
                if not duel_service.is_round_expired(duel, round_obj):
                    logger.info(
                        "round timer: deadline not reached yet for duel=%s round=%s",
                        duel_id,
                        round_number,
                    )
                    return

                logger.info("round timer: completing round for duel=%s round=%s", duel_id, round_number)
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
                logger.info("round timer: sending timeout message for duel=%s round=%s", duel_id, round_number)
                await bot.send_message(chat_id=chat_id, text=text)
            finally:
                await bot.session.close()
        except asyncio.CancelledError:
            return
        finally:
            self._tasks.pop((duel_id, round_number), None)


round_timer_service = RoundTimerService()
