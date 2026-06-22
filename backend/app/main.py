"""FastAPI приложение"""

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import CORS_ORIGINS, PRELOAD_ON_STARTUP, AUDIO_DIR, STATIC_TRACKS_PATH
from app.routes import sessions, generate, health

"""Настройка логирования"""
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


"""Lifespan для предзагрузки модели"""
async def lifespan(app: FastAPI):
    """Lifecycle manager"""
    if PRELOAD_ON_STARTUP:
        logger.info("Preloading MusicGen model...")
        try:
            from app.generator import preload_model
            preload_model()
            logger.info("MusicGen preloaded successfully")
        except Exception as e:
            logger.error(f"Failed to preload model: {e}")
    yield

"""Создание приложения"""
app = FastAPI(
    title="Heartbeat Music Generator API",
    description="API for generating music based on heart rate and activity",
    version="1.0.0",
    lifespan=lifespan,
)

"""CORS middleware"""
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

"""Регистрация роутеров"""
app.include_router(health.router)
app.include_router(sessions.router)
app.include_router(generate.router)

"""Статическая раздача сгенерированных треков для потокового AVPlayer"""
os.makedirs(AUDIO_DIR, exist_ok=True)
app.mount(STATIC_TRACKS_PATH, StaticFiles(directory=AUDIO_DIR), name="tracks")

@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "service": "Heartbeat Music Generator",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }