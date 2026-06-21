"""
Эндпоинты генерации музыки
"""

import asyncio
import logging
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
    calculate_gradual_bpm,
    get_heart_rate_zone,
    get_heart_rate_zone_label,
    select_genre,
    select_energy,
    select_mood,
    build_prompt,
    build_track_title,
)
from app.audio_utils import (
    get_filename_from_path,
    get_audio_url,
    create_transition_bridge,
    create_loop_bridge,
    read_mono,
    prepare_for_serving,
)
from app.config import CHUNK_DURATION_SEC, CROSSFADE_SEC, AUDIO_DIR, DELETE_BRIDGE_WAV_AFTER_ENCODE

router = APIRouter(prefix="/api/v1", tags=["generate"])
logger = logging.getLogger(__name__)


def _bridge_duration(path: str) -> int:
    samples, sr = read_mono(path)
    return max(1, int(len(samples) / sr))


def _generate_fragment_sync(
    *,
    session_id: UUID,
    prompt: str,
    seed: int | None,
    last_raw_fragment_path: str | None,
    fragment_index: int,
    tick: int,
    bpm: int,
    genre: str,
    energy,
    mood: str,
    intensity: float,
) -> GenerateResponse:
    """
    Тяжёлая синхронная работа: MusicGen + crossfade + ffmpeg.
    Выполняется в thread pool, чтобы не блокировать event loop
    (иначе AVPlayer и heartrate зависают на время генерации).
    """
    audio_path = generate_audio(
        prompt=prompt,
        duration_seconds=CHUNK_DURATION_SEC,
        seed=seed,
    )

    transition_path = None
    if last_raw_fragment_path:
        transition_path = create_transition_bridge(
            last_raw_fragment_path,
            audio_path,
            fade_seconds=CROSSFADE_SEC,
        )

    loop_bridge_path = create_loop_bridge(audio_path, fade_seconds=CROSSFADE_SEC)
    new_fragment_index = fragment_index + 1
    new_tick = tick + 1

    update_session(
        session_id,
        last_fragment_path=audio_path,
        last_raw_fragment_path=audio_path,
        last_loop_bridge_path=loop_bridge_path,
        last_transition_path=transition_path,
        fragment_index=new_fragment_index,
        last_bpm=bpm,
        last_genre=genre,
        tick=new_tick,
    )

    served_audio = prepare_for_serving(audio_path, delete_source=False)
    filename = get_filename_from_path(served_audio)
    zone = get_heart_rate_zone(intensity)

    transition_url = None
    transition_dur = 0
    if transition_path:
        transition_dur = _bridge_duration(transition_path)
        served_transition = prepare_for_serving(
            transition_path,
            delete_source=DELETE_BRIDGE_WAV_AFTER_ENCODE,
        )
        transition_url = get_audio_url(get_filename_from_path(served_transition))

    loop_dur = _bridge_duration(loop_bridge_path)
    served_loop = prepare_for_serving(
        loop_bridge_path,
        delete_source=DELETE_BRIDGE_WAV_AFTER_ENCODE,
    )
    loop_url = get_audio_url(get_filename_from_path(served_loop))

    logger.info("Fragment ready: %s", filename)

    return GenerateResponse(
        success=True,
        audio_url=get_audio_url(filename),
        bpm=bpm,
        genre=genre,
        energy=energy,
        mood=mood,
        track_title=build_track_title(genre, mood, bpm),
        duration_seconds=int(CHUNK_DURATION_SEC),
        tick=new_tick,
        fragment_file=filename,
        fragment_index=new_fragment_index,
        heart_rate_zone=zone,
        heart_rate_zone_label=get_heart_rate_zone_label(zone),
        transition_audio_url=transition_url,
        transition_duration_seconds=transition_dur,
        loop_bridge_url=loop_url,
        loop_bridge_duration_seconds=loop_dur,
        chunk_duration_sec=CHUNK_DURATION_SEC,
    )


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
        conditions=session.profile.conditions,
    )
    track_bpm = calculate_gradual_bpm(
        target_bpm=bpm,
        last_bpm=session.last_bpm,
        conditions=session.profile.conditions,
    )

    genre = select_genre(
        activity=session.context.activity_type,
        preferred_genres=session.profile.preferred_genres,
        intensity=intensity,
    )

    energy = select_energy(track_bpm)
    is_stress = session.stress_level > 0.7
    mood = select_mood(intensity, is_stress, conditions=session.profile.conditions)

    prompt = build_prompt(
        bpm=track_bpm,
        genre=genre,
        energy=energy,
        mood=mood,
        activity=session.context.activity_type,
        goal=session.context.goal,
    )

    try:
        return await asyncio.to_thread(
            _generate_fragment_sync,
            session_id=session_id,
            prompt=prompt,
            seed=request.seed,
            last_raw_fragment_path=session.last_raw_fragment_path,
            fragment_index=session.fragment_index,
            tick=session.tick,
            bpm=track_bpm,
            genre=genre,
            energy=energy,
            mood=mood,
            intensity=intensity,
        )
    except Exception as e:
        logger.exception("Generation failed")
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@router.get("/audio/{filename}")
async def serve_audio(filename: str):
    """Fallback: отдать аудиофайл (основной путь — /static/tracks/...)"""
    path = os.path.join(AUDIO_DIR, filename)

    real_path = os.path.realpath(path)
    real_audio_dir = os.path.realpath(AUDIO_DIR)
    if not real_path.startswith(real_audio_dir):
        raise HTTPException(status_code=403, detail="Forbidden")

    if not os.path.exists(real_path):
        raise HTTPException(status_code=404, detail="Audio file not found")

    media_type = "audio/mpeg" if filename.lower().endswith(".mp3") else "audio/wav"

    return FileResponse(
        path=real_path,
        media_type=media_type,
        filename=filename,
    )
