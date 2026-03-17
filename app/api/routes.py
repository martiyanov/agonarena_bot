from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.session import AsyncSessionLocal
from app.services import DuelService, JudgeService, OpponentService, OpponentTurnContext, ScenarioService

router = APIRouter(prefix="/api")


class TurnRequest(BaseModel):
    text: str


@router.get("/scenarios")
async def list_scenarios() -> list[dict]:
    async with AsyncSessionLocal() as session:
        items = await ScenarioService().list_active(session)
        return [
            {
                "code": item.code,
                "title": item.title,
                "description": item.description,
                "category": item.category,
                "difficulty": item.difficulty,
                "role_a_name": item.role_a_name,
                "role_a_goal": item.role_a_goal,
                "role_b_name": item.role_b_name,
                "role_b_goal": item.role_b_goal,
            }
            for item in items
        ]


@router.post("/duels/start/{scenario_code}")
async def start_duel(scenario_code: str, telegram_user_id: int = 127583377) -> dict:
    async with AsyncSessionLocal() as session:
        duel_service = DuelService()
        scenario = await duel_service.get_scenario_by_code(session, scenario_code)
        if scenario is None:
            raise HTTPException(status_code=404, detail="Scenario not found")

        duel = await duel_service.create_duel(session, telegram_user_id=telegram_user_id, scenario=scenario)
        rounds = await duel_service.get_duel_rounds(session, duel.id)

        return {
            "duel_id": duel.id,
            "status": duel.status,
            "scenario": scenario.code,
            "rounds": [
                {
                    "round_number": item.round_number,
                    "user_role": item.user_role,
                    "ai_role": item.ai_role,
                    "opening_line": item.opening_line,
                }
                for item in rounds
            ],
        }


@router.get("/duels/{duel_id}")
async def get_duel(duel_id: int) -> dict:
    async with AsyncSessionLocal() as session:
        duel_service = DuelService()
        duel = await duel_service.get_duel(session, duel_id)
        if duel is None:
            raise HTTPException(status_code=404, detail="Duel not found")

        rounds = await duel_service.get_duel_rounds(session, duel.id)
        judge_results = await duel_service.list_judge_results(session, duel.id)

        return {
            "duel_id": duel.id,
            "status": duel.status,
            "current_round_number": duel.current_round_number,
            "final_verdict": duel.final_verdict,
            "rounds": [
                {
                    "round_number": item.round_number,
                    "status": item.status,
                    "user_role": item.user_role,
                    "ai_role": item.ai_role,
                    "opening_line": item.opening_line,
                }
                for item in rounds
            ],
            "judge_results": [
                {"judge_type": item.judge_type, "winner": item.winner, "comment": item.comment}
                for item in judge_results
            ],
        }


@router.post("/duels/{duel_id}/turn")
async def submit_turn(duel_id: int, payload: TurnRequest) -> dict:
    async with AsyncSessionLocal() as session:
        duel_service = DuelService()
        duel = await duel_service.get_duel(session, duel_id)
        if duel is None:
            raise HTTPException(status_code=404, detail="Duel not found")
        if duel.status == "finished":
            raise HTTPException(status_code=409, detail="Duel already finished")

        scenario = await duel_service.get_scenario_by_id(session, duel.scenario_id)
        round_obj = await duel_service.get_round(session, duel.id, duel.current_round_number)
        if round_obj is None:
            raise HTTPException(status_code=404, detail="Round not found")

        await duel_service.ensure_round_started(duel, round_obj)
        await duel_service.add_message(session, duel.id, round_obj.round_number, "user", payload.text)
        history = await duel_service.list_messages_for_round(session, duel.id, round_obj.round_number)
        opponent_service = OpponentService()
        ai_reply = await opponent_service.generate_reply(
            OpponentTurnContext(
                scenario_title=scenario.title if scenario else "",
                scenario_description=scenario.description if scenario else "",
                round_number=round_obj.round_number,
                user_role=round_obj.user_role,
                ai_role=round_obj.ai_role,
                opening_line=round_obj.opening_line,
                history=history,
            )
        )
        await duel_service.add_message(session, duel.id, round_obj.round_number, "ai", ai_reply)
        await session.commit()

        return {
            "duel_id": duel.id,
            "round_number": round_obj.round_number,
            "status": duel.status,
            "ai_reply": ai_reply,
        }


@router.post("/duels/{duel_id}/next-round")
async def next_round(duel_id: int) -> dict:
    async with AsyncSessionLocal() as session:
        duel_service = DuelService()
        duel = await duel_service.get_duel(session, duel_id)
        if duel is None:
            raise HTTPException(status_code=404, detail="Duel not found")
        if duel.current_round_number != 1:
            raise HTTPException(status_code=409, detail="Duel is not on round 1")

        round_1 = await duel_service.get_round(session, duel.id, 1)
        round_2 = await duel_service.get_round(session, duel.id, 2)
        if round_1 is None or round_2 is None:
            raise HTTPException(status_code=404, detail="Rounds not found")

        await duel_service.complete_round(duel, round_1)
        await duel_service.ensure_round_started(duel, round_2)
        await session.commit()

        return {
            "duel_id": duel.id,
            "status": duel.status,
            "current_round_number": duel.current_round_number,
            "next_round": {
                "round_number": round_2.round_number,
                "user_role": round_2.user_role,
                "ai_role": round_2.ai_role,
                "opening_line": round_2.opening_line,
            },
        }


@router.post("/duels/{duel_id}/finish")
async def finish_duel(duel_id: int) -> dict:
    async with AsyncSessionLocal() as session:
        duel_service = DuelService()
        judge_service = JudgeService()

        duel = await duel_service.get_duel(session, duel_id)
        if duel is None:
            raise HTTPException(status_code=404, detail="Duel not found")

        round_1 = await duel_service.get_round(session, duel.id, 1)
        round_2 = await duel_service.get_round(session, duel.id, 2)
        scenario = await duel_service.get_scenario_by_id(session, duel.scenario_id)
        if round_1 is None or round_2 is None or scenario is None:
            raise HTTPException(status_code=404, detail="Duel data is incomplete")

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

        return {
            "duel_id": duel.id,
            "status": duel.status,
            "final_verdict": final_verdict,
            "judge_results": [v.model_dump() for v in verdicts],
        }
