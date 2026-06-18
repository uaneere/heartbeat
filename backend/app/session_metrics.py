"""
Расчёт метрик сессии для ответов API
"""

from app.decision_engine import (
    calculate_max_heart_rate,
    calculate_intensity,
    calculate_target_bpm,
    get_heart_rate_zone,
    get_heart_rate_zone_label,
)
from app.session_store import SessionState


def compute_session_metrics(session: SessionState) -> dict:
    max_hr = calculate_max_heart_rate(session.profile.age)
    intensity = calculate_intensity(
        session.current_hr,
        session.profile.resting_hr,
        max_hr,
    )
    zone = get_heart_rate_zone(intensity)
    target_bpm = calculate_target_bpm(
        activity=session.context.activity_type,
        current_hr=session.current_hr,
        resting_hr=session.profile.resting_hr,
        max_hr=max_hr,
        goal=session.context.goal,
        tempo_preference=session.context.tempo_preference,
    )
    return {
        "heart_rate_zone": zone,
        "heart_rate_zone_label": get_heart_rate_zone_label(zone),
        "target_bpm": target_bpm,
        "intensity": intensity,
    }
