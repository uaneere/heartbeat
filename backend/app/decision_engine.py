"""
Логика выбора BPM, жанра и настроения.
Поток данных:
  HealthKit -> current_hr (каждые несколько сек)
  Профиль   -> age, resting_hr, preferred_genres, conditions
  Сессия    -> activity_type, goal, tempo_preference
  current_hr + профиль -> intensity, зона пульса, target BPM
  conditions           -> потолок BPM, шаг смены BPM, спокойное настроение
  preferred_genres     -> жанр (с фильтром по активности)
"""

import math
from dataclasses import dataclass
from typing import List, Optional

from app.models import ActivityType, GoalType, TempoPreference, EnergyLevel

"""Синонимы жанров для сопоставления UI-предпочтений с жанрами активности"""
_GENRE_ALIASES: dict[str, set[str]] = {
    "lofi": {"lofi", "lo-fi", "chill", "downtempo", "chill electronic"},
    "electronic": {
        "electronic", "edm", "house", "techno", "trance", "synthwave",
        "chiptune", "progressive house", "hardstyle", "drum and bass",
    },
    "rock": {"rock", "metal"},
    "classical": {"classical", "piano", "acoustic"},
    "jazz": {"jazz"},
    "pop": {"pop"},
    "phonk": {"phonk", "drift"},
    "ambient": {"ambient", "meditation", "nature sounds", "white noise"},
}

"""Рекомендуемый целевой BPM по виду активности (без учёта текущего пульса)"""
_ACTIVITY_TARGET_BPM: dict[ActivityType, int] = {
    ActivityType.SLEEP: 60,
    ActivityType.MEDITATION: 70,
    ActivityType.STUDYING: 85,
    ActivityType.WALKING: 105,
    ActivityType.YOGA: 95,
    ActivityType.CYCLING: 120,
    ActivityType.GYM: 125,
    ActivityType.RUNNING: 130,
    ActivityType.GAMING: 110,
}

"""Дефолтные жанры по активности (если нет подходящих предпочтений)"""
_ACTIVITY_DEFAULT_GENRES: dict[ActivityType, list[str]] = {
    ActivityType.RUNNING: ["edm", "techno", "drum and bass", "house"],
    ActivityType.GYM: ["techno", "metal", "rock", "hardstyle"],
    ActivityType.CYCLING: ["house", "progressive house", "trance"],
    ActivityType.WALKING: ["chill electronic", "lofi", "downtempo"],
    ActivityType.YOGA: ["ambient", "lofi", "piano", "acoustic"],
    ActivityType.MEDITATION: ["ambient", "lofi", "meditation", "nature sounds"],
    ActivityType.SLEEP: ["ambient", "piano", "white noise"],
    ActivityType.STUDYING: ["lofi", "classical", "jazz", "ambient"],
    ActivityType.GAMING: ["electronic", "synthwave", "chiptune"],
}

"""Жанры, несовместимые с видом активности (предпочтения пользователя фильтруются)"""
_ACTIVITY_INCOMPATIBLE_GENRES: dict[ActivityType, set[str]] = {
    ActivityType.MEDITATION: {
        "rock", "metal", "phonk", "electronic", "pop",
        "hardstyle", "drum and bass", "techno", "edm", "house",
        "trance", "synthwave", "chiptune",
    },
    ActivityType.SLEEP: {
        "rock", "metal", "phonk", "electronic", "pop", "jazz",
        "hardstyle", "drum and bass", "techno", "edm", "house",
        "trance", "synthwave", "chiptune",
    },
    ActivityType.YOGA: {
        "rock", "metal", "phonk", "electronic",
        "hardstyle", "drum and bass", "techno", "edm",
        "synthwave", "chiptune",
    },
    ActivityType.STUDYING: {
        "metal", "rock", "phonk", "hardstyle", "drum and bass",
        "techno", "edm", "house",
    },
    ActivityType.WALKING: {"metal", "phonk", "hardstyle", "drum and bass"},
    ActivityType.RUNNING: {
        "ambient", "meditation", "nature sounds", "white noise",
        "classical", "piano", "acoustic",
    },
    ActivityType.GYM: {
        "ambient", "meditation", "nature sounds", "white noise",
        "lofi", "classical", "piano", "acoustic",
    },
    ActivityType.CYCLING: {"ambient", "meditation", "white noise", "lofi"},
    ActivityType.GAMING: {
        "ambient", "meditation", "nature sounds", "white noise",
        "classical", "piano", "acoustic",
    },
}

@dataclass(frozen=True)
class ConditionEffect:
    """Единый источник правды: как заболевание влияет на музыку"""
    max_bpm: int | None = None
    min_bpm: int | None = None
    calming_mood: bool = False
    bpm_step: int | None = None

