import os

import numpy as np
import soundfile as sf

from app.wav_paths import new_wav_path


def _read_mono(path: str) -> tuple[np.ndarray, int]:
    """Читает WAV в моно"""
    samples, sample_rate = sf.read(path, dtype="float32")
    if samples.ndim > 1:
        samples = samples.mean(axis=1)
    return samples, sample_rate


def _write_mono(samples: np.ndarray, sample_rate: int, name_prefix: str = "stitch") -> str:
    path = new_wav_path(name_prefix)
    sf.write(path, samples, sample_rate)
    return path


def cut_audio(samples: np.ndarray, sample_rate: int, cut_start: float = 0, cut_end: float = 0) -> np.ndarray:
    """Обрезает аудио с начала и конца"""
    start_sample = int(cut_start * sample_rate)
    end_sample = len(samples) - int(cut_end * sample_rate)
    return samples[start_sample:end_sample]


def simple_crossfade(path_a: str, path_b: str, fade_seconds: float = 2.0) -> str:
    """
    Простой crossfade между двумя аудиофайлами
    Используется для склейки основного трека с бриджем
    """
    a, sr_a = _read_mono(path_a)
    b, sr_b = _read_mono(path_b)
    
    if sr_a != sr_b:
        raise ValueError("Sample rates do not match")
    
    fade_n = min(int(fade_seconds * sr_a), len(a), len(b))
    
    if fade_n <= 0:
        merged = np.concatenate([a, b])
        return _write_mono(merged, sr_a, "merged")
    
    # Обрезаем последние fade_seconds первого и первые fade_seconds второго
    a_trimmed = a[:-fade_n] if len(a) > fade_n else a
    b_trimmed = b[fade_n:] if len(b) > fade_n else b
    
    tail = a[-fade_n:] if len(a) >= fade_n else a
    lead = b[:fade_n] if len(b) >= fade_n else b
    
    # Плавный crossfade
    x = np.linspace(0.0, 1.0, len(tail), dtype=np.float32)
    gain_out = np.cos(x * np.pi / 2)  # Плавное затухание
    gain_in = np.sin(x * np.pi / 2)   # Плавное нарастание
    
    mixed = tail * gain_out + lead * gain_in
    
    # Собираем результат
    if len(a_trimmed) > 0 and len(b_trimmed) > 0:
        merged = np.concatenate([a_trimmed, mixed, b_trimmed])
    elif len(a_trimmed) > 0:
        merged = np.concatenate([a_trimmed, mixed])
    else:
        merged = np.concatenate([mixed, b_trimmed])
    
    return _write_mono(merged, sr_a, "merged")


def create_playable_chunk(track_path: str, bridge_path: str = None, 
                          next_track_path: str = None, 
                          crossfade: float = 2.0) -> str:
    """
    Создает готовый для воспроизведения чанк:
    - Если нет bridge и next_track: просто возвращает track
    - Если есть bridge: склеивает track + bridge
    - Если есть bridge и next_track: склеивает track + bridge + next_track с crossfade
    """
    if bridge_path is None:
        return track_path
    
    # Склеиваем track + bridge
    temp_merged = simple_crossfade(track_path, bridge_path, crossfade)
    
    if next_track_path is None:
        return temp_merged
    
    # Добавляем следующий трек
    final = simple_crossfade(temp_merged, next_track_path, crossfade)
    
    # Очищаем временный файл
    try:
        if temp_merged != track_path and os.path.exists(temp_merged):
            os.remove(temp_merged)
    except:
        pass
    
    return final


def repeat_previous_with_transition(previous_path: str, fade_seconds: float = 2.5) -> str:
    """
    Если новый фрагмент не удалось сгенерировать: повтор предыдущего трека
    с плавным переходом (crossfade хвоста в начало того же файла — бесшовное продление).
    """
    prev = os.path.abspath(previous_path)
    if not os.path.isfile(prev):
        raise FileNotFoundError(prev)
    return simple_crossfade(prev, prev, fade_seconds=fade_seconds)