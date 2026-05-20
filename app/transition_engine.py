from dataclasses import dataclass
from typing import Optional
import os

from app.audio_stitch import create_playable_chunk, simple_crossfade
from app.generator import generate


@dataclass
class TransitionResult:
    file_path: str
    mode: str
    bridge_path: Optional[str] = None


def build_bridge_prompt(
    from_genre: str,
    from_bpm: int,
    from_energy: str,
    to_genre: str,
    to_bpm: int,
    to_energy: str,
) -> str:
    """Создает промпт для переходного трека"""
    return (
        f"short musical bridge, transitioning from {from_genre} ({from_bpm} bpm, {from_energy} energy) "
        f"to {to_genre} ({to_bpm} bpm, {to_energy} energy), "
        f"smooth gradual change, neutral mood, "
        f"slowly fading out old elements and introducing new ones, "
        f"intermediate tempo {int((from_bpm + to_bpm) / 2)} bpm, "
        f"duration 6 seconds, seamless connection"
    )


def render_next_fragment(
    *,
    transition_mode: str,
    previous_chunk_path: str | None,
    target_prompt: str,
    target_genre: str,
    target_bpm: int,
    target_energy: str,
    previous_genre: str | None,
    previous_bpm: int | None,
    previous_energy: str | None,
    duration_seconds: int = 30,
    seed: int | None = None,
) -> TransitionResult:
    """
    Рендеринг следующего фрагмента с использованием bridge-переходов
    """
    
    # Первый трек - просто генерируем
    if previous_chunk_path is None:
        track = generate(target_prompt, duration_seconds=duration_seconds, seed=seed)
        return TransitionResult(file_path=track, mode="new")
    
    # Если параметры не изменились или изменения минимальны
    if transition_mode == "hold":
        # Генерируем новый трек и просто добавляем его без перехода
        next_track = generate(target_prompt, duration_seconds=duration_seconds, seed=seed)
        # Короткий crossfade для плавности
        merged = simple_crossfade(previous_chunk_path, next_track, fade_seconds=2.0)
        return TransitionResult(file_path=merged, mode="hold")
    
    # Небольшие изменения - короткий bridge
    if transition_mode == "continue":
        # Генерируем следующий трек
        next_track = generate(target_prompt, duration_seconds=duration_seconds, seed=seed)
        
        # Создаем короткий bridge (6 секунд)
        bridge_prompt = build_bridge_prompt(
            from_genre=previous_genre or target_genre,
            from_bpm=previous_bpm or target_bpm,
            from_energy=previous_energy or target_energy,
            to_genre=target_genre,
            to_bpm=target_bpm,
            to_energy=target_energy,
        )
        
        bridge_seed = None if seed is None else seed + 1
        bridge = generate(bridge_prompt, duration_seconds=6, seed=bridge_seed)
        
        # Склеиваем: предыдущий трек + bridge + новый трек
        # Обрезаем по 1 секунде с каждого конца для плавности
        merged = create_playable_chunk(previous_chunk_path, bridge, next_track, crossfade=1.5)
        
        return TransitionResult(file_path=merged, mode="continue", bridge_path=bridge)
    
    # Значительные изменения - длинный bridge
    if transition_mode == "transition":
        # Генерируем следующий трек
        next_track = generate(target_prompt, duration_seconds=duration_seconds, seed=seed)
        
        # Создаем bridge (8-10 секунд)
        bridge_prompt = build_bridge_prompt(
            from_genre=previous_genre or "electronic",
            from_bpm=previous_bpm or target_bpm,
            from_energy=previous_energy or "medium",
            to_genre=target_genre,
            to_bpm=target_bpm,
            to_energy=target_energy,
        )
        
        bridge_seed = None if seed is None else seed + 1
        bridge = generate(bridge_prompt, duration_seconds=10, seed=bridge_seed)
        
        # Склеиваем с более длинным crossfade
        merged = create_playable_chunk(previous_chunk_path, bridge, next_track, crossfade=2.5)
        
        return TransitionResult(file_path=merged, mode="transition", bridge_path=bridge)
    
    # Fallback
    next_track = generate(target_prompt, duration_seconds=duration_seconds, seed=seed)
    return TransitionResult(file_path=next_track, mode="new")