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

# Очищать CUDA кэш после каждой генерации
CLEAR_CUDA_CACHE_EACH_GEN = os.getenv("MUSICGEN_CLEAR_CACHE", "1") == "1"

# Предзагрузка модели при старте
PRELOAD_ON_STARTUP = os.getenv("MUSICGEN_PRELOAD", "1") == "1"

# CORS настройки
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

# Папка для аудиофайлов
AUDIO_DIR = "data"