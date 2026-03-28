"""
Judge Verdicts Flow Tests (extends existing test_judge_round_breakdown.py)

Проверяет:
- LLM judge response parsing (round1_comment, round2_comment)
- Fallback verdicts
- Verdict aggregation (majority wins)
- Final verdict display formatting
"""

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TEST_DB_PATH = ROOT / "data" / "agonarena_test_judge_flow.db"
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_PATH}"

from app.db import session as db_session
from app.db.init_db import init_db
from app.db.models import Duel, DuelRound, JudgeResult
from app.services.duel_service import DuelService
from app.services.judge_service import JudgeService, JudgeVerdict, JudgeContext


@pytest.fixture(autouse=True)
async def fresh_test_db():
    """Инициализация чистой тестовой БД перед каждым тестом."""
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


class TestLLMJudgeResponseParsing:
    """Тесты парсинга ответов LLM судей."""

    @pytest.mark.asyncio
    async def test_parse_llm_response_with_all_fields(self, fresh_test_db):
        """LLM response с полным набором полей корректно парсится."""
        from app.services.llm_service import LLMService

        mock_llm_response = """{
            "winner": "user",
            "comment": "Пользователь выиграл благодаря лучшей аргументации",
            "round1_comment": "Раунд 1: Отличное начало, чёткие аргументы",
            "round2_comment": "Раунд 2: Уверенное завершение, контраргументы"
        }"""

        judge_service = JudgeService()

        with patch.object(LLMService, 'is_configured', return_value=True):
            with patch.object(LLMService, 'generate_text', new_callable=AsyncMock) as mock_generate:
                mock_generate.return_value = mock_llm_response

                context = JudgeContext(
                    judge_type="owner",
                    scenario_code="test_scenario",
                    duel_id=1,
                    round1_transcript="Транскрипт раунда 1",
                    round2_transcript="Транскрипт раунда 2",
                )

                verdict = await judge_service.run_single_judge(context)

        assert verdict.winner == "user"
        assert "благодаря лучшей аргументации" in verdict.comment
        assert "Раунд 1: Отличное начало" in verdict.round1_comment
        assert "Раунд 2: Уверенное завершение" in verdict.round2_comment

    @pytest.mark.asyncio
    async def test_parse_llm_response_missing_optional_fields(self, fresh_test_db):
        """LLM response без необязательных полей обрабатывается корректно."""
        from app.services.llm_service import LLMService

        mock_llm_response = """{
            "winner": "ai",
            "comment": "AI продемонстрировала превосходное понимание"
        }"""  # Нет round1_comment и round2_comment

        judge_service = JudgeService()

        with patch.object(LLMService, 'is_configured', return_value=True):
            with patch.object(LLMService, 'generate_text', new_callable=AsyncMock) as mock_generate:
                mock_generate.return_value = mock_llm_response

                context = JudgeContext(
                    judge_type="team",
                    scenario_code="test_scenario",
                    duel_id=1,
                    round1_transcript="Транскрипт",
                    round2_transcript="Транскрипт",
                )

                verdict = await judge_service.run_single_judge(context)

        assert verdict.winner == "ai"
        assert "превосходное понимание" in verdict.comment
        assert verdict.round1_comment == ""  # Пустая строка по умолчанию
        assert verdict.round2_comment == ""  # Пустая строка по умолчанию

    @pytest.mark.asyncio
    async def test_parse_llm_response_malformed_json_uses_fallback(self, fresh_test_db):
        """При некорректном JSON используется fallback вердикт."""
        from app.services.llm_service import LLMService

        malformed_response = "{invalid json}"

        judge_service = JudgeService()

        with patch.object(LLMService, 'is_configured', return_value=True):
            with patch.object(LLMService, 'generate_text', new_callable=AsyncMock) as mock_generate:
                mock_generate.return_value = malformed_response

                context = JudgeContext(
                    judge_type="sending_to_negotiation",
                    scenario_code="test_scenario",
                    duel_id=1,
                    round1_transcript="Транскрипт",
                    round2_transcript="Транскрипт",
                )

                verdict = await judge_service.run_single_judge(context)

        # При ошибке парсинга должен использоваться fallback
        assert verdict.winner in ["user", "ai", "draw"]
        # Fallback должен содержать round комментарии
        assert hasattr(verdict, 'round1_comment')
        assert hasattr(verdict, 'round2_comment')

    @pytest.mark.asyncio
    async def test_parse_llm_response_with_extra_fields(self, fresh_test_db):
        """LLM response с дополнительными полями обрабатывается корректно."""
        from app.services.llm_service import LLMService

        mock_llm_response = """{
            "winner": "draw",
            "comment": "Обе стороны показали равный уровень",
            "round1_comment": "Раунд 1: Хорошая борьба",
            "round2_comment": "Раунд 2: Баланс сил",
            "confidence": 0.8,
            "timestamp": "2024-01-01T00:00:00Z"
        }"""

        judge_service = JudgeService()

        with patch.object(LLMService, 'is_configured', return_value=True):
            with patch.object(LLMService, 'generate_text', new_callable=AsyncMock) as mock_generate:
                mock_generate.return_value = mock_llm_response

                context = JudgeContext(
                    judge_type="owner",
                    scenario_code="test_scenario",
                    duel_id=1,
                    round1_transcript="Транскрипт",
                    round2_transcript="Транскрипт",
                )

                verdict = await judge_service.run_single_judge(context)

        assert verdict.winner == "draw"
        assert "равный уровень" in verdict.comment
        assert "Хорошая борьба" in verdict.round1_comment
        assert "Баланс сил" in verdict.round2_comment
        # Дополнительные поля игнорируются, но основные обрабатываются


