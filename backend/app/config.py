"""
Конфигурация приложения
"""

import os

# MusicGen настройки
MODEL_PRESETS = {
    "small": "facebook/musicgen-small",
    "medium": "facebook/musicgen-medium",
    "melody": "facebook/musicgen-melody",
}

DEFAULT_MODEL_KEY = os.getenv("MUSICGEN_MODEL", "medium").strip().lower()
if DEFAULT_MODEL_KEY not in MODEL_PRESETS:
    DEFAULT_MODEL_KEY = "medium"

# Длительность фрагмента в секундах
CHUNK_DURATION_SEC = float(os.getenv("MUSICGEN_DURATION", "30"))

# Длительность crossfade между отрывками (сек)
CROSSFADE_SEC = float(os.getenv("MUSICGEN_CROSSFADE", "2.0"))

# Очищать CUDA кэш после каждой генерации
CLEAR_CUDA_CACHE_EACH_GEN = os.getenv("MUSICGEN_CLEAR_CACHE", "1") == "1"

# Предзагрузка модели при старте
PRELOAD_ON_STARTUP = os.getenv("MUSICGEN_PRELOAD", "1") == "1"

# CORS настройки
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

# Папка для аудиофайлов
AUDIO_DIR = "data"

# Формат отдачи клиенту: mp3
AUDIO_SERVE_FORMAT = os.getenv("AUDIO_SERVE_FORMAT", "mp3").strip().lower()

# Путь для статической раздачи треков
STATIC_TRACKS_PATH = "/static/tracks"

# Качество MP3 для ffmpeg
MP3_QUALITY = os.getenv("MP3_QUALITY", "2")

# Удалять WAV после конвертации (только для bridge-файлов; сырые треки сохраняются)
DELETE_BRIDGE_WAV_AFTER_ENCODE = os.getenv("DELETE_BRIDGE_WAV_AFTER_ENCODE", "1") == "1"