"""Заболевания из профиля -> ограничения генерации"""
CONDITION_EFFECTS: dict[str, ConditionEffect] = {
    "hypertension": ConditionEffect(max_bpm=120, calming_mood=True, bpm_step=5),
    "arrhythmia": ConditionEffect(max_bpm=110, calming_mood=True, bpm_step=5),
    "ischemic_heart_disease": ConditionEffect(max_bpm=115, calming_mood=True, bpm_step=5),
    "asthma": ConditionEffect(max_bpm=125),
    "diabetes": ConditionEffect(min_bpm=70),
}

def calculate_max_heart_rate(age: int) -> int:
    """Максимальный пульс по возрасту (формула Tanaka)"""
    return int(208 - 0.7 * age)

def calculate_intensity(current_hr: int, resting_hr: int, max_hr: int) -> float:
    """Интенсивность нагрузки (0-1)"""
    hr_range = max_hr - resting_hr
    if hr_range <= 0:
        return 0.5
    intensity = (current_hr - resting_hr) / hr_range
    return max(0.0, min(1.0, intensity))

def get_heart_rate_zone(intensity: float) -> int:
    """Зона пульса (1-5)"""
    if intensity < 0.5:
        return 1  # Recovery
    elif intensity < 0.65:
        return 2  # Fat burn
    elif intensity < 0.8:
        return 3  # Cardio
    elif intensity < 0.9:
        return 4  # Hard
    else:
        return 5  # Max
        
def get_heart_rate_zone_label(zone: int) -> str:
    """Название зоны пульса"""
    labels = {
        1: "Восстановление",
        2: "Жиросжигание",
        3: "Кардио",
        4: "Анаэробная",
        5: "Максимум",
    }
    return labels.get(zone, "Кардио")

def _normalize_genre(name: str) -> str:
    return name.lower().strip().replace("-", "")

"""Максимальный шаг изменения BPM между отрывками (по умолчанию)"""
_DEFAULT_BPM_STEP = 10

def _genre_alias_set(genre: str) -> set[str]:
    """Все синонимы жанра для сопоставления"""
    norm = _normalize_genre(genre)
    for aliases in _GENRE_ALIASES.values():
        norm_aliases = {_normalize_genre(x) for x in aliases}
        if norm in norm_aliases:
            return norm_aliases
    return {norm}

def _is_genre_incompatible(genre: str, activity: ActivityType) -> bool:
    """Жанр несовместим с активностью, если пересекается с чёрным списком"""
    banned = _ACTIVITY_INCOMPATIBLE_GENRES.get(activity)
    if not banned:
        return False
    genre_aliases = _genre_alias_set(genre)
    for banned_genre in banned:
        if genre_aliases & _genre_alias_set(banned_genre):
            return True
    return False

def _filter_compatible_genres(genres: List[str], activity: ActivityType) -> List[str]:
    """Оставляет только жанры, совместимые с активностью"""
    return [g for g in genres if not _is_genre_incompatible(g, activity)]

def _pick_from_defaults(activity: ActivityType, intensity: float) -> str:
    """Жанр из дефолтного списка активности с учётом интенсивности"""
    genres = _ACTIVITY_DEFAULT_GENRES.get(activity, ["electronic", "house"])
    if intensity > 0.7:
        return genres[0]
    if intensity < 0.3:
        return genres[-1]
    return genres[min(1, len(genres) - 1)]

def _pick_rotating(
    candidates: List[str],
    fragment_index: int,
    last_genre: Optional[str],
) -> str:
    """Чередует жанры из списка, стараясь не повторять предыдущий"""
    if len(candidates) == 1:
        return candidates[0]
    pool = candidates
    if last_genre:
        different = [g for g in candidates if not _genres_match(g, last_genre)]
        if different:
            pool = different
    return pool[fragment_index % len(pool)]

def _genres_match(activity_genre: str, preference: str) -> bool:
    """Проверяет, относятся ли два жанра к одной группе синонимов"""
    a = _normalize_genre(activity_genre)
    p = _normalize_genre(preference)
    if p in a or a in p:
        return True
    for aliases in _GENRE_ALIASES.values():
        norm_aliases = {_normalize_genre(x) for x in aliases}
        if p in norm_aliases and a in norm_aliases:
            return True
    return False

def _apply_conditions_bpm_cap(bpm: int, conditions: List[str]) -> int:
    """Ограничения BPM при хронических заболеваниях"""
    capped = bpm
    for condition in conditions:
        effect = CONDITION_EFFECTS.get(condition.lower())
        if not effect:
            continue
        if effect.max_bpm is not None:
            capped = min(capped, effect.max_bpm)
        if effect.min_bpm is not None:
            capped = max(capped, effect.min_bpm)
    return capped

def _bpm_step_for_conditions(conditions: List[str]) -> int:
    """Меньший шаг BPM при сердечно-сосудистых ограничениях"""
    steps = [
        effect.bpm_step
        for condition in conditions
        if (effect := CONDITION_EFFECTS.get(condition.lower())) and effect.bpm_step
    ]
    return min(steps) if steps else _DEFAULT_BPM_STEP

