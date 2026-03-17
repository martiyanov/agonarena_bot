from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.db.init_db import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Agon Arena Bot", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def healthcheck() -> dict:
    return {
        "status": "ok",
        "app": "agonarena_bot",
        "env": settings.app_env,
    }
