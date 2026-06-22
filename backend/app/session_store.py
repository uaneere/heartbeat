"""In-memory хранилище сессий"""

from uuid import UUID, uuid4
from dataclasses import dataclass, field
from typing import Dict, Optional

from app.models import Profile, SessionContext, ActivityType, GoalType

@dataclass
class SessionState:
    """Состояние сессии"""
    session_id: UUID
    profile: Profile
    context: SessionContext
    current_hr: int
    tick: int = 0
    last_fragment_path: Optional[str] = None
    last_raw_fragment_path: Optional[str] = None
    last_loop_bridge_path: Optional[str] = None
    last_transition_path: Optional[str] = None
    fragment_index: int = 0
    last_bpm: Optional[int] = None
    last_genre: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "session_id": str(self.session_id),
            "tick": self.tick,
            "current_hr": self.current_hr,
            "activity_type": self.context.activity_type.value,
            "goal": self.context.goal.value,
        }

"""Хранилище сессий"""
_sessions: Dict[UUID, SessionState] = {}

def create_session(profile: Profile, context: SessionContext, initial_hr: int) -> SessionState:
    """Создание новой сессии"""
    session = SessionState(
        session_id=uuid4(),
        profile=profile,
        context=context,
        current_hr=initial_hr,
    )
    _sessions[session.session_id] = session
    return session

def get_session(session_id: UUID) -> Optional[SessionState]:
    """Получение сессии по ID"""
    return _sessions.get(session_id)

def update_session(session_id: UUID, **kwargs) -> Optional[SessionState]:
    """Обновление сессии"""
    session = get_session(session_id)
    if session:
        for key, value in kwargs.items():
            if hasattr(session, key):
                setattr(session, key, value)
    return session

def delete_session(session_id: UUID) -> bool:
    """Удаление сессии"""
    if session_id in _sessions:
        del _sessions[session_id]
        return True
    return False

def get_active_sessions() -> list[dict]:
    """Список активных сессий"""
    return [s.to_dict() for s in _sessions.values()]