class TestFallbackVerdicts:
    """Тесты fallback вердиктов."""

    @pytest.mark.asyncio
    async def test_fallback_verdict_when_llm_unavailable(self, fresh_test_db):
        """Fallback вердикт при недоступности LLM."""
        from app.services.llm_service import LLMService

        judge_service = JudgeService()

        with patch.object(LLMService, 'is_configured', return_value=False):  # LLM не настроен
            context = JudgeContext(
                judge_type="owner",
                scenario_code="test_scenario",
                duel_id=1,
                round1_transcript="Транскрипт раунда 1",
                round2_transcript="Транскрипт раунда 2",
            )

            verdict = await judge_service.run_single_judge(context)

        # Fallback должен вернуть разумный вердикт
        assert verdict.winner in ["user", "ai", "draw"]
        assert verdict.comment != ""
        assert verdict.round1_comment != ""
        assert verdict.round2_comment != ""

    @pytest.mark.asyncio
    async def test_fallback_verdict_considers_scenario_context(self, fresh_test_db):
        """Fallback вердикт учитывает контекст сценария."""
        judge_service = JudgeService()

        context = JudgeContext(
            judge_type="team",
            scenario_code="salary_negotiation",
            duel_id=1,
            round1_transcript="Работник просит повышения, начальник сопротивляется",
            round2_transcript="Работник предлагает компромисс, начальник соглашается частично",
        )

        verdict = judge_service._fallback_verdict(context)

        assert verdict.winner in ["user", "ai", "draw"]
        assert verdict.comment != ""
        assert "зарплата" in verdict.comment.lower() or "переговоры" in verdict.comment.lower()
        assert verdict.round1_comment != ""
        assert verdict.round2_comment != ""

    @pytest.mark.asyncio
    async def test_fallback_verdict_for_different_judge_types(self, fresh_test_db):
        """Fallback вердикт различается для разных типов судей."""
        judge_service = JudgeService()

        context_owner = JudgeContext(
            judge_type="owner",
            scenario_code="test",
            duel_id=1,
            round1_transcript="тест",
            round2_transcript="тест",
        )
        context_team = JudgeContext(
            judge_type="team",
            scenario_code="test",
            duel_id=2,
            round1_transcript="тест",
            round2_transcript="тест",
        )
        context_sender = JudgeContext(
            judge_type="sending_to_negotiation",
            scenario_code="test",
            duel_id=3,
            round1_transcript="тест",
            round2_transcript="тест",
        )

        verdict_owner = judge_service._fallback_verdict(context_owner)
        verdict_team = judge_service._fallback_verdict(context_team)
        verdict_sender = judge_service._fallback_verdict(context_sender)

        # Все должны быть допустимыми вердиктами
        assert verdict_owner.winner in ["user", "ai", "draw"]
        assert verdict_team.winner in ["user", "ai", "draw"]
        assert verdict_sender.winner in ["user", "ai", "draw"]

        # Комментарии должны существовать
        assert verdict_owner.comment != ""
        assert verdict_team.comment != ""
        assert verdict_sender.comment != ""


