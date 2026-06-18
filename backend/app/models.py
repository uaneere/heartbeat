"""
Pydantic модели - КОНТРАКТ с мобильным приложением
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from enum import Enum
class ActivityType(str, Enum):
    """Типы активностей"""
    RUNNING = "running"
    WALKING = "walking"
    GYM = "gym"
    CYCLING = "cycling"
    MEDITATION = "meditation"
    SLEEP = "sleep"
    STUDYING = "studying"
    YOGA = "yoga"
    GAMING = "gaming"


class GoalType(str, Enum):
    """Цели тренировки"""
    FAT_BURNING = "fat_burning"
    SPRINT = "sprint"
    RECOVERY = "recovery"
    GENERAL = "general_fitness"
    STRESS_REDUCTION = "stress_reduction"
    WARMUP = "warmup"
    COOLDOWN = "cooldown"


class TempoPreference(str, Enum):
    """Предпочтение темпа"""
    SLOW = "slow"
    MEDIUM = "medium"
    FAST = "fast"


class EnergyLevel(str, Enum):
    """Уровень энергии трека"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Profile(BaseModel):
    """Профиль пользователя"""
    age: int = Field(..., ge=5, le=100, description="Возраст")
    resting_hr: int = Field(..., ge=40, le=120, description="Пульс в покое")
    avg_active_hr: Optional[int] = Field(None, ge=80, le=220, description="Средний активный пульс")
    preferred_genres: List[str] = Field(default=[], description="Предпочитаемые жанры")
    conditions: List[str] = Field(default=[], description="Медицинские показания")


class SessionContext(BaseModel):
    """Контекст сессии"""
    activity_type: ActivityType = Field(..., description="Тип активности")
    goal: GoalType = Field(default=GoalType.GENERAL, description="Цель")
    tempo_preference: TempoPreference = Field(default=TempoPreference.MEDIUM, description="Предпочтение темпа")


# === REQUEST / RESPONSE модели ===

class StartSessionRequest(BaseModel):
    """Запрос на начало сессии"""
    profile: Profile
    session: SessionContext


class StartSessionResponse(BaseModel):
    """Ответ на начало сессии"""
    session_id: UUID
    current_hr: int
    tick: int
    message: str = "Session started successfully"


class HeartRateUpdate(BaseModel):
    """Обновление пульса"""
    current_hr: int = Field(..., ge=30, le=220, description="Текущий пульс")
    movement_intensity: float = Field(0.5, ge=0.0, le=1.0, description="Интенсивность движения")
    stress_level: float = Field(0.3, ge=0.0, le=1.0, description="Уровень стресса")


class HeartRateResponse(BaseModel):
    """Ответ на обновление пульса"""
    success: bool
    tick: int
    current_hr: int
    heart_rate_zone: int
    heart_rate_zone_label: str
    target_bpm: int
    message: str = "OK"


class GenerateRequest(BaseModel):
    """Запрос на генерацию музыки"""
    force_regenerate: bool = Field(False, description="Принудительно перегенерировать")
    seed: Optional[int] = Field(None, description="Seed для воспроизводимости")


class GenerateResponse(BaseModel):
    """Ответ с сгенерированной музыкой"""
    success: bool
    audio_url: str = Field(..., description="URL для скачивания аудио")
    bpm: int = Field(..., description="Target BPM")
    genre: str = Field(..., description="Жанр")
    energy: EnergyLevel = Field(..., description="Энергия трека")
    mood: str = Field(..., description="Настроение")
    track_title: str = Field(..., description="Название трека для UI")
    duration_seconds: int = Field(..., description="Длительность в секундах")
    tick: int = Field(..., description="Номер тика")
    fragment_file: str = Field(..., description="Имя файла")
    heart_rate_zone: int = Field(..., description="Зона пульса 1-5")
    heart_rate_zone_label: str = Field(..., description="Название зоны пульса")


class SessionStatusResponse(BaseModel):
    """Статус сессии"""
    session_id: UUID
    tick: int
    current_hr: int
    activity_type: ActivityType
    goal: GoalType
    tempo_preference: TempoPreference
    is_active: bool
    heart_rate_zone: int
    heart_rate_zone_label: str
    target_bpm: int
    last_bpm: Optional[int] = None
    last_genre: Optional[str] = None


class UpdateSessionContextRequest(BaseModel):
    """Обновление настроек активной сессии"""
    session: SessionContext


class HealthResponse(BaseModel):
    """Health check ответ"""
    status: str
    model_ready: bool
    model_key: str
    chunk_duration_sec: float
    version: str = "1.0.0"