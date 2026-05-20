import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.musicgen_config import PRELOAD_ON_STARTUP
from app.routes import router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if PRELOAD_ON_STARTUP:
        logger.info("Предзагрузка MusicGen (может занять несколько минут)...")
        try:
            from app.generator import preload_model

            preload_model()
            logger.info("MusicGen предзагружен")
        except Exception as exc:
            logger.error("Не удалось предзагрузить MusicGen: %s", exc)
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(router)