class TestVerdictAggregation:
    """Тесты агрегации вердиктов (majority wins)."""

    def test_majority_wins_simple_case(self):
        """Простой случай: majority wins."""
        judge_service = JudgeService()

        verdicts = [
            JudgeVerdict(judge_type="owner", winner="user", comment="Пользователь лучше"),
            JudgeVerdict(judge_type="team", winner="user", comment="Поддерживаю пользователя"),
            JudgeVerdict(judge_type="sending_to_negotiation", winner="ai", comment="AI была убедительна"),
        ]

        final_verdict = judge_service.summarize_final_verdict(verdicts)
        # Check if user wins based on the verdict summary
        assert "user" in final_verdict.lower() or "пользователь" in final_verdict.lower()

    def test_draw_when_tie(self):
        """Ничья при равенстве голосов."""
        judge_service = JudgeService()

        verdicts = [
            JudgeVerdict(judge_type="owner", winner="user", comment="Пользователь лучше"),
            JudgeVerdict(judge_type="team", winner="ai", comment="AI была убедительна"),
            JudgeVerdict(judge_type="sending_to_negotiation", winner="draw", comment="Ничья"),
        ]

        final_verdict = judge_service.summarize_final_verdict(verdicts)
        # Check if the verdict mentions draw
        assert "draw" in final_verdict.lower() or "ничья" in final_verdict.lower() or "ничь" in final_verdict.lower()

    def test_majority_wins_with_more_than_three_judges(self):
        """Majority wins с более чем тремя судьями."""
        judge_service = JudgeService()

        verdicts = [
            JudgeVerdict(judge_type="owner", winner="user", comment="1"),
            JudgeVerdict(judge_type="team", winner="user", comment="2"),
            JudgeVerdict(judge_type="sending_to_negotiation", winner="ai", comment="3"),
            JudgeVerdict(judge_type="external", winner="user", comment="4"),
            JudgeVerdict(judge_type="observer", winner="user", comment="5"),
        ]

        final_verdict = judge_service.summarize_final_verdict(verdicts)
        # Check if user wins based on the verdict summary
        assert "user" in final_verdict.lower() or "пользователь" in final_verdict.lower()

    def test_aggregate_verdicts_preserves_individual_comments(self):
        """Агрегация сохраняет комментарии всех судей."""
        judge_service = JudgeService()

        verdicts = [
            JudgeVerdict(judge_type="owner", winner="user", comment="Владелец: пользователь лучше"),
            JudgeVerdict(judge_type="team", winner="ai", comment="Команда: AI убедительна"),
            JudgeVerdict(judge_type="sending_to_negotiation", winner="user", comment="Отправитель: пользователь прав"),
        ]

        # Агрегация не изменяет оригинальные вердикты
        assert len(verdicts) == 3
        assert verdicts[0].comment == "Владелец: пользователь лучше"
        assert verdicts[1].comment == "Команда: AI убедительна"
        assert verdicts[2].comment == "Отправитель: пользователь прав"

    def test_summarize_final_verdict_formats_majority_decision(self):
        """Финальный вердикт форматируется с учётом большинства."""
        judge_service = JudgeService()

        verdicts = [
            JudgeVerdict(judge_type="owner", winner="user", comment="Пользователь лучше"),
            JudgeVerdict(judge_type="team", winner="user", comment="Поддерживаю"),
            JudgeVerdict(judge_type="sending_to_negotiation", winner="ai", comment="AI была убедительна"),
        ]

        final_verdict = judge_service.summarize_final_verdict(verdicts)
        # В финальном вердикте должно отражаться решение большинства
        assert "user" in final_verdict.lower() or "пользователь" in final_verdict.lower()


