from fastapi import APIRouter, HTTPException

from app.db.session import AsyncSessionLocal
from app.services import DuelService, ScenarioService

router = APIRouter(prefix="/api")


@router.get("/scenarios")
async def list_scenarios() -> list[dict]:
    async with AsyncSessionLocal() as session:
        items = await ScenarioService().list_active(session)
        return [
            {
                "code": item.code,
                "title": item.title,
                "description": item.description,
                "role_a_name": item.role_a_name,
                "role_b_name": item.role_b_name,
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
