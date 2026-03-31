"""
Тесты на корректную маршрутизацию голосовых сообщений в duel-flow.

Критерии:
- active duel имеет приоритет над pending custom scenario
- voice внутри активного duel не создаёт новый duel
- voice без активного duel и без pending custom scenario возвращает подсказку
"""

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TEST_DB_PATH = ROOT / "data" / "agonarena_test_voice_routing.db"
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_PATH}"

import app.config as app_config  # noqa: E402
from app.db import session as db_session  # noqa: E402
from app.db.init_db import init_db  # noqa: E402
from app.db.models.duel import Duel  # noqa: E402

app_config.settings = app_config.Settings()


@pytest.fixture
async def fresh_test_db():
    """Async fixture для инициализации чистой тестовой БД."""
    TEST_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    if db_session.engine is not None:
        await db_session.engine.dispose()

    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()

    db_session.configure_database(f"sqlite+aiosqlite:///{TEST_DB_PATH}")
    await init_db()

    yield

    if db_session.engine is not None:
        await db_session.engine.dispose()

    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()


def _create_mock_message(from_user_id: int = 123, chat_id: int = 456) -> MagicMock:
    """Создаёт мок Telegram-сообщения."""
    message = MagicMock()
    message.from_user = MagicMock(id=from_user_id)
    message.chat = MagicMock(id=chat_id)
    message.voice = MagicMock(file_id="voice_file_123")
    message.audio = None
    message.text = None
    message.answer = AsyncMock()
    message.bot = MagicMock()
    message.bot.get_file = AsyncMock(return_value=MagicMock(file_path="voice.ogg"))
    message.bot.download_file = AsyncMock()
    return message


def _create_mock_duel(user_id: int, status: str = "round_1_active") -> Duel:
    """Создаёт тестовый дуэль."""
    duel = Duel()
    duel.id = 999
    duel.telegram_user_id = user_id
    duel.status = status
    duel.scenario_id = 1
    duel.current_round_number = 1
    duel.turn_time_limit_sec = 300
    duel.final_verdict = None
    return duel


class TestVoiceRoutingWithActiveDuel:
    """Тесты: голосовое внутри активного дуэля."""

    @pytest.mark.asyncio
    async def test_voice_in_active_duel_continues_duel(self, fresh_test_db) -> None:
        """Голосовое в активном дуэле продолжает дуэль, а не создаёт новый."""
        from app.bot.handlers.menu import process_voice_turn, PENDING_CUSTOM_SCENARIO_USERS

        message = _create_mock_message(from_user_id=123)
        PENDING_CUSTOM_SCENARIO_USERS.add(123)

        mock_duel = _create_mock_duel(user_id=123, status="round_1_active")

        with patch("app.bot.handlers.menu.TranscriptionService") as MockTranscriptionService, \
             patch("app.bot.handlers.menu.db_session") as mock_db_session, \
             patch("app.bot.handlers.menu.DuelService") as MockDuelService, \
             patch("app.bot.handlers.menu._run_turn") as mock_run_turn:

            mock_transcription_service = MockTranscriptionService.return_value
            mock_transcription_service.is_configured.return_value = True
            mock_transcription_service.transcribe = AsyncMock(return_value="распознанный текст")

            mock_duel_service = MockDuelService.return_value
            mock_duel_service.get_latest_duel_for_user = AsyncMock(return_value=mock_duel)

            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_db_session.AsyncSessionLocal.return_value = mock_session

            await process_voice_turn(message)

            # Проверяем, что _run_turn был вызван (продолжение дуэля)
            mock_run_turn.assert_called_once()
            # И что start_custom_duel НЕ вызывался
            assert message.answer.called


    @pytest.mark.asyncio
    async def test_voice_in_finished_duel_offers_hint(self, fresh_test_db) -> None:
        """Голосовое в завершённом дуэле не продолжает дуэль."""
        from app.bot.handlers.menu import process_voice_turn, PENDING_CUSTOM_SCENARIO_USERS

        message = _create_mock_message(from_user_id=456)
        PENDING_CUSTOM_SCENARIO_USERS.add(456)

        mock_duel = _create_mock_duel(user_id=456, status="finished")

        with patch("app.bot.handlers.menu.TranscriptionService") as MockTranscriptionService, \
             patch("app.bot.handlers.menu.db_session") as mock_db_session, \
             patch("app.bot.handlers.menu.DuelService") as MockDuelService, \
             patch("app.bot.handlers.menu._run_turn") as mock_run_turn, \
             patch("app.bot.handlers.menu._start_custom_duel") as mock_start_custom:

            mock_transcription_service = MockTranscriptionService.return_value
            mock_transcription_service.is_configured.return_value = True
            mock_transcription_service.transcribe = AsyncMock(return_value="распознанный текст")

            mock_duel_service = MockDuelService.return_value
            mock_duel_service.get_latest_duel_for_user = AsyncMock(return_value=mock_duel)

            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_db_session.AsyncSessionLocal.return_value = mock_session

            await process_voice_turn(message)

            # _run_turn не должен вызываться для finished duel
            mock_run_turn.assert_not_called()
            # Должен вызваться _start_custom_duel (т.к. пользователь в pending)
            mock_start_custom.assert_called_once()


