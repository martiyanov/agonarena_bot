"""
Voice Message Flow Tests (extends existing test_voice_routing.py)

Проверяет:
- Voice in active duel → continues round
- Voice without active duel → error/redirect
- Transcription service integration
"""

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TEST_DB_PATH = ROOT / "data" / "agonarena_test_voice_flow.db"
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


def _create_mock_duel(user_id: int, status: str = "in_progress", current_round: int = 1) -> Duel:
    """Создаёт тестовый дуэль."""
    duel = Duel()
    duel.id = 999
    duel.telegram_user_id = user_id
    duel.status = status
    duel.scenario_id = 1
    duel.current_round_number = current_round
    duel.turn_time_limit_sec = 300
    duel.final_verdict = None
    return duel


class TestVoiceInActiveDuel:
    """Тесты: голосовое сообщение в активной дуэли продолжает раунд."""

    @pytest.mark.asyncio
    async def test_voice_in_active_duel_continues_current_round(self, fresh_test_db) -> None:
        """Голосовое сообщение в активной дуэли продолжает текущий раунд."""
        from app.bot.handlers.menu import process_voice_turn

        message = _create_mock_message(from_user_id=123)

        mock_duel = _create_mock_duel(user_id=123, status="in_progress", current_round=1)

        with patch("app.bot.handlers.menu.TranscriptionService") as MockTranscriptionService, \
             patch("app.bot.handlers.menu.db_session") as mock_db_session, \
             patch("app.bot.handlers.menu.DuelService") as MockDuelService, \
             patch("app.bot.handlers.menu._run_turn") as mock_run_turn:

            mock_transcription_service = MockTranscriptionService.return_value
            mock_transcription_service.is_configured.return_value = True
            mock_transcription_service.transcribe = AsyncMock(return_value="распознанный текст голосового сообщения")

            mock_duel_service = MockDuelService.return_value
            mock_duel_service.get_latest_duel_for_user = AsyncMock(return_value=mock_duel)

            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_db_session.AsyncSessionLocal.return_value = mock_session

            await process_voice_turn(message)

            # Проверяем, что _run_turn был вызван с распознанным текстом
            mock_run_turn.assert_called_once()
            call_args = mock_run_turn.call_args
            # Second positional argument is the recognized text
            assert len(call_args[0]) >= 2  # Ensure there are at least 2 positional args
            assert call_args[0][1] == "распознанный текст голосового сообщения"
            assert call_args[1].get("recognized_from_voice") is True

    @pytest.mark.asyncio
    async def test_voice_in_round_2_also_continues_duel(self, fresh_test_db) -> None:
        """Голосовое сообщение во втором раунде также продолжает дуэль."""
        from app.bot.handlers.menu import process_voice_turn

        message = _create_mock_message(from_user_id=456)

        mock_duel = _create_mock_duel(user_id=456, status="in_progress", current_round=2)

        with patch("app.bot.handlers.menu.TranscriptionService") as MockTranscriptionService, \
             patch("app.bot.handlers.menu.db_session") as mock_db_session, \
             patch("app.bot.handlers.menu.DuelService") as MockDuelService, \
             patch("app.bot.handlers.menu._run_turn") as mock_run_turn:

            mock_transcription_service = MockTranscriptionService.return_value
            mock_transcription_service.is_configured.return_value = True
            mock_transcription_service.transcribe = AsyncMock(return_value="текст из голоса во втором раунде")

            mock_duel_service = MockDuelService.return_value
            mock_duel_service.get_latest_duel_for_user = AsyncMock(return_value=mock_duel)

            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_db_session.AsyncSessionLocal.return_value = mock_session

            await process_voice_turn(message)

            mock_run_turn.assert_called_once()
            call_args = mock_run_turn.call_args
            # Second positional argument is the recognized text
            assert len(call_args[0]) >= 2  # Ensure there are at least 2 positional args
            assert call_args[0][1] == "текст из голоса во втором раунде"
            # current_round is not a parameter to _run_turn, so removing that assertion

    @pytest.mark.asyncio
    async def test_voice_processing_updates_message_history(self, fresh_test_db) -> None:
        """Обработка голосового сообщения обновляет историю сообщений."""
        from app.bot.handlers.menu import process_voice_turn

        message = _create_mock_message(from_user_id=789)

        mock_duel = _create_mock_duel(user_id=789, status="in_progress", current_round=1)

        with patch("app.bot.handlers.menu.TranscriptionService") as MockTranscriptionService, \
             patch("app.bot.handlers.menu.db_session") as mock_db_session, \
             patch("app.bot.handlers.menu.DuelService") as MockDuelService, \
             patch("app.bot.handlers.menu._run_turn") as mock_run_turn:

            mock_transcription_service = MockTranscriptionService.return_value
            mock_transcription_service.is_configured.return_value = True
            mock_transcription_service.transcribe = AsyncMock(return_value="голосовое сообщение для истории")

            mock_duel_service = MockDuelService.return_value
            mock_duel_service.get_latest_duel_for_user = AsyncMock(return_value=mock_duel)

            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_db_session.AsyncSessionLocal.return_value = mock_session

            await process_voice_turn(message)

            # Проверяем, что _run_turn получил распознанный текст
            mock_run_turn.assert_called_once()
            call_args = mock_run_turn.call_args
            # Second positional argument is the recognized text
            assert len(call_args[0]) >= 2  # Ensure there are at least 2 positional args
            assert "голосовое сообщение для истории" in call_args[0][1]


