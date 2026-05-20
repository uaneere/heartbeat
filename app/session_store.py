from dataclasses import dataclass
from uuid import UUID, uuid4

from app.schemas import RealTimeSignals, SessionContext, StaticProfile


@dataclass
class SessionState:
    session_id: UUID
    profile: StaticProfile
    context: SessionContext
    realtime: RealTimeSignals
    previous_hr: int | None = None
    previous_bpm: int | None = None
    previous_genre: str | None = None
    previous_energy: str | None = None
    previous_activity_type: str | None = None
    last_chunk_path: str | None = None
    last_fragment_path: str | None = None
    last_transition_path: str | None = None
    last_fade_seconds: float = 2.5
    tick: int = 0


SESSIONS: dict[UUID, SessionState] = {}


def create_session(profile: StaticProfile, context: SessionContext, initial_hr: int) -> SessionState:
    state = SessionState(
        session_id=uuid4(),
        profile=profile,
        context=context,
        realtime=RealTimeSignals(
            current_hr=initial_hr,
            movement_intensity=0.2,
            stress_level=0.1,
            cadence=0,
            steps=0,
        ),
        previous_activity_type=context.activity_type,
    )
    SESSIONS[state.session_id] = state
    return state


def get_session(session_id: UUID) -> SessionState | None:
    return SESSIONS.get(session_id)
