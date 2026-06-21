"""
Эндпоинты генерации музыки
"""

import os
from uuid import UUID
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.models import (
    GenerateRequest,
    GenerateResponse,
)
from app.session_store import get_session, update_session
from app.generator import generate_audio, is_model_ready
from app.decision_engine import (
    calculate_max_heart_rate,
    calculate_intensity,
    calculate_target_bpm,
    select_genre,
    select_energy,
    select_mood,
    build_prompt,
    build_track_title,
    get_heart_rate_zone,
    get_heart_rate_zone_label,
)
from app.audio_utils import (
    get_filename_from_path,
    get_audio_url,
    create_transition_bridge,
    create_loop_bridge,
    read_mono,
)
from app.config import CHUNK_DURATION_SEC, CROSSFADE_SEC, AUDIO_DIR

router = APIRouter(prefix="/api/v1", tags=["generate"])


def _bridge_duration(path: str) -> int:
    samples, sr = read_mono(path)
    return max(1, int(len(samples) / sr))


@router.post("/session/{session_id}/generate", response_model=GenerateResponse)
async def generate_music(session_id: UUID, request: GenerateRequest = GenerateRequest()):
    """
    Сгенерировать музыкальный отрывок на основе текущего пульса.

    Пайплайн:
    1. Первый отрывок — сырой WAV (воспроизведение после полной генерации).
    2. Следующие отрывки — сырой WAV + transition (crossfade с предыдущим) + loop_bridge.
    3. loop_bridge — плавный переход конец→начало, если следующий отрывок ещё не готов.
    """
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not is_model_ready():
        raise HTTPException(status_code=503, detail="Model is still loading")

    max_hr = calculate_max_heart_rate(session.profile.age)
    intensity = calculate_intensity(
        session.current_hr,
        session.profile.resting_hr,
        max_hr,
    )

    bpm = calculate_target_bpm(
        activity=session.context.activity_type,
        current_hr=session.current_hr,
        resting_hr=session.profile.resting_hr,
        max_hr=max_hr,
        goal=session.context.goal,
        tempo_preference=session.context.tempo_preference,
    )

    genre = select_genre(
        activity=session.context.activity_type,
        preferred_genres=session.profile.preferred_genres,
        intensity=intensity,
    )

    energy = select_energy(bpm)
    is_stress = session.stress_level > 0.7
    mood = select_mood(intensity, is_stress)

    prompt = build_prompt(
        bpm=bpm,
        genre=genre,
        energy=energy,
        mood=mood,
        activity=session.context.activity_type,
        goal=session.context.goal,
    )

    try:
        audio_path = generate_audio(
            prompt=prompt,
            duration_seconds=CHUNK_DURATION_SEC,
            seed=request.seed,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

    transition_path = None
    if session.last_raw_fragment_path:
        transition_path = create_transition_bridge(
            session.last_raw_fragment_path,
            audio_path,
            fade_seconds=CROSSFADE_SEC,
        )

    loop_bridge_path = create_loop_bridge(audio_path, fade_seconds=CROSSFADE_SEC)
    fragment_index = session.fragment_index + 1

    session.tick += 1
    update_session(
        session_id,
        last_fragment_path=audio_path,
        last_raw_fragment_path=audio_path,
        last_loop_bridge_path=loop_bridge_path,
        last_transition_path=transition_path,
        fragment_index=fragment_index,
        last_bpm=bpm,
        last_genre=genre,
        tick=session.tick,
    )

    filename = get_filename_from_path(audio_path)
    zone = get_heart_rate_zone(intensity)

    transition_url = None
    transition_dur = 0
    if transition_path:
        transition_url = get_audio_url(get_filename_from_path(transition_path))
        transition_dur = _bridge_duration(transition_path)

    loop_url = get_audio_url(get_filename_from_path(loop_bridge_path))
    loop_dur = _bridge_duration(loop_bridge_path)

    return GenerateResponse(
        success=True,
        audio_url=get_audio_url(filename),
        bpm=bpm,
        genre=genre,
        energy=energy,
        mood=mood,
        track_title=build_track_title(genre, mood, bpm),
        duration_seconds=int(CHUNK_DURATION_SEC),
        tick=session.tick,
        fragment_file=filename,
        fragment_index=fragment_index,
        heart_rate_zone=zone,
        heart_rate_zone_label=get_heart_rate_zone_label(zone),
        transition_audio_url=transition_url,
        transition_duration_seconds=transition_dur,
        loop_bridge_url=loop_url,
        loop_bridge_duration_seconds=loop_dur,
        chunk_duration_sec=CHUNK_DURATION_SEC,
    )


@router.get("/audio/{filename}")
async def serve_audio(filename: str):
    """Отдать аудиофайл для воспроизведения"""
    path = os.path.join(AUDIO_DIR, filename)

    real_path = os.path.realpath(path)
    real_audio_dir = os.path.realpath(AUDIO_DIR)
    if not real_path.startswith(real_audio_dir):
        raise HTTPException(status_code=403, detail="Forbidden")

    if not os.path.exists(real_path):
        raise HTTPException(status_code=404, detail="Audio file not found")

    return FileResponse(
        path=real_path,
        media_type="audio/wav",
        filename=filename,
    )