class TestVoiceWithoutActiveDuel:
    """Тесты: голосовое сообщение без активной дуэли."""

    @pytest.mark.asyncio
    async def test_voice_without_active_duel_shows_redirect_message(self, fresh_test_db) -> None:
        """Голосовое сообщение без активной дуэли показывает сообщение о перенаправлении."""
        from app.bot.handlers.menu import process_voice_turn

        message = _create_mock_message(from_user_id=333)

        with patch("app.bot.handlers.menu.TranscriptionService") as MockTranscriptionService, \
             patch("app.bot.handlers.menu.db_session") as mock_db_session, \
             patch("app.bot.handlers.menu.DuelService") as MockDuelService:

            mock_transcription_service = MockTranscriptionService.return_value
            mock_transcription_service.is_configured.return_value = True
            mock_transcription_service.transcribe = AsyncMock(return_value="текст голоса")

            mock_duel_service = MockDuelService.return_value
            mock_duel_service.get_latest_duel_for_user = AsyncMock(return_value=None)

            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_db_session.AsyncSessionLocal.return_value = mock_session

            await process_voice_turn(message)

            # Проверяем, что показывается сообщение о перенаправлении
            message.answer.assert_called()
            call_args = message.answer.call_args
            assert "активного поединка" in str(call_args[0][0]) or "выбрать сценарий" in str(call_args[0][0])

    @pytest.mark.asyncio
    async def test_voice_without_duel_does_not_call_run_turn(self, fresh_test_db) -> None:
        """Голосовое сообщение без дуэли не вызывает _run_turn."""
        from app.bot.handlers.menu import process_voice_turn

        message = _create_mock_message(from_user_id=444)

        with patch("app.bot.handlers.menu.TranscriptionService") as MockTranscriptionService, \
             patch("app.bot.handlers.menu.db_session") as mock_db_session, \
             patch("app.bot.handlers.menu.DuelService") as MockDuelService, \
             patch("app.bot.handlers.menu._run_turn") as mock_run_turn:

            mock_transcription_service = MockTranscriptionService.return_value
            mock_transcription_service.is_configured.return_value = True
            mock_transcription_service.transcribe = AsyncMock(return_value="любой текст")

            mock_duel_service = MockDuelService.return_value
            mock_duel_service.get_latest_duel_for_user = AsyncMock(return_value=None)

            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_db_session.AsyncSessionLocal.return_value = mock_session

            await process_voice_turn(message)

            # _run_turn не должен быть вызван
            mock_run_turn.assert_not_called()

    @pytest.mark.asyncio
    async def test_voice_without_duel_checks_for_custom_scenario(self, fresh_test_db) -> None:
        """Голосовое без дуэли проверяет наличие кастомного сценария."""
        from app.bot.handlers.menu import process_voice_turn, PENDING_CUSTOM_SCENARIO_USERS

        message = _create_mock_message(from_user_id=555)
        PENDING_CUSTOM_SCENARIO_USERS.add(555)

        with patch("app.bot.handlers.menu.TranscriptionService") as MockTranscriptionService, \
             patch("app.bot.handlers.menu.db_session") as mock_db_session, \
             patch("app.bot.handlers.menu.DuelService") as MockDuelService, \
             patch("app.bot.handlers.menu._start_custom_duel") as mock_start_custom:

            mock_transcription_service = MockTranscriptionService.return_value
            mock_transcription_service.is_configured.return_value = True
            mock_transcription_service.transcribe = AsyncMock(return_value="описание кастомного сценария")

            mock_duel_service = MockDuelService.return_value
            mock_duel_service.get_latest_duel_for_user = AsyncMock(return_value=None)

            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_db_session.AsyncSessionLocal.return_value = mock_session

            await process_voice_turn(message)

            # Должен быть вызван _start_custom_duel для пользователя в pending
            mock_start_custom.assert_called_once()


