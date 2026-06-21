"""
Утилиты для работы с аудио (crossfade, чтение/запись, конвертация для стриминга)
"""

import logging
import os
import subprocess
import numpy as np
import soundfile as sf
from datetime import datetime

from app.config import (
    AUDIO_DIR,
    AUDIO_SERVE_FORMAT,
    DELETE_BRIDGE_WAV_AFTER_ENCODE,
    MP3_QUALITY,
    STATIC_TRACKS_PATH,
)

logger = logging.getLogger(__name__)


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


def _resample_if_needed(audio: np.ndarray, src_sr: int, target_sr: int) -> np.ndarray:
    if src_sr == target_sr:
        return audio
    from scipy import signal
    logger.warning("Resampling from %s to %s", src_sr, target_sr)
    new_len = int(len(audio) * target_sr / src_sr)
    return signal.resample(audio, new_len)


def _equal_power_crossfade(tail: np.ndarray, head: np.ndarray) -> np.ndarray:
    fade_samples = min(len(tail), len(head))
    if fade_samples <= 0:
        return np.array([], dtype=np.float32)
    tail = tail[-fade_samples:]
    head = head[:fade_samples]
    x = np.linspace(0, np.pi / 2, fade_samples)
    fade_out = np.cos(x) ** 2
    fade_in = np.sin(x) ** 2
    return tail * fade_out + head * fade_in


def create_transition_bridge(file_a: str, file_b: str, fade_seconds: float = 2.0) -> str:
    """
    Создаёт короткий файл-переход: хвост file_a плавно переходит в начало file_b.
  Используется при смене отрывков в плеере.
    """
    audio_a, sr_a = read_mono(file_a)
    audio_b, sr_b = read_mono(file_b)
    audio_b = _resample_if_needed(audio_b, sr_b, sr_a)

    fade_samples = min(int(fade_seconds * sr_a), len(audio_a), len(audio_b))
    if fade_samples <= 0:
        return write_audio(np.array([], dtype=np.float32), sr_a, "transition")

    bridge = _equal_power_crossfade(audio_a[-fade_samples:], audio_b[:fade_samples])
    return write_audio(bridge, sr_a, "transition")


def create_loop_bridge(file_path: str, fade_seconds: float = 2.0) -> str:
    """
    Создаёт плавный переход конец→начало одного отрывка.
    Используется, когда следующий отрывок ещё не готов.
    """
    audio, sr = read_mono(file_path)
    fade_samples = min(int(fade_seconds * sr), len(audio) // 2)
    if fade_samples <= 0:
        return write_audio(np.array([], dtype=np.float32), sr, "loop_bridge")

    bridge = _equal_power_crossfade(audio[-fade_samples:], audio[:fade_samples])
    return write_audio(bridge, sr, "loop_bridge")


def crossfade_files(file_a: str, file_b: str, fade_seconds: float = 2.0) -> str:
    """Склеивает два файла с crossfade (полный merge, для офлайн-склейки)."""
    audio_a, sr_a = read_mono(file_a)
    audio_b, sr_b = read_mono(file_b)
    audio_b = _resample_if_needed(audio_b, sr_b, sr_a)

    fade_samples = min(int(fade_seconds * sr_a), len(audio_a), len(audio_b))
    if fade_samples <= 0:
        merged = np.concatenate([audio_a, audio_b])
    else:
        body_a = audio_a[:-fade_samples]
        body_b = audio_b[fade_samples:]
        crossfaded = _equal_power_crossfade(audio_a, audio_b)
        merged = np.concatenate([body_a, crossfaded, body_b])

    return write_audio(merged, sr_a, "crossfade")


def convert_wav_to_mp3(wav_path: str, *, delete_source: bool = False) -> str:
    """Конвертирует WAV в MP3 через ffmpeg для потоковой отдачи клиенту."""
    mp3_path = os.path.splitext(wav_path)[0] + ".mp3"
    if os.path.exists(mp3_path):
        return mp3_path

    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            wav_path,
            "-codec:a",
            "libmp3lame",
            "-qscale:a",
            str(MP3_QUALITY),
            mp3_path,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        logger.error("ffmpeg failed for %s: %s", wav_path, result.stderr)
        raise RuntimeError(f"MP3 conversion failed: {result.stderr.strip()}")

    if delete_source:
        try:
            os.remove(wav_path)
        except OSError as exc:
            logger.warning("Could not delete source WAV %s: %s", wav_path, exc)

    return mp3_path


def prepare_for_serving(wav_path: str, *, delete_source: bool = False) -> str:
    """
    Готовит файл к отдаче клиенту.
    WAV остаётся для внутренней обработки (crossfade); клиент получает MP3 по статическому URL.
    """
    if AUDIO_SERVE_FORMAT == "wav":
        return wav_path
    return convert_wav_to_mp3(wav_path, delete_source=delete_source)


def get_audio_url(filename: str) -> str:
    """Формирует статический URL для потокового воспроизведения на клиенте."""
    return f"{STATIC_TRACKS_PATH}/{filename}"


def get_filename_from_path(path: str) -> str:
    """Извлекает имя файла из пути"""
    return os.path.basename(path)
