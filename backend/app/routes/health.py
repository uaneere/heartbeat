"""Health check эндпоинты"""

from fastapi import APIRouter

from app.generator import is_model_ready, get_active_model_info
from app.models import HealthResponse

router = APIRouter(tags=["health"])

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Проверка состояния сервиса"""
    info = get_active_model_info()
    return HealthResponse(
        status="ready" if info["ready"] else "loading",
        model_ready=info["ready"],
        model_key=info["model_key"],
        chunk_duration_sec=info["chunk_duration_sec"],
    )

@router.get("/ready")
async def ready():
    """Алиас для health check (совместимость)"""
    info = get_active_model_info()
    return {"ready": info["ready"], **info}

@router.get("/model")
async def model_info():
    """Информация о текущей модели MusicGen"""
    return get_active_model_info()