class TestTranscriptionServiceIntegration:
    """Тесты интеграции с сервисом транскрибации."""

    @pytest.mark.asyncio
    async def test_transcription_service_called_with_voice_file(self, fresh_test_db) -> None:
        """Сервис транскрибации вызывается с файлом голосового сообщения."""
        from app.bot.handlers.menu import process_voice_turn

        message = _create_mock_message(from_user_id=666)
        message.voice.file_id = "test_voice_file_123"

        mock_duel = _create_mock_duel(user_id=666, status="in_progress")

        with patch("app.bot.handlers.menu.TranscriptionService") as MockTranscriptionService, \
             patch("app.bot.handlers.menu.db_session") as mock_db_session, \
             patch("app.bot.handlers.menu.DuelService") as MockDuelService, \
             patch("app.bot.handlers.menu._run_turn") as mock_run_turn:

            mock_transcription_service = MockTranscriptionService.return_value
            mock_transcription_service.is_configured.return_value = True
            mock_transcription_service.transcribe = AsyncMock(return_value="тестовый результат транскрибации")

            mock_duel_service = MockDuelService.return_value
            mock_duel_service.get_latest_duel_for_user = AsyncMock(return_value=mock_duel)

            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_db_session.AsyncSessionLocal.return_value = mock_session

            await process_voice_turn(message)

            # Проверяем, что transcribe был вызван
            mock_transcription_service.transcribe.assert_called_once()

    @pytest.mark.asyncio
    async def test_transcription_error_handled_gracefully(self, fresh_test_db) -> None:
        """Ошибка транскрибации обрабатывается корректно."""
        from app.bot.handlers.menu import process_voice_turn

        message = _create_mock_message(from_user_id=777)

        mock_duel = _create_mock_duel(user_id=777, status="in_progress")

        with patch("app.bot.handlers.menu.TranscriptionService") as MockTranscriptionService, \
             patch("app.bot.handlers.menu.db_session") as mock_db_session, \
             patch("app.bot.handlers.menu.DuelService") as MockDuelService, \
             patch("app.bot.handlers.menu._run_turn") as mock_run_turn:

            mock_transcription_service = MockTranscriptionService.return_value
            mock_transcription_service.is_configured.return_value = True
            mock_transcription_service.transcribe = AsyncMock(side_effect=Exception("Ошибка транскрибации"))

            mock_duel_service = MockDuelService.return_value
            mock_duel_service.get_latest_duel_for_user = AsyncMock(return_value=mock_duel)

            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_db_session.AsyncSessionLocal.return_value = mock_session

            await process_voice_turn(message)

            # При ошибке транскрибации _run_turn не должен быть вызван
            mock_run_turn.assert_not_called()
            # Но должно быть показано сообщение об ошибке
            message.answer.assert_called()

    @pytest.mark.asyncio
    async def test_unconfigured_transcription_service_shows_error(self, fresh_test_db) -> None:
        """Не настроенный сервис транскрибации показывает сообщение об ошибке."""
        from app.bot.handlers.menu import process_voice_turn

        message = _create_mock_message(from_user_id=888)

        mock_duel = _create_mock_duel(user_id=888, status="in_progress")

        with patch("app.bot.handlers.menu.TranscriptionService") as MockTranscriptionService, \
             patch("app.bot.handlers.menu.db_session") as mock_db_session, \
             patch("app.bot.handlers.menu.DuelService") as MockDuelService, \
             patch("app.bot.handlers.menu._run_turn") as mock_run_turn:

            mock_transcription_service = MockTranscriptionService.return_value
            mock_transcription_service.is_configured.return_value = False  # Не настроен

            mock_duel_service = MockDuelService.return_value
            mock_duel_service.get_latest_duel_for_user = AsyncMock(return_value=mock_duel)

            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_db_session.AsyncSessionLocal.return_value = mock_session

            await process_voice_turn(message)

            # Если сервис не настроен, _run_turn не должен быть вызван
            mock_run_turn.assert_not_called()
            # Должно быть показано сообщение о необходимости настройки
            message.answer.assert_called()
            call_args = message.answer.call_args
            # Actual message is "Распознавание голоса пока не настроено. Отправьте сообщение текстом."
            assert "настроено" in str(call_args[0][0]) or "транскрибация" in str(call_args[0][0])

    @pytest.mark.asyncio
    async def test_transcription_passed_to_duel_logic(self, fresh_test_db) -> None:
        """Результат транскрибации передается в логику дуэли."""
        from app.bot.handlers.menu import process_voice_turn

        message = _create_mock_message(from_user_id=999)

        mock_duel = _create_mock_duel(user_id=999, status="in_progress")

        expected_transcription = "точный текст из голосового сообщения"

        with patch("app.bot.handlers.menu.TranscriptionService") as MockTranscriptionService, \
             patch("app.bot.handlers.menu.db_session") as mock_db_session, \
             patch("app.bot.handlers.menu.DuelService") as MockDuelService, \
             patch("app.bot.handlers.menu._run_turn") as mock_run_turn:

            mock_transcription_service = MockTranscriptionService.return_value
            mock_transcription_service.is_configured.return_value = True
            mock_transcription_service.transcribe = AsyncMock(return_value=expected_transcription)

            mock_duel_service = MockDuelService.return_value
            mock_duel_service.get_latest_duel_for_user = AsyncMock(return_value=mock_duel)

            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_db_session.AsyncSessionLocal.return_value = mock_session

            await process_voice_turn(message)

            # Проверяем, что транскрибированный текст передан в _run_turn
            mock_run_turn.assert_called_once()
            call_args = mock_run_turn.call_args
            # Second positional argument is the recognized text
            assert len(call_args[0]) >= 2  # Ensure there are at least 2 positional args
            assert call_args[0][1] == expected_transcription
            assert call_args[1].get("recognized_from_voice") is True


class TestAudioMessageHandling:
    """Тесты обработки аудио сообщений (не голосовых)."""

    @pytest.mark.asyncio
    async def test_audio_message_processed_similar_to_voice(self, fresh_test_db) -> None:
        """Аудио сообщения обрабатываются аналогично голосовым."""
        from app.bot.handlers.menu import process_audio_turn

        message = _create_mock_message(from_user_id=101)
        message.voice = None
        message.audio = MagicMock(file_id="audio_file_456", file_name="audio.mp3")

        mock_duel = _create_mock_duel(user_id=101, status="in_progress")

        with patch("app.bot.handlers.menu.TranscriptionService") as MockTranscriptionService, \
             patch("app.bot.handlers.menu.db_session") as mock_db_session, \
             patch("app.bot.handlers.menu.DuelService") as MockDuelService, \
             patch("app.bot.handlers.menu._run_turn") as mock_run_turn:

            mock_transcription_service = MockTranscriptionService.return_value
            mock_transcription_service.is_configured.return_value = True
            mock_transcription_service.transcribe = AsyncMock(return_value="текст из аудио файла")

            mock_duel_service = MockDuelService.return_value
            mock_duel_service.get_latest_duel_for_user = AsyncMock(return_value=mock_duel)

            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_db_session.AsyncSessionLocal.return_value = mock_session

            await process_audio_turn(message)

            mock_run_turn.assert_called_once()
            call_args = mock_run_turn.call_args
            # Second positional argument is the recognized text
            assert len(call_args[0]) >= 2  # Ensure there are at least 2 positional args
            assert call_args[0][1] == "текст из аудио файла"
            assert call_args[1].get("recognized_from_voice") is True  # Должно быть True для обоих типов

    @pytest.mark.asyncio
    async def test_audio_without_active_duel_shows_hint(self, fresh_test_db) -> None:
        """Аудио без активной дуэли показывает подсказку."""
        from app.bot.handlers.menu import process_audio_turn

        message = _create_mock_message(from_user_id=202)
        message.voice = None
        message.audio = MagicMock(file_id="audio_file_789", file_name="speech.mp3")

        with patch("app.bot.handlers.menu.TranscriptionService") as MockTranscriptionService, \
             patch("app.bot.handlers.menu.db_session") as mock_db_session, \
             patch("app.bot.handlers.menu.DuelService") as MockDuelService:

            mock_transcription_service = MockTranscriptionService.return_value
            mock_transcription_service.is_configured.return_value = True
            mock_transcription_service.transcribe = AsyncMock(return_value="любой текст")

            mock_duel_service = MockDuelService.return_value
            mock_duel_service.get_latest_duel_for_user = AsyncMock(return_value=None)

            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_db_session.AsyncSessionLocal.return_value = mock_session

            await process_audio_turn(message)

            message.answer.assert_called()
            call_args = message.answer.call_args
            assert "активного поединка" in str(call_args[0][0])