def _conditions_need_calming_mood(conditions: List[str]) -> bool:
    return any(
        CONDITION_EFFECTS.get(condition.lower(), ConditionEffect()).calming_mood
        for condition in conditions
    )

def calculate_gradual_bpm(
    target_bpm: int,
    last_bpm: Optional[int],
    conditions: Optional[List[str]] = None,
) -> int:
    """
    Постепенный переход BPM между отрывками
    Если разница с целевым велика — меняем не более чем на один шаг за трек
    """
    conditions = conditions or []
    target_bpm = _apply_conditions_bpm_cap(target_bpm, conditions)
    if last_bpm is None:
        return target_bpm
    step = _bpm_step_for_conditions(conditions)
    diff = target_bpm - last_bpm
    if abs(diff) <= step:
        return target_bpm
    return last_bpm + step if diff > 0 else last_bpm - step

def build_track_title(genre: str, mood: str, bpm: int) -> str:
    """Название трека для отображения в клиенте"""
    mood_titles = {
        "calming": "Спокойствие",
        "relaxing": "Релакс",
        "motivational": "Мотивация",
        "energetic": "Энергия",
    }
    prefix = mood_titles.get(mood, "Пульс")
    return f"{prefix} · {genre.title()}"

def calculate_target_bpm(
    activity: ActivityType,
    current_hr: int,
    resting_hr: int,
    max_hr: int,
    goal: GoalType,
    tempo_preference: TempoPreference,
    conditions: Optional[List[str]] = None,
) -> int:
    """Расчёт целевого BPM: база от активности + коррекция по пульсу, цели и темпу"""

    conditions = conditions or []
    base_bpm = _ACTIVITY_TARGET_BPM.get(activity, 110)
    intensity = calculate_intensity(current_hr, resting_hr, max_hr)
    hr_bpm = int(current_hr * (0.6 + intensity * 0.2))
    goal_adjustments = {
        GoalType.FAT_BURNING: -5,
        GoalType.SPRINT: +20,
        GoalType.RECOVERY: -15,
        GoalType.GENERAL: 0,
        GoalType.STRESS_REDUCTION: -20,
        GoalType.WARMUP: -10,
        GoalType.COOLDOWN: -15,
    }
    tempo_adjustments = {
        TempoPreference.SLOW: -15,
        TempoPreference.MEDIUM: 0,
        TempoPreference.FAST: +15,
    }

    """60% веса — вид активности, 40% — текущий пульс"""
    bpm = int(base_bpm * 0.6 + hr_bpm * 0.4)
    bpm += goal_adjustments.get(goal, 0)
    bpm += tempo_adjustments.get(tempo_preference, 0)
    bpm = max(60, min(180, bpm))
    return _apply_conditions_bpm_cap(bpm, conditions)

def select_genre(
    activity: ActivityType,
    preferred_genres: List[str],
    intensity: float,
    last_genre: Optional[str] = None,
    fragment_index: int = 0,
) -> str:
    """
    Выбор жанра:
    1. Из предпочтений пользователя берутся только совместимые с активностью
    2. Если таких несколько — чередуются между отрывками
    3. Если подходящих нет (например, metal при медитации) — дефолты активности
    """
    compatible = _filter_compatible_genres(preferred_genres, activity)
    if compatible:
        return _pick_rotating(compatible, fragment_index, last_genre)
    return _pick_from_defaults(activity, intensity)

def select_energy(bpm: int) -> EnergyLevel:
    """Выбор уровня энергии на основе BPM"""
    if bpm < 100:
        return EnergyLevel.LOW
    elif bpm < 130:
        return EnergyLevel.MEDIUM
    else:
        return EnergyLevel.HIGH

def select_mood(intensity: float, conditions: Optional[List[str]] = None) -> str:
    """Настроение: заболевания -> calming, иначе по интенсивности пульса"""
    if _conditions_need_calming_mood(conditions or []):
        return "calming"
    if intensity > 0.7:
        return "energetic"
    if intensity > 0.3:
        return "motivational"
    return "relaxing"

def build_prompt(
    bpm: int,
    genre: str,
    energy: EnergyLevel,
    mood: str,
    activity: ActivityType,
    goal: GoalType,
) -> str:
    """Сборка промпта для MusicGen"""
    
    energy_desc = {
        EnergyLevel.LOW: "low energy, relaxing, soft",
        EnergyLevel.MEDIUM: "medium energy, steady, groovy",
        EnergyLevel.HIGH: "high energy, intense, driving",
    }
    
    mood_desc = {
        "calming": "calming, soothing, peaceful",
        "relaxing": "relaxing, gentle, smooth",
        "motivational": "motivational, uplifting, inspiring",
        "energetic": "energetic, powerful, dynamic",
    }
    
    return (
        f"{genre}, {mood_desc.get(mood, 'motivational')}, "
        f"{energy_desc.get(energy, 'medium energy')}, "
        f"{bpm} bpm, steady beat, consistent rhythm, "
        f"suitable for {activity.value}, {goal.value} goal, high quality production"
    )