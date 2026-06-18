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
    EnergyLevel,
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
from app.audio_utils import get_filename_from_path, get_audio_url
from app.config import CHUNK_DURATION_SEC, AUDIO_DIR

router = APIRouter(prefix="/api/v1", tags=["generate"])


@router.post("/session/{session_id}/generate", response_model=GenerateResponse)
async def generate_music(session_id: UUID, request: GenerateRequest = GenerateRequest()):
    """
    Сгенерировать музыку на основе текущего состояния сессии
    
    Мобильное приложение вызывает этот эндпоинт, когда:
    - Текущий трек подходит к концу (за 5-10 секунд до окончания)
    - Пользователь вручную запросил смену трека
    - Изменилась активность или цель
    """
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Проверяем готовность модели
    if not is_model_ready():
        raise HTTPException(status_code=503, detail="Model is still loading")
    
    # Рассчитываем параметры
    max_hr = calculate_max_heart_rate(session.profile.age)
    intensity = calculate_intensity(
        session.current_hr,
        session.profile.resting_hr,
        max_hr
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
    
    # Определяем стресс
    is_stress = session.stress_level > 0.7
    mood = select_mood(intensity, is_stress)
    
    # Собираем промпт
    prompt = build_prompt(
        bpm=bpm,
        genre=genre,
        energy=energy,
        mood=mood,
        activity=session.context.activity_type,
        goal=session.context.goal,
    )
    
    # Генерируем аудио
    try:
        audio_path = generate_audio(
            prompt=prompt,
            duration_seconds=CHUNK_DURATION_SEC,
            seed=request.seed,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

    session.tick += 1
    update_session(
        session_id,
        last_fragment_path=audio_path,
        last_bpm=bpm,
        last_genre=genre,
        tick=session.tick,
    )

    filename = get_filename_from_path(audio_path)
    zone = get_heart_rate_zone(intensity)

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
        heart_rate_zone=zone,
        heart_rate_zone_label=get_heart_rate_zone_label(zone),
    )


@router.get("/audio/{filename}")
async def serve_audio(filename: str):
    """
    Отдать аудиофайл для воспроизведения
    
    Мобильное приложение скачивает аудио по URL из GenerateResponse.audio_url
    """
    path = os.path.join(AUDIO_DIR, filename)
    
    # Безопасность: проверяем, что файл в разрешенной директории
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