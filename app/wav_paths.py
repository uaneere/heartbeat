"""Имена выходных WAV: dd.mm.yyyy-hh.mm.ss.wav (локальное время)."""

import os
from datetime import datetime


def new_wav_path(name_prefix: str = "track") -> str:
    """
    Возвращает путь вида data/dd.mm.yyyy-HH.MM.SS.wav.
    При коллизии в ту же секунду: dd.mm.yyyy-HH.MM.SS_2.wav и т.д.
    name_prefix используется только в суффиксе при коллизии (логирование).
    """
    os.makedirs("data", exist_ok=True)
    base = datetime.now().strftime("%d.%m.%Y-%H.%M.%S")
    path = os.path.join("data", f"{base}.wav")
    if not os.path.exists(path):
        return path
    for i in range(2, 10_000):
        candidate = os.path.join("data", f"{base}_{i}.wav")
        if not os.path.exists(candidate):
            return candidate
    return os.path.join("data", f"{base}_{name_prefix}_{os.getpid()}.wav")
