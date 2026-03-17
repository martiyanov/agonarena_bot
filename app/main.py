from fastapi import FastAPI

from app.config import settings

app = FastAPI(title="Agon Arena Bot", version="0.1.0")


@app.get("/health")
def healthcheck() -> dict:
    return {
        "status": "ok",
        "app": "agonarena_bot",
        "env": settings.app_env,
    }
