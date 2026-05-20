"""
Логика стрима: длительность перехода, сборка x-секундного crossfade, план воспроизведения.

Фрагмент = 30 с. Переход x с = хвост предыдущего + голова следующего (equal-power fade).
Воспроизведение:
  - первый фрагмент: [0, 30-x]
  - связка: переход x с, затем новый фрагмент [x, 30]
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import numpy as np
import soundfile as sf

from app.wav_paths import new_wav_path

try:
    from app.musicgen_config import CHUNK_DURATION_SEC as _CFG_CHUNK
    CHUNK_DURATION_SEC = float(_CFG_CHUNK)
except ImportError:
    CHUNK_DURATION_SEC = 30.0
MIN_FADE_SEC = 2.5
MAX_FADE_SEC = 8.0
# После MusicGen continuation — короче (модель уже «продолжила» тембр)
MIN_FADE_CONTINUATION_SEC = 1.5
MAX_FADE_CONTINUATION_SEC = 4.0


@dataclass
class TrackParams:
    bpm: int
    genre: str
    energy: str


@dataclass
class PlaybackSegment:
    file: str
    start: float
    duration: float
    kind: str  # fragment_head | transition | fragment_body | repeat_cycle


def _read_mono(path: str) -> tuple[np.ndarray, int]:
    path = os.path.abspath(path)
    samples, sr = sf.read(path, dtype="float32")
    if samples.ndim > 1:
        samples = samples.mean(axis=1)
    return samples, sr


def should_use_continuation(prev: Optional[TrackParams], nxt: TrackParams) -> bool:
    """
    Передаём хвост WAV в MusicGen, если смена не слишком резкая.
    При смене жанра или большом скачке BPM — новая генерация с нуля.
    """
    if prev is None:
        return False
    if prev.genre.lower() != nxt.genre.lower():
        return False
    if abs(nxt.bpm - prev.bpm) > 18:
        return False
    return True


def compute_fade_seconds(
    prev: Optional[TrackParams],
    nxt: TrackParams,
    *,
    continuation_used: bool = False,
) -> float:
    """
    Длительность перехода x (и y) по различию параметров.
    Почти одинаковые треки → MIN_FADE_SEC (2.5).
    """
    min_f = MIN_FADE_CONTINUATION_SEC if continuation_used else MIN_FADE_SEC
    max_f = MAX_FADE_CONTINUATION_SEC if continuation_used else MAX_FADE_SEC

    if prev is None:
        return min_f

    bpm_delta = abs(nxt.bpm - prev.bpm)
    genre_changed = prev.genre.lower() != nxt.genre.lower()
    energy_changed = prev.energy.lower() != nxt.energy.lower()

    if continuation_used and bpm_delta < 5 and not genre_changed:
        return min_f

    if bpm_delta < 3 and not genre_changed and not energy_changed:
        return min_f

    fade = min_f
    fade += min(bpm_delta / 10.0, 3.0)
    if genre_changed:
        fade += 2.5
    if energy_changed:
        fade += 0.5
    return round(min(max_f, max(min_f, fade)), 2)


def build_transition_clip(path_from: str, path_to: str, fade_seconds: float) -> str:
    """
    Сохраняет ровно fade_seconds WAV: crossfade хвоста path_from и головы path_to.
    """
    fade_seconds = max(MIN_FADE_SEC, min(fade_seconds, CHUNK_DURATION_SEC / 2))
    a, sr_a = _read_mono(path_from)
    b, sr_b = _read_mono(path_to)
    if sr_a != sr_b:
        raise ValueError("Sample rates do not match")

    fade_n = int(fade_seconds * sr_a)
    fade_n = max(1, min(fade_n, len(a), len(b)))

    tail = a[-fade_n:]
    lead = b[:fade_n]
    # Equal-power + мягкая S-кривая (меньше «провала» в середине)
    x = np.linspace(0.0, 1.0, fade_n, dtype=np.float32)
    t = x * x * (3.0 - 2.0 * x)
    gain_out = np.sqrt(1.0 - t)
    gain_in = np.sqrt(t)
    mixed = tail * gain_out + lead * gain_in

    out = new_wav_path("transition")
    sf.write(out, mixed, sr_a)
    return out


def playback_plan_first_fragment(fragment_path: str, fade_out_sec: float) -> list[PlaybackSegment]:
    """Первый фрагмент: играем только [0, 30-x] (хвост пойдёт в следующий переход)."""
    body = max(1.0, CHUNK_DURATION_SEC - fade_out_sec)
    return [
        PlaybackSegment(
            file=fragment_path,
            start=0.0,
            duration=body,
            kind="fragment_head",
        )
    ]


def playback_plan_link(
    transition_path: str,
    next_fragment_path: str,
    fade_sec: float,
) -> list[PlaybackSegment]:
    """Связка: переход x с, затем новый фрагмент [x, 30]."""
    body = max(1.0, CHUNK_DURATION_SEC - fade_sec)
    return [
        PlaybackSegment(
            file=transition_path,
            start=0.0,
            duration=fade_sec,
            kind="transition",
        ),
        PlaybackSegment(
            file=next_fragment_path,
            start=fade_sec,
            duration=body,
            kind="fragment_body",
        ),
    ]


def playback_plan_repeat_cycle(
    transition_path: str,
    fragment_path: str,
    fade_sec: float,
) -> list[PlaybackSegment]:
    """Повтор при неуспевшей генерации: тот же переход + тело [x, 30]."""
    return playback_plan_link(transition_path, fragment_path, fade_sec)


def segments_to_dicts(segments: list[PlaybackSegment]) -> list[dict]:
    return [
        {"file": s.file, "start": s.start, "duration": s.duration, "kind": s.kind}
        for s in segments
    ]
