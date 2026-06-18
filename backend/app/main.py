"""
FastAPI приложение
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS, PRELOAD_ON_STARTUP
from app.routes import sessions, generate, health

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Lifespan для предзагрузки модели
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


# Создаем приложение
app = FastAPI(
    title="Heartbeat Music Generator API",
    description="API for generating music based on heart rate and activity",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Регистрируем роутеры
app.include_router(health.router)
app.include_router(sessions.router)
app.include_router(generate.router)


@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "service": "Heartbeat Music Generator",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }