"""
Выбор модели MusicGen и лимиты под железо (RTX 3050 6GB).

Переменные окружения:
  MUSICGEN_MODEL=medium|melody|small   (по умолчанию medium)
  MUSICGEN_DURATION=15                 для medium/melody на 6GB — 15 стабильнее, чем 30
  MUSICGEN_TAIL_SEC=8
  MUSICGEN_PRELOAD=1                   загрузить модель при старте API
"""

import os

MODEL_PRESETS = {
    "small": "facebook/musicgen-small",
    "medium": "facebook/musicgen-medium",
    "melody": "facebook/musicgen-melody",
}

DEFAULT_MODEL_KEY = os.getenv("MUSICGEN_MODEL", "medium").strip().lower()
if DEFAULT_MODEL_KEY not in MODEL_PRESETS:
    DEFAULT_MODEL_KEY = "medium"

FALLBACK_MODEL_KEY = "small"

# medium/melody на 6GB: 30s часто даёт AssertionError в transformer — по умолчанию 15s
if "MUSICGEN_DURATION" in os.environ:
    CHUNK_DURATION_SEC = float(os.getenv("MUSICGEN_DURATION", "15"))
else:
    CHUNK_DURATION_SEC = 15.0 if DEFAULT_MODEL_KEY in ("medium", "melody") else 30.0

CONTINUATION_TAIL_SEC = float(os.getenv("MUSICGEN_TAIL_SEC", "8"))
# extend_stride должен быть < duration (требование MusicGen)
EXTEND_STRIDE_SEC = min(
    float(os.getenv("MUSICGEN_EXTEND_STRIDE", "6")),
    max(2.0, CHUNK_DURATION_SEC - 2),
)

CLEAR_CUDA_CACHE_EACH_GEN = os.getenv("MUSICGEN_CLEAR_CACHE", "1") == "1"
PRELOAD_ON_STARTUP = os.getenv("MUSICGEN_PRELOAD", "1") == "1"
