import random


def _activity_target(activity_type: str, resting_hr: int, avg_active_hr: int | None) -> int:
    base_active = avg_active_hr if avg_active_hr is not None else resting_hr + 65
    mapping = {
        "sleep": resting_hr - 8,
        "meditation": resting_hr + 3,
        "studying": resting_hr + 8,
        "walking": resting_hr + 25,
        "yoga": resting_hr + 18,
        "cycling": resting_hr + 45,
        "gym": resting_hr + 50,
        "running": base_active,
        "gaming": resting_hr + 20,
    }
    return mapping.get(activity_type, resting_hr + 20)


def simulate_heart_rate(
    *,
    previous_hr: int,
    resting_hr: int,
    avg_active_hr: int | None,
    activity_type: str,
    tick: int,
) -> int:
    target = _activity_target(activity_type, resting_hr, avg_active_hr)

    # Smooth drift to target with minor bounded noise.
    delta = target - previous_hr
    step = max(-4, min(4, int(delta * 0.25)))
    noise = random.randint(-1, 1)

    wave = int(2 * (1 if (tick // 3) % 2 == 0 else -1))
    candidate = previous_hr + step + noise + wave
    return max(40, min(210, candidate))
