import logging
import os

from app.generator import build_prompt, generate_fragment
from app.schemas import OutputData, PlaybackSegmentOut
from app.services import compute_music_decision, intensity, max_hr, should_regenerate
from stream_logic import (
    MIN_FADE_SEC,
    TrackParams,
    build_transition_clip,
    compute_fade_seconds,
    playback_plan_first_fragment,
    playback_plan_link,
    playback_plan_repeat_cycle,
    segments_to_dicts,
    should_use_continuation,
)

logger = logging.getLogger(__name__)


def _params_from_decision(decision) -> TrackParams:
    return TrackParams(
        bpm=decision.target_bpm,
        genre=decision.target_genre,
        energy=decision.target_energy,
    )


def run_music_pipeline(
    *,
    age: int,
    resting_hr: int,
    current_hr: int,
    activity_type: str,
    goal: str,
    tempo_preference: str,
    time_signature: str,
    preferred_genres: list[str],
    conditions: list[str],
    movement_intensity: float,
    previous_hr: int | None,
    previous_activity_type: str | None,
    previous_bpm: int | None,
    previous_genre: str | None,
    previous_energy: str | None,
    previous_fragment_path: str | None,
    previous_transition_path: str | None,
    previous_fade_seconds: float,
    seed: int | None,
    generate_audio: bool,
    force_regenerate: bool = False,
    duration_seconds: int | None = None,
) -> OutputData:
    from app.musicgen_config import CHUNK_DURATION_SEC

    if duration_seconds is None:
        duration_seconds = int(CHUNK_DURATION_SEC)
    mhr = max_hr(age)
    i = intensity(current_hr, resting_hr, mhr)

    decision = compute_music_decision(
        activity_type=activity_type,
        goal=goal,
        tempo_preference=tempo_preference,
        preferred_genres=preferred_genres,
        conditions=conditions,
        intensity_value=i,
        current_hr=current_hr,
        resting_hr=resting_hr,
        movement_intensity=movement_intensity,
        previous_bpm=previous_bpm,
    )

    new_params = _params_from_decision(decision)
    prev_params = None
    if previous_bpm is not None and previous_genre and previous_energy:
        prev_params = TrackParams(
            bpm=previous_bpm,
            genre=previous_genre,
            energy=previous_energy,
        )

    use_cont = should_use_continuation(prev_params, new_params)
    prompt = build_prompt(
        bpm=decision.target_bpm,
        mood=decision.mood,
        genre=decision.target_genre,
        energy=decision.target_energy,
        activity_type=activity_type,
        goal=goal,
        mode=decision.mode,
        time_signature=time_signature,
        continuation=use_cont and previous_fragment_path is not None,
    )

    stress_detected = decision.mode in {"stress", "calming"}
    regenerate = force_regenerate or should_regenerate(
        previous_hr=previous_hr,
        current_hr=current_hr,
        previous_activity_type=previous_activity_type,
        activity_type=activity_type,
        stress_detected=stress_detected,
    )

    fade_sec = compute_fade_seconds(
        prev_params, new_params, continuation_used=False
    )
    fragment_file = ""
    transition_file = ""
    playback_out: list[PlaybackSegmentOut] = []
    transition_mode = "none"
    generation_method = "none"
    file_path = ""

    if generate_audio and regenerate:
        try:
            fragment_file, generation_method = generate_fragment(
                prompt,
                duration_seconds=duration_seconds,
                seed=seed,
                previous_fragment_path=previous_fragment_path,
                use_continuation=use_cont,
            )
            file_path = fragment_file

            cont_applied = generation_method in {"continuation", "melody"}
            fade_sec = compute_fade_seconds(
                prev_params, new_params, continuation_used=cont_applied
            )

            if previous_fragment_path and os.path.isfile(previous_fragment_path):
                transition_file = build_transition_clip(
                    previous_fragment_path, fragment_file, fade_sec
                )
                plan = playback_plan_link(transition_file, fragment_file, fade_sec)
                transition_mode = "continuation_link" if cont_applied else "link"
            else:
                plan = playback_plan_first_fragment(fragment_file, fade_sec)
                transition_mode = "new"

            playback_out = [PlaybackSegmentOut(**d) for d in segments_to_dicts(plan)]

        except Exception as exc:
            logger.exception("Fragment generation failed: %s", exc)
            if previous_fragment_path and os.path.isfile(previous_fragment_path):
                fragment_file = previous_fragment_path
                transition_file = previous_transition_path or ""
                fade_sec = previous_fade_seconds or MIN_FADE_SEC
                file_path = fragment_file
                generation_method = "repeat_fallback"

                if transition_file and os.path.isfile(transition_file):
                    plan = playback_plan_repeat_cycle(
                        transition_file, fragment_file, fade_sec
                    )
                    transition_mode = "repeat_fallback"
                else:
                    plan = playback_plan_first_fragment(fragment_file, fade_sec)
                    transition_mode = "repeat_head"

                playback_out = [PlaybackSegmentOut(**d) for d in segments_to_dicts(plan)]
                logger.warning("Repeat playback plan (gen failed)")
            else:
                # Первый фрагмент без fallback — отдаём 200 с пустым audio, не 500
                logger.error("Первая генерация не удалась, playback пустой")
                transition_mode = "error"

    return OutputData(
        target_bpm=decision.target_bpm,
        intensity=round(i, 2),
        target_energy=decision.target_energy,
        target_genre=decision.target_genre,
        mood=decision.mood,
        mode=decision.mode,
        state_changed=stress_detected,
        should_regenerate=regenerate,
        transition_mode=transition_mode,
        prompt=prompt,
        file=file_path,
        fragment_file=fragment_file,
        transition_file=transition_file,
        fade_seconds=fade_sec,
        generation_method=generation_method,
        playback=playback_out,
    )
