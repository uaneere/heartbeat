from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class StaticProfile(BaseModel):
    age: int = Field(..., ge=5, le=100)
    sex: Optional[str] = None
    weight: Optional[float] = Field(default=None, ge=20, le=300)
    height: Optional[float] = Field(default=None, ge=100, le=250)
    resting_hr: int = Field(..., ge=30, le=120)
    avg_active_hr: Optional[int] = Field(default=None, ge=50, le=220)
    blood_pressure: Optional[str] = None
    conditions: List[str] = []
    preferred_genres: List[str] = []


class SessionContext(BaseModel):
    activity_type: str
    goal: str = "general_fitness"
    manual_tempo_preference: str = "medium"
    time_signature: str = "4/4"


class RealTimeSignals(BaseModel):
    current_hr: int = Field(..., ge=30, le=220)
    movement_intensity: float = Field(default=0.0, ge=0.0, le=1.0)
    stress_level: float = Field(default=0.0, ge=0.0, le=1.0)
    cadence: Optional[int] = Field(default=None, ge=0, le=260)
    steps: Optional[int] = Field(default=None, ge=0)


class InputData(BaseModel):
    profile: StaticProfile
    session: SessionContext
    realtime: RealTimeSignals
    previous_hr: Optional[int] = Field(default=None, ge=30, le=220)
    previous_activity_type: Optional[str] = None
    previous_bpm: Optional[int] = Field(default=None, ge=40, le=220)
    force_regenerate: bool = False
    seed: Optional[int] = None
    generate_audio: bool = False


class PlaybackSegmentOut(BaseModel):
    file: str
    start: float
    duration: float
    kind: str = "segment"


class OutputData(BaseModel):
    target_bpm: int
    intensity: float
    target_energy: str
    target_genre: str
    mood: str
    mode: str
    state_changed: bool
    should_regenerate: bool
    transition_mode: str = "none"
    prompt: str
    file: str
    fragment_file: str = ""
    transition_file: str = ""
    fade_seconds: float = 2.5
    generation_method: str = "none"
    playback: List[PlaybackSegmentOut] = []


class SessionStartRequest(BaseModel):
    profile: StaticProfile
    session: SessionContext


class SessionStartResponse(BaseModel):
    session_id: UUID
    current_hr: int
    tick: int


class SessionTickRequest(BaseModel):
    movement_intensity: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    stress_level: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class SessionTickResponse(BaseModel):
    session_id: UUID
    tick: int
    realtime: RealTimeSignals


class SessionGenerateRequest(BaseModel):
    movement_intensity: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    stress_level: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    force_regenerate: bool = False
    generate_audio: bool = True
    seed: Optional[int] = None


class SessionGenerateResponse(BaseModel):
    session_id: UUID
    tick: int
    result: OutputData


class SessionContextPatchRequest(BaseModel):
    activity_type: Optional[str] = None
    goal: Optional[str] = None
    manual_tempo_preference: Optional[str] = None
    time_signature: Optional[str] = None


class SessionContextResponse(BaseModel):
    session_id: UUID
    context: SessionContext