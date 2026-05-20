from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.hr_simulator import simulate_heart_rate
from app.musicgen_config import CHUNK_DURATION_SEC
from app.pipeline import run_music_pipeline
from app.schemas import (
    InputData,
    OutputData,
    SessionContextPatchRequest,
    SessionContextResponse,
    SessionGenerateRequest,
    SessionGenerateResponse,
    SessionStartRequest,
    SessionStartResponse,
    SessionTickRequest,
    SessionTickResponse,
)
from app.session_store import create_session, get_session

router = APIRouter()


@router.get("/model")
def model_info():
    from app.generator import get_active_model_info

    return get_active_model_info()


@router.get("/ready")
def ready():
    from app.generator import get_active_model_info, is_model_ready

    info = get_active_model_info()
    if not info.get("ready"):
        return JSONResponse(
            status_code=503,
            content={"ready": False, "message": "Модель ещё загружается", **info},
        )
    return {"ready": True, **info}


@router.post("/generate", response_model=OutputData)
def generate_music(data: InputData):
    return run_music_pipeline(
        age=data.profile.age,
        resting_hr=data.profile.resting_hr,
        current_hr=data.realtime.current_hr,
        activity_type=data.session.activity_type,
        goal=data.session.goal,
        tempo_preference=data.session.manual_tempo_preference,
        time_signature=data.session.time_signature,
        preferred_genres=data.profile.preferred_genres,
        conditions=data.profile.conditions,
        movement_intensity=data.realtime.movement_intensity,
        previous_hr=data.previous_hr,
        previous_activity_type=data.previous_activity_type,
        previous_bpm=data.previous_bpm,
        previous_genre=None,
        previous_energy=None,
        previous_fragment_path=None,
        previous_transition_path=None,
        previous_fade_seconds=2.5,
        seed=data.seed,
        generate_audio=data.generate_audio,
        force_regenerate=data.force_regenerate,
    )


@router.post("/sessions/start", response_model=SessionStartResponse)
def start_session(payload: SessionStartRequest):
    initial_hr = payload.profile.resting_hr
    state = create_session(payload.profile, payload.session, initial_hr=initial_hr)
    return SessionStartResponse(session_id=state.session_id, current_hr=initial_hr, tick=state.tick)


@router.post("/sessions/{session_id}/tick", response_model=SessionTickResponse)
def next_tick(session_id: str, payload: SessionTickRequest):
    from uuid import UUID

    state = get_session(UUID(session_id))
    if state is None:
        raise HTTPException(status_code=404, detail="Session not found")

    movement = payload.movement_intensity if payload.movement_intensity is not None else state.realtime.movement_intensity
    stress = payload.stress_level if payload.stress_level is not None else state.realtime.stress_level

    state.tick += 1
    new_hr = simulate_heart_rate(
        previous_hr=state.realtime.current_hr,
        resting_hr=state.profile.resting_hr,
        avg_active_hr=state.profile.avg_active_hr,
        activity_type=state.context.activity_type,
        tick=state.tick,
    )

    state.realtime.current_hr = new_hr
    state.realtime.movement_intensity = movement
    state.realtime.stress_level = stress
    state.realtime.steps = (state.realtime.steps or 0) + int(8 + movement * 15)
    state.realtime.cadence = int(70 + movement * 90)

    return SessionTickResponse(session_id=state.session_id, tick=state.tick, realtime=state.realtime)


@router.post("/sessions/{session_id}/generate", response_model=SessionGenerateResponse)
def generate_for_session(session_id: str, payload: SessionGenerateRequest):
    from uuid import UUID

    state = get_session(UUID(session_id))
    if state is None:
        raise HTTPException(status_code=404, detail="Session not found")

    movement = payload.movement_intensity if payload.movement_intensity is not None else state.realtime.movement_intensity
    stress = payload.stress_level if payload.stress_level is not None else state.realtime.stress_level

    state.tick += 1
    new_hr = simulate_heart_rate(
        previous_hr=state.realtime.current_hr,
        resting_hr=state.profile.resting_hr,
        avg_active_hr=state.profile.avg_active_hr,
        activity_type=state.context.activity_type,
        tick=state.tick,
    )
    state.realtime.current_hr = new_hr
    state.realtime.movement_intensity = movement
    state.realtime.stress_level = stress

    result = run_music_pipeline(
        age=state.profile.age,
        resting_hr=state.profile.resting_hr,
        current_hr=state.realtime.current_hr,
        activity_type=state.context.activity_type,
        goal=state.context.goal,
        tempo_preference=state.context.manual_tempo_preference,
        time_signature=state.context.time_signature,
        preferred_genres=state.profile.preferred_genres,
        conditions=state.profile.conditions,
        movement_intensity=state.realtime.movement_intensity,
        previous_hr=state.previous_hr,
        previous_activity_type=state.previous_activity_type,
        previous_bpm=state.previous_bpm,
        previous_genre=state.previous_genre,
        previous_energy=state.previous_energy,  # Добавлено
        previous_fragment_path=state.last_fragment_path,
        previous_transition_path=state.last_transition_path,
        previous_fade_seconds=state.last_fade_seconds,
        seed=payload.seed,
        generate_audio=payload.generate_audio,
        force_regenerate=payload.force_regenerate,
        duration_seconds=int(CHUNK_DURATION_SEC),
    )

    state.previous_hr = state.realtime.current_hr
    state.previous_bpm = result.target_bpm
    state.previous_genre = result.target_genre
    state.previous_energy = result.target_energy
    state.previous_activity_type = state.context.activity_type
    if result.fragment_file:
        state.last_fragment_path = result.fragment_file
        state.last_chunk_path = result.fragment_file
    if result.transition_file:
        state.last_transition_path = result.transition_file
    state.last_fade_seconds = result.fade_seconds

    return SessionGenerateResponse(session_id=state.session_id, tick=state.tick, result=result)

@router.patch("/sessions/{session_id}/context", response_model=SessionContextResponse)
def update_session_context(session_id: str, payload: SessionContextPatchRequest):
    from uuid import UUID

    state = get_session(UUID(session_id))
    if state is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if payload.activity_type is not None:
        state.context.activity_type = payload.activity_type
    if payload.goal is not None:
        state.context.goal = payload.goal
    if payload.manual_tempo_preference is not None:
        state.context.manual_tempo_preference = payload.manual_tempo_preference
    if payload.time_signature is not None:
        state.context.time_signature = payload.time_signature

    return SessionContextResponse(session_id=state.session_id, context=state.context)