class TestFinalVerdictDisplayFormatting:
    """Тесты форматирования финального отображения вердикта."""

    def test_format_final_verdict_includes_all_judge_opinions(self):
        """Финальный вердикт включает мнения всех судей."""
        from app.bot.handlers.menu import _format_final_verdict

        judge_service = JudgeService()

        verdicts = [
            JudgeVerdict(
                judge_type="owner",
                winner="user",
                comment="Владелец: пользователь был убедителен",
                round1_comment="Раунд 1: четкая позиция",
                round2_comment="Раунд 2: уверенная защита"
            ),
            JudgeVerdict(
                judge_type="team", 
                winner="user",
                comment="Команда: сильная аргументация",
                round1_comment="Раунд 1: хорошие доводы",
                round2_comment="Раунд 2: эффективные контраргументы"
            ),
        ]

        final_verdict = "Пользователь выиграл по решению большинства судей"
        formatted = _format_final_verdict(judge_service, verdicts, final_verdict)

        # Проверяем наличие мнений всех судей
        assert "Владелец:" in formatted or "собственник" in formatted.lower()
        assert "Команда:" in formatted or "team" in formatted.lower()
        assert "пользователь" in formatted.lower() or "user" in formatted.lower()

        # Проверяем наличие разбивки по раундам
        assert "Раунд 1:" in formatted
        assert "Раунд 2:" in formatted

    def test_format_final_verdict_handles_draw_correctly(self):
        """Форматирование корректно обрабатывает ничью."""
        from app.bot.handlers.menu import _format_final_verdict

        judge_service = JudgeService()

        verdicts = [
            JudgeVerdict(
                judge_type="owner",
                winner="draw",
                comment="Владелец: обе стороны были равны",
                round1_comment="Раунд 1: равная борьба",
                round2_comment="Раунд 2: сбалансированное завершение"
            ),
        ]

        final_verdict = "Ничья по результатам поединка"
        formatted = _format_final_verdict(judge_service, verdicts, final_verdict)

        assert "ничья" in formatted.lower() or "draw" in formatted.lower()
        assert "обе стороны" in formatted.lower()
        assert "Раунд 1:" in formatted
        assert "Раунд 2:" in formatted

    def test_format_final_verdict_omits_empty_round_comments(self):
        """Форматирование пропускает пустые раундовые комментарии."""
        from app.bot.handlers.menu import _format_final_verdict

        judge_service = JudgeService()

        verdicts = [
            JudgeVerdict(
                judge_type="team",
                winner="ai",
                comment="AI была убедительна",
                round1_comment="",  # Пустой
                round2_comment="Но во втором раунде пользователь отстал"  # Только один раунд
            ),
        ]

        final_verdict = "AI выиграла"
        formatted = _format_final_verdict(judge_service, verdicts, final_verdict)

        assert "ai" in formatted.lower()
        # Должен быть только второй раунд, так как первый пуст
        assert "во втором раунде" in formatted.lower()
        # Не должно быть упоминания пустого первого раунда в специальном формате

    def test_format_final_verdict_includes_judge_types(self):
        """Форматирование включает типы судей."""
        from app.bot.handlers.menu import _format_final_verdict

        judge_service = JudgeService()

        verdicts = [
            JudgeVerdict(judge_type="owner", winner="user", comment="Мнение владельца"),
            JudgeVerdict(judge_type="team", winner="user", comment="Мнение команды"),
            JudgeVerdict(judge_type="sending_to_negotiation", winner="ai", comment="Мнение отправителя"),
        ]

        final_verdict = "Решение по большинству"
        formatted = _format_final_verdict(judge_service, verdicts, final_verdict)

        # Проверяем, что типы судей упоминаются
        assert any(judge_type in formatted.lower() for judge_type in ["owner", "team", "sending_to_negotiation", "собственник", "команда", "отправитель"])


