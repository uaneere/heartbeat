from dataclasses import dataclass


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def max_hr(age: int) -> int:
    return int(208 - 0.7 * age)


def intensity(hr: int, resting: int, max_hr_val: int) -> float:
    denominator = max(max_hr_val - resting, 1)
    normalized = (hr - resting) / denominator
    return clamp(normalized, 0.0, 1.0)


def zone_from_intensity(i: float) -> int:
    if i < 0.5:
        return 1
    if i < 0.7:
        return 2
    if i < 0.85:
        return 3
    return 4


def detect_mode(activity_type: str, current_hr: int, resting_hr: int, movement_intensity: float) -> str:
    if activity_type == "meditation" and current_hr > resting_hr + 40:
        return "calming"

    if current_hr > resting_hr + 35 and movement_intensity < 0.25:
        return "stress"

    return "exercise"


def should_regenerate(
    previous_hr: int | None,
    current_hr: int,
    previous_activity_type: str | None,
    activity_type: str,
    stress_detected: bool,
    hr_threshold: int = 8,
) -> bool:
    if previous_activity_type and previous_activity_type != activity_type:
        return True
    if previous_hr is None:
        return True
    if abs(current_hr - previous_hr) > hr_threshold:
        return True
    return stress_detected


def _activity_base_bpm(activity_type: str) -> int:
    mapping = {
        "sleep": 60,
        "meditation": 68,
        "studying": 82,
        "walking": 102,
        "yoga": 92,
        "cycling": 118,
        "gym": 122,
        "running": 128,
        "gaming": 110,
    }
    return mapping.get(activity_type, 105)


def _goal_adjustment(goal: str) -> int:
    mapping = {
        "recovery_run": -8,
        "fat_burning": 5,
        "sprint": 18,
        "marathon_pace": 12,
        "warmup": -8,
        "hypertrophy": 4,
        "powerlifting": 8,
        "cooldown": -14,
        "stress_reduction": -18,
        "breathing": -16,
        "sleep_prep": -20,
        "general_fitness": 0,
    }
    return mapping.get(goal, 0)


def _tempo_adjustment(tempo_pref: str) -> int:
    mapping = {"slow": -12, "medium": 0, "fast": 10}
    return mapping.get(tempo_pref, 0)


def _zone_adjustment(zone: int) -> int:
    mapping = {1: -12, 2: 0, 3: 15, 4: 26}
    return mapping.get(zone, 0)


def _select_energy(target_bpm: int) -> str:
    if target_bpm < 90:
        return "low"
    if target_bpm < 125:
        return "medium"
    return "high"


def _select_genre(activity_type: str, preferred_genres: list[str], mode: str) -> str:
    calming_fallback = {
        "sleep": "ambient",
        "meditation": "ambient",
        "studying": "lofi",
    }
    active_fallback = {
        "running": "edm",
        "gym": "techno",
        "cycling": "house",
        "walking": "chill electronic",
        "gaming": "electronic",
    }

    if mode in {"calming", "stress"}:
        return calming_fallback.get(activity_type, "ambient")

    if preferred_genres:
        if activity_type in {"sleep", "meditation"}:
            safe_genres = {"ambient", "lofi", "piano", "chill"}
            for genre in preferred_genres:
                if genre.lower() in safe_genres:
                    return genre
            return calming_fallback.get(activity_type, "ambient")
        return preferred_genres[0]

    return active_fallback.get(activity_type, "electronic")


def _apply_health_constraints(target_bpm: int, conditions: list[str], previous_bpm: int | None) -> int:
    constrained = target_bpm
    condition_set = {c.lower() for c in conditions}

    if "tachycardia" in condition_set and previous_bpm is not None:
        upper = previous_bpm + 10
        lower = previous_bpm - 10
        constrained = int(clamp(constrained, lower, upper))

    if "hypertension" in condition_set:
        constrained = min(constrained, 140)

    if "asthma" in condition_set:
        constrained = min(constrained, 145)

    return int(clamp(constrained, 55, 180))


@dataclass
class MusicDecision:
    target_bpm: int
    target_energy: str
    target_genre: str
    mood: str
    mode: str


def choose_transition_mode(
    *,
    previous_bpm: int | None,
    previous_genre: str | None,
    previous_energy: str | None,
    next_bpm: int,
    next_genre: str,
    next_energy: str,
    # Используем относительные проценты вместо абсолютных значений
) -> str:
    if previous_bpm is None or previous_genre is None or previous_energy is None:
        return "new"
    
    # Относительное изменение BPM (в процентах)
    delta_ratio = abs(next_bpm - previous_bpm) / max(previous_bpm, 1)
    
    # Случай 1: почти идентичный трек (<3% изменения BPM, тот же жанр, та же энергия)
    if delta_ratio < 0.03 and previous_genre == next_genre and previous_energy == next_energy:
        return "hold"
    
    # Случай 2: небольшое изменение (<8% BPM, без смены жанра/энергии)
    if delta_ratio < 0.08 and not (previous_genre != next_genre or previous_energy != next_energy):
        return "continue"
    
    # Случай 3: значительное изменение — переход
    return "transition"


def compute_music_decision(
    *,
    activity_type: str,
    goal: str,
    tempo_preference: str,
    preferred_genres: list[str],
    conditions: list[str],
    intensity_value: float,
    current_hr: int,
    resting_hr: int,
    movement_intensity: float,
    previous_bpm: int | None,
) -> MusicDecision:
    zone = zone_from_intensity(intensity_value)
    mode = detect_mode(activity_type, current_hr, resting_hr, movement_intensity)

    bpm = (
        _activity_base_bpm(activity_type)
        + _zone_adjustment(zone)
        + _goal_adjustment(goal)
        + _tempo_adjustment(tempo_preference)
    )

    if mode in {"calming", "stress"}:
        bpm -= 18

    bpm = _apply_health_constraints(bpm, conditions, previous_bpm)
    energy = _select_energy(bpm)
    genre = _select_genre(activity_type, preferred_genres, mode)
    mood = "calming" if mode in {"calming", "stress"} else "motivational"

    return MusicDecision(
        target_bpm=bpm,
        target_energy=energy,
        target_genre=genre,
        mood=mood,
        mode=mode,
    )