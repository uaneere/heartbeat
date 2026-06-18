"""
Эндпоинты управления сессиями
"""

from uuid import UUID
from fastapi import APIRouter, HTTPException

from app.models import (
    StartSessionRequest,
    StartSessionResponse,
    HeartRateUpdate,
    HeartRateResponse,
    SessionStatusResponse,
    ActivityType,
    GoalType,
)
from app.session_store import create_session, get_session, get_active_sessions
from app.decision_engine import calculate_max_heart_rate

router = APIRouter(prefix="/api/v1", tags=["sessions"])


@router.post("/session/start", response_model=StartSessionResponse)
async def start_session(req: StartSessionRequest):
    """
    Начать новую сессию тренировки
    
    Создает сессию с профилем пользователя и контекстом активности.
    Возвращает session_id для дальнейших запросов.
    """
    initial_hr = req.profile.resting_hr
    session = create_session(req.profile, req.session, initial_hr)
    
    return StartSessionResponse(
        session_id=session.session_id,
        current_hr=initial_hr,
        tick=0,
        message="Session started successfully",
    )


@router.post("/session/{session_id}/heartrate", response_model=HeartRateResponse)
async def update_heartrate(session_id: UUID, data: HeartRateUpdate):
    """
    Обновить пульс и параметры активности
    
    Мобильное приложение вызывает этот эндпоинт каждые 2-3 секунды
    с текущим пульсом пользователя.
    """
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session.current_hr = data.current_hr
    session.movement_intensity = data.movement_intensity
    session.stress_level = data.stress_level
    session.tick += 1
    
    return HeartRateResponse(
        success=True,
        tick=session.tick,
        message="OK",
    )


@router.get("/session/{session_id}/status", response_model=SessionStatusResponse)
async def get_session_status(session_id: UUID):
    """
    Получить статус сессии
    """
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return SessionStatusResponse(
        session_id=session.session_id,
        tick=session.tick,
        current_hr=session.current_hr,
        activity_type=session.context.activity_type,
        goal=session.context.goal,
        is_active=True,
    )


@router.get("/sessions")
async def list_sessions():
    """Список всех активных сессий (для отладки)"""
    from app.session_store import get_active_sessions
    return {"sessions": get_active_sessions()}


@router.delete("/session/{session_id}")
async def delete_session(session_id: UUID):
    """Завершить сессию"""
    from app.session_store import delete_session
    
    if not delete_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"success": True, "message": "Session ended"}