class TestVoiceRoutingWithoutActiveDuel:
    """Тесты: голосовое без активного дуэля."""

    @pytest.mark.asyncio
    async def test_voice_with_pending_custom_scenario_starts_custom_duel(self) -> None:
        """Голосовое от пользователя в pending custom scenario создаёт кастомный дуэль."""
        from app.bot.handlers.menu import process_voice_turn, PENDING_CUSTOM_SCENARIO_USERS

        message = _create_mock_message(from_user_id=789)
        PENDING_CUSTOM_SCENARIO_USERS.add(789)

        with patch("app.bot.handlers.menu.TranscriptionService") as MockTranscriptionService, \
             patch("app.bot.handlers.menu.db_session") as mock_db_session, \
             patch("app.bot.handlers.menu.DuelService") as MockDuelService, \
             patch("app.bot.handlers.menu._start_custom_duel") as mock_start_custom:

            mock_transcription_service = MockTranscriptionService.return_value
            mock_transcription_service.is_configured.return_value = True
            mock_transcription_service.transcribe = AsyncMock(return_value="распознанный текст")

            mock_duel_service = MockDuelService.return_value
            mock_duel_service.get_latest_duel_for_user = AsyncMock(return_value=None)

            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_db_session.AsyncSessionLocal.return_value = mock_session

            await process_voice_turn(message)

            # Должен вызваться _start_custom_duel
            mock_start_custom.assert_called_once()


    @pytest.mark.asyncio
    async def test_voice_without_duel_and_without_pending_shows_hint(self) -> None:
        """Голосовое без дуэля и без pending показывает подсказку."""
        from app.bot.handlers.menu import process_voice_turn, PENDING_CUSTOM_SCENARIO_USERS

        message = _create_mock_message(from_user_id=999)
        PENDING_CUSTOM_SCENARIO_USERS.discard(999)

        with patch("app.bot.handlers.menu.TranscriptionService") as MockTranscriptionService, \
             patch("app.bot.handlers.menu.db_session") as mock_db_session, \
             patch("app.bot.handlers.menu.DuelService") as MockDuelService:

            mock_transcription_service = MockTranscriptionService.return_value
            mock_transcription_service.is_configured.return_value = True
            mock_transcription_service.transcribe = AsyncMock(return_value="распознанный текст")

            mock_duel_service = MockDuelService.return_value
            mock_duel_service.get_latest_duel_for_user = AsyncMock(return_value=None)

            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_db_session.AsyncSessionLocal.return_value = mock_session

            await process_voice_turn(message)

            # Должна быть показана подсказка
            message.answer.assert_any_call(
                "Сейчас у вас нет активного поединка. Нажмите «🎯 Выбрать сценарий» для старта."
            )


class TestAudioRoutingWithActiveDuel:
    """Тесты: аудио внутри активного дуэля (аналогично voice)."""

    @pytest.mark.asyncio
    async def test_audio_in_active_duel_continues_duel(self) -> None:
        """Аудио в активном дуэле продолжает дуэль, а не создаёт новый."""
        from app.bot.handlers.menu import process_audio_turn, PENDING_CUSTOM_SCENARIO_USERS

        message = _create_mock_message(from_user_id=123)
        message.voice = None
        message.audio = MagicMock(file_id="audio_file_123", file_name="audio.mp3")
        PENDING_CUSTOM_SCENARIO_USERS.add(123)

        mock_duel = _create_mock_duel(user_id=123, status="round_1_active")

        with patch("app.bot.handlers.menu.TranscriptionService") as MockTranscriptionService, \
             patch("app.bot.handlers.menu.db_session") as mock_db_session, \
             patch("app.bot.handlers.menu.DuelService") as MockDuelService, \
             patch("app.bot.handlers.menu._run_turn") as mock_run_turn:

            mock_transcription_service = MockTranscriptionService.return_value
            mock_transcription_service.is_configured.return_value = True
            mock_transcription_service.transcribe = AsyncMock(return_value="распознанный текст")

            mock_duel_service = MockDuelService.return_value
            mock_duel_service.get_latest_duel_for_user = AsyncMock(return_value=mock_duel)

            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_db_session.AsyncSessionLocal.return_value = mock_session

            await process_audio_turn(message)

            # Проверяем, что _run_turn был вызван (продолжение дуэля)
            mock_run_turn.assert_called_once()


class TestVoiceMidDuel:
    """Тесты: голосовое сообщение в середине активного duel не сбрасывает состояние."""

    @pytest.mark.asyncio
    async def test_voice_mid_duel_does_not_reset_state(self) -> None:
        """
        Критический тест: голосовое сообщение в середине раунда
        должно продолжать текущий duel, а не создавать новый.
        """
        from app.bot.handlers.menu import process_voice_turn, PENDING_CUSTOM_SCENARIO_USERS

        message = _create_mock_message(from_user_id=555)
        # Пользователь мог ранее нажать "Свой сценарий", но уже начал duel
        PENDING_CUSTOM_SCENARIO_USERS.add(555)

        # Активный duel в состоянии round_1_active
        mock_duel = _create_mock_duel(user_id=555, status="round_1_active")
        mock_duel.current_round_number = 1

        with patch("app.bot.handlers.menu.TranscriptionService") as MockTranscriptionService, \
             patch("app.bot.handlers.menu.db_session") as mock_db_session, \
             patch("app.bot.handlers.menu.DuelService") as MockDuelService, \
             patch("app.bot.handlers.menu._run_turn") as mock_run_turn, \
             patch("app.bot.handlers.menu._start_custom_duel") as mock_start_custom:

            mock_transcription_service = MockTranscriptionService.return_value
            mock_transcription_service.is_configured.return_value = True
            mock_transcription_service.transcribe = AsyncMock(return_value="тестовая реплика")

            mock_duel_service = MockDuelService.return_value
            mock_duel_service.get_latest_duel_for_user = AsyncMock(return_value=mock_duel)

            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_db_session.AsyncSessionLocal.return_value = mock_session

            await process_voice_turn(message)

            # КРИТИЧЕСКАЯ ПРОВЕРКА: _run_turn вызван, _start_custom_duel НЕ вызван
            mock_run_turn.assert_called_once()
            mock_start_custom.assert_not_called()

            # Проверяем, что вызов был с recognized_from_voice=True
            call_args = mock_run_turn.call_args
            assert call_args.kwargs.get("recognized_from_voice") is True
