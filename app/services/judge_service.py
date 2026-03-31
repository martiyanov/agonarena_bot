import json
import logging
from pathlib import Path
from typing import Literal, Sequence

from pydantic import BaseModel

from app.db.models import Duel, DuelMessage, JudgeResult
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "judges.md"


class JudgeType:
    OWNER = "owner"
    TEAM = "team"
    SENDER = "sending_to_negotiation"


class JudgeContext(BaseModel):
    judge_type: Literal["owner", "team", "sending_to_negotiation"]
    scenario_code: str
    duel_id: int
    round1_transcript: str
    round2_transcript: str


class JudgeVerdict(BaseModel):
    judge_type: Literal["owner", "team", "sending_to_negotiation"]
    winner: Literal["user", "ai", "draw"]
    comment: str
    round1_comment: str = ""
    round2_comment: str = ""


class JudgeService:
    """Судьи с LLM-first режимом и rule-based fallback."""

    JUDGE_LABELS = {
        JudgeType.OWNER: "собственник",
        JudgeType.TEAM: "команда",
        JudgeType.SENDER: "отправляющий на переговоры",
    }

    def __init__(self, llm_service: LLMService | None = None):
        self.llm_service = llm_service or LLMService()
        self.system_prompt = PROMPT_PATH.read_text(encoding="utf-8") if PROMPT_PATH.exists() else ""

    async def run_single_judge(self, context: JudgeContext) -> JudgeVerdict:
        if self.llm_service.is_configured():
            try:
                raw = await self.llm_service.generate_text(
                    system_prompt=self.system_prompt,
                    user_prompt=self._build_user_prompt(context),
                    temperature=0.2,
                )
                logger.info("LLM judge response: %s", raw[:200])
                data = json.loads(raw)
                logger.info("Parsed verdict: winner=%s, has_r1=%s, has_r2=%s", 
                           data.get("winner"), 
                           bool(data.get("round1_comment")),
                           bool(data.get("round2_comment")))
                return JudgeVerdict(
                    judge_type=context.judge_type,
                    winner=data.get("winner", "draw"),
                    comment=data.get("comment", "Судья не дал развёрнутый комментарий."),
                    round1_comment=data.get("round1_comment", ""),
                    round2_comment=data.get("round2_comment", ""),
                )
            except Exception as e:
                logger.error("LLM judge failed: %s", e)
                pass

        return self._fallback_verdict(context)

    async def run_all_judges(self, contexts: Sequence[JudgeContext]) -> list[JudgeVerdict]:
        results: list[JudgeVerdict] = []
        for context in contexts:
            results.append(await self.run_single_judge(context))
        return results

    async def save_verdict(self, duel: Duel, verdict: JudgeVerdict) -> JudgeResult:
        return JudgeResult(
            duel_id=duel.id,
            judge_type=verdict.judge_type,
            winner=verdict.winner,
            comment=verdict.comment,
            round1_comment=verdict.round1_comment,
            round2_comment=verdict.round2_comment,
        )

    def build_transcript(self, messages: Sequence[DuelMessage]) -> str:
        lines: list[str] = []
        for msg in messages:
            prefix = "Вы" if msg.author == "user" else "AI"
            lines.append(f"{prefix}: {msg.content}")
        return "\n".join(lines) if lines else "(пусто)"

    def build_contexts_for_duel(
        self,
        *,
        duel: Duel,
        scenario_code: str,
        round1_messages: Sequence[DuelMessage],
        round2_messages: Sequence[DuelMessage],
    ) -> list[JudgeContext]:
        round1 = self.build_transcript(round1_messages)
        round2 = self.build_transcript(round2_messages)
        return [
            JudgeContext(
                judge_type=judge_type,
                scenario_code=scenario_code,
                duel_id=duel.id,
                round1_transcript=round1,
                round2_transcript=round2,
            )
            for judge_type in (JudgeType.OWNER, JudgeType.TEAM, JudgeType.SENDER)
        ]

    def summarize_final_verdict(self, verdicts: Sequence[JudgeVerdict]) -> str:
        wins = {"user": 0, "ai": 0, "draw": 0}
        for item in verdicts:
            wins[item.winner] += 1

        winner = max(wins, key=wins.get)
        if wins["user"] == wins["ai"]:
            winner = "draw"

        header = {
            "user": "Победа пользователя по мнению большинства судей.",
            "ai": "Победа AI по мнению большинства судей.",
            "draw": "Судьи сочли поединок ничьей.",
        }[winner]
        details = "\n".join(
            f"- {self.JUDGE_LABELS.get(item.judge_type, item.judge_type)}: {item.comment}" for item in verdicts
        )
        return f"{header}\n{details}"

    def _build_user_prompt(self, context: JudgeContext) -> str:
        return (
            f"Judge type: {context.judge_type}\n"
            f"Scenario code: {context.scenario_code}\n"
            f"Round 1 transcript:\n{context.round1_transcript}\n\n"
            f"Round 2 transcript:\n{context.round2_transcript}\n\n"
            "Return JSON with fields: winner, comment, round1_comment, round2_comment. All comments must be in Russian.\n"
            "round1_comment: Comment specifically about Round 1 performance and outcome.\n"
            "round2_comment: Comment specifically about Round 2 performance and outcome.\n"
            "comment: Overall summary comment covering both rounds."
        )

    def _fallback_verdict(self, context: JudgeContext) -> JudgeVerdict:
        transcript_len = len(context.round1_transcript) + len(context.round2_transcript)
        winner = "draw" if transcript_len < 1200 else "user"

        if context.judge_type == JudgeType.OWNER:
            comment = "Смотрю на устойчивость решения и экономику: позиция выглядела собранной, но без явного доминирования."
            round1_comment = "Обе стороны проявили себя сдержанно, без явного преимущества."
            round2_comment = "Смена ролей позволила лучше раскрыть позиции, но без кардинальных изменений."
        elif context.judge_type == JudgeType.TEAM:
            comment = "С точки зрения команды важны ясность и выполнимость; результат выглядит рабочим, но компромиссным."
            round1_comment = "Первоначальные позиции были ясны, но требуют проработки деталей реализации."
            round2_comment = "Диалог во второй половине показал готовность к конструктивному взаимодействию."
        else:
            comment = "С точки зрения переговорщика, диалог сохранил пространство для манёвра и не разрушил отношения сторон."
            round1_comment = "Стороны установили контакт, но остались в своих позициях."
            round2_comment = "Взаимодействие стало более продуктивным, появились элементы сотрудничества."

        return JudgeVerdict(
            judge_type=context.judge_type, 
            winner=winner, 
            comment=comment,
            round1_comment=round1_comment,
            round2_comment=round2_comment
        )
