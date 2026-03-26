import pytest
import httpx

from app.main import app


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "description",
    [
        "Клиент заказал услугу, сроки сорвали, клиент требует скидку и извинений.",
        "Я руководитель отдела, ко мне пришёл сотрудник с жалобой на переработки, он хочет повышение зарплаты.",
        "Стартап и инвестор: инвестор недоволен темпами роста, хочет жёсткий контроль и замену части команды.",
    ],
)
async def test_custom_scenario_pipeline(description: str) -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/test/custom-scenario", json={"description": description})

    assert resp.status_code == 200
    data = resp.json()

    # Проверяем базовую структуру сценария
    for key in [
        "title",
        "description",
        "role_a_name",
        "role_a_goal",
        "role_b_name",
        "role_b_goal",
        "opening_line_a",
        "opening_line_b",
    ]:
        assert key in data, f"missing key: {key}"
        assert isinstance(data[key], str), f"{key} must be a string"
        assert data[key].strip() != "", f"{key} must not be empty"


@pytest.mark.asyncio
async def test_custom_scenario_invalid_text_returns_400() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Намеренно даём текст, который с высокой вероятностью поломает JSON-модель
        resp = await client.post("/api/test/custom-scenario", json={"description": ""})

    assert resp.status_code in {400, 422}
