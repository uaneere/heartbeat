"""
Логика выбора BPM, жанра и настроения на основе пульса и активности
"""

import math
from typing import List, Optional

from app.models import ActivityType, GoalType, TempoPreference, EnergyLevel


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
    """Человекочитаемое название зоны пульса"""
    labels = {
        1: "Восстановление",
        2: "Жиросжигание",
        3: "Кардио",
        4: "Анаэробная",
        5: "Максимум",
    }
    return labels.get(zone, "Кардио")


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
) -> int:
    """Расчет целевого BPM на основе пульса и активности"""
    
    # База от активности
    activity_base = {
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
    
    base_bpm = activity_base.get(activity, 110)
    
    # Корректировка по интенсивности (BPM ~ 60-80% от HR)
    intensity = calculate_intensity(current_hr, resting_hr, max_hr)
    hr_bpm = int(current_hr * (0.6 + intensity * 0.2))
    
    # Корректировка по цели
    goal_adjustments = {
        GoalType.FAT_BURNING: -5,
        GoalType.SPRINT: +20,
        GoalType.RECOVERY: -15,
        GoalType.GENERAL: 0,
        GoalType.STRESS_REDUCTION: -20,
        GoalType.WARMUP: -10,
        GoalType.COOLDOWN: -15,
    }
    
    # Корректировка по темпу
    tempo_adjustments = {
        TempoPreference.SLOW: -15,
        TempoPreference.MEDIUM: 0,
        TempoPreference.FAST: +15,
    }
    
    bpm = (base_bpm + hr_bpm) // 2
    bpm += goal_adjustments.get(goal, 0)
    bpm += tempo_adjustments.get(tempo_preference, 0)
    
    # Ограничения
    return max(60, min(180, bpm))


def select_genre(
    activity: ActivityType,
    preferred_genres: List[str],
    intensity: float,
) -> str:
    """Выбор жанра на основе активности и предпочтений"""
    
    # Жанры по активности
    activity_genres = {
        ActivityType.RUNNING: ["edm", "techno", "drum and bass", "house"],
        ActivityType.GYM: ["techno", "metal", "rock", "hardstyle"],
        ActivityType.CYCLING: ["house", "progressive house", "trance"],
        ActivityType.WALKING: ["chill electronic", "lofi", "downtempo"],
        ActivityType.YOGA: ["ambient", "lofi", "piano", "acoustic"],
        ActivityType.MEDITATION: ["ambient", "meditation", "nature sounds"],
        ActivityType.SLEEP: ["ambient", "piano", "white noise"],
        ActivityType.STUDYING: ["lofi", "classical", "jazz", "ambient"],
        ActivityType.GAMING: ["electronic", "synthwave", "chiptune"],
    }
    
    genres = activity_genres.get(activity, ["electronic", "house"])
    
    # Если есть предпочтения пользователя
    if preferred_genres:
        for pref in preferred_genres:
            if any(pref.lower() in g.lower() for g in genres):
                return pref
        return preferred_genres[0]
    
    # Выбор по интенсивности
    if intensity > 0.7:
        return genres[0]  # Более энергичный
    elif intensity < 0.3:
        return genres[-1]  # Более спокойный
    else:
        return genres[min(1, len(genres)-1)]


def select_energy(bpm: int) -> EnergyLevel:
    """Выбор уровня энергии на основе BPM"""
    if bpm < 100:
        return EnergyLevel.LOW
    elif bpm < 130:
        return EnergyLevel.MEDIUM
    else:
        return EnergyLevel.HIGH


def select_mood(intensity: float, is_stress: bool = False) -> str:
    """Выбор настроения"""
    if is_stress:
        return "calming"
    if intensity > 0.7:
        return "energetic"
    elif intensity > 0.3:
        return "motivational"
    else:
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