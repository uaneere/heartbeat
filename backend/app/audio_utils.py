"""
Утилиты для работы с аудио (crossfade, чтение/запись)
"""

import os
import numpy as np
import soundfile as sf
from datetime import datetime

from app.config import AUDIO_DIR


def read_mono(path: str) -> tuple[np.ndarray, int]:
    """Читает WAV в моно"""
    samples, sample_rate = sf.read(path, dtype="float32")
    if samples.ndim > 1:
        samples = samples.mean(axis=1)
    return samples, sample_rate


def write_audio(samples: np.ndarray, sample_rate: int, prefix: str = "audio") -> str:
    """Сохраняет аудио в файл"""
    os.makedirs(AUDIO_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    path = os.path.join(AUDIO_DIR, f"{prefix}_{timestamp}.wav")
    sf.write(path, samples, sample_rate)
    return path


def crossfade_files(file_a: str, file_b: str, fade_seconds: float = 2.0) -> str:
    """
    Простой рабочий crossfade между двумя файлами
    
    Args:
        file_a: Первый файл
        file_b: Второй файл
        fade_seconds: Длительность перехода в секундах
    
    Returns:
        Путь к склеенному файлу
    """
    # Читаем оба файла
    audio_a, sr_a = read_mono(file_a)
    audio_b, sr_b = read_mono(file_b)
    
    # Ресэмплинг если нужно
    if sr_a != sr_b:
        from scipy import signal
        logger.warning(f"Resampling from {sr_b} to {sr_a}")
        audio_b = signal.resample(audio_b, int(len(audio_b) * sr_a / sr_b))
        sr_b = sr_a
    
    # Количество семплов для fade
    fade_samples = min(int(fade_seconds * sr_a), len(audio_a), len(audio_b))
    
    if fade_samples <= 0:
        merged = np.concatenate([audio_a, audio_b])
    else:
        # Обрезаем конец первого и начало второго
        tail = audio_a[-fade_samples:]
        head = audio_b[:fade_samples]
        body_a = audio_a[:-fade_samples]
        body_b = audio_b[fade_samples:]
        
        # Equal-power crossfade
        x = np.linspace(0, np.pi/2, fade_samples)
        fade_out = np.cos(x) ** 2
        fade_in = np.sin(x) ** 2
        
        crossfaded = tail * fade_out + head * fade_in
        merged = np.concatenate([body_a, crossfaded, body_b])
    
    return write_audio(merged, sr_a, "crossfade")


def get_audio_url(filename: str) -> str:
    """Формирует URL для доступа к аудиофайлу"""
    return f"/api/v1/audio/{filename}"


def get_filename_from_path(path: str) -> str:
    """Извлекает имя файла из пути"""
    return os.path.basename(path)