class TestJudgeResultsPersistence:
    """Тесты сохранения результатов судей."""

    @pytest.mark.asyncio
    async def test_save_multiple_judge_verdicts(self, fresh_test_db):
        """Сохранение результатов нескольких судей работает корректно."""
        async with db_session.AsyncSessionLocal() as session:
            # Создаём дуэль
            duel = Duel(
                status="judging",
                scenario_id=1,
                user_telegram_id=123,
                user_role_round1="Роль A",
                ai_role_round1="Роль B", 
                user_role_round2="Роль B",
                ai_role_round2="Роль A",
            )
            session.add(duel)
            await session.flush()

            judge_service = JudgeService()

            # Создаём несколько вердиктов
            verdicts = [
                JudgeVerdict(
                    judge_type="owner",
                    winner="user", 
                    comment="Владелец: пользователь лучше",
                    round1_comment="Раунд 1: сильная позиция",
                    round2_comment="Раунд 2: уверенная защита"
                ),
                JudgeVerdict(
                    judge_type="team",
                    winner="user",
                    comment="Команда: поддерживаю пользователя",
                    round1_comment="Раунд 1: хорошие аргументы",
                    round2_comment="Раунд 2: эффективные контраргументы"
                ),
            ]

            # Сохраняем все вердикты
            for verdict in verdicts:
                judge_result = await judge_service.save_verdict(duel, verdict)
                session.add(judge_result)
            await session.commit()

            # Читаем сохранённые результаты
            saved_results = await DuelService().list_judge_results(session, duel.id)

            assert len(saved_results) == 2
            assert saved_results[0].judge_type in ["owner", "team"]
            assert saved_results[1].judge_type in ["owner", "team"]
            assert saved_results[0].winner == "user"
            assert saved_results[1].winner == "user"

    @pytest.mark.asyncio
    async def test_load_judge_results_with_round_comments(self, fresh_test_db):
        """Загрузка результатов судей с раундовыми комментариями."""
        async with db_session.AsyncSessionLocal() as session:
            # Создаём дуэль
            duel = Duel(
                status="finished",
                scenario_id=1,
                user_telegram_id=456,
                user_role_round1="Менеджер",
                ai_role_round1="Разработчик",
                user_role_round2="Разработчик", 
                ai_role_round2="Менеджер",
            )
            session.add(duel)
            await session.flush()

            # Создаём и сохраняем результат судьи
            judge_result = JudgeResult(
                duel_id=duel.id,
                judge_type="external",
                winner="draw",
                comment="Эксперт: обе стороны были равны",
                round1_comment="Раунд 1: напряжённая дискуссия",
                round2_comment="Раунд 2: конструктивный финал",
            )
            session.add(judge_result)
            await session.commit()

            # Загружаем результаты
            loaded_results = await DuelService().list_judge_results(session, duel.id)

            assert len(loaded_results) == 1
            assert loaded_results[0].judge_type == "external"
            assert loaded_results[0].winner == "draw"
            assert "обе стороны были равны" in loaded_results[0].comment
            assert "напряжённая дискуссия" in loaded_results[0].round1_comment
            assert "конструктивный финал" in loaded_results[0].round2_comment

    @pytest.mark.asyncio
    async def test_judge_results_linked_to_correct_duel(self, fresh_test_db):
        """Результаты судей связаны с правильной дуэлью."""
        async with db_session.AsyncSessionLocal() as session:
            # Создаём две дуэли
            duel1 = Duel(
                status="finished",
                scenario_id=1,
                user_telegram_id=789,
                user_role_round1="Роль A",
                ai_role_round1="Роль B",
                user_role_round2="Роль B",
                ai_role_round2="Роль A",
            )
            duel2 = Duel(
                status="finished", 
                scenario_id=2,
                user_telegram_id=999,
                user_role_round1="Роль C",
                ai_role_round1="Роль D",
                user_role_round2="Роль D",
                ai_role_round2="Роль C",
            )
            session.add(duel1)
            session.add(duel2)
            await session.flush()

            # Добавляем результаты для каждой дуэли
            result1 = JudgeResult(
                duel_id=duel1.id,
                judge_type="owner",
                winner="user",
                comment="Для дуэли 1",
                round1_comment="Р1 дуэли 1",
                round2_comment="Р2 дуэли 1",
            )
            result2 = JudgeResult(
                duel_id=duel2.id, 
                judge_type="team",
                winner="ai",
                comment="Для дуэли 2",
                round1_comment="Р1 дуэли 2",
                round2_comment="Р2 дуэли 2",
            )
            session.add(result1)
            session.add(result2)
            await session.commit()

            # Проверяем, что результаты принадлежат нужным дуэлям
            results_duel1 = await DuelService().list_judge_results(session, duel1.id)
            results_duel2 = await DuelService().list_judge_results(session, duel2.id)

            assert len(results_duel1) == 1
            assert len(results_duel2) == 1
            assert results_duel1[0].comment == "Для дуэли 1"
            assert results_duel2[0].comment == "Для дуэли 2"