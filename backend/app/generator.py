"""MusicGen обертка для генерации аудио"""

import logging
import os
import threading

import torch
import soundfile as sf

from app.config import (
    CHUNK_DURATION_SEC,
    CLEAR_CUDA_CACHE_EACH_GEN,
    DEFAULT_MODEL_KEY,
    MODEL_PRESETS,
    AUDIO_DIR,
)

logger = logging.getLogger(__name__)

_MODEL = None
_ACTIVE_MODEL_KEY: str | None = None
_MODEL_READY = False
_GEN_LOCK = threading.Lock()

def _clear_cuda_cache() -> None:
    """Очистка CUDA кэша"""
    if CLEAR_CUDA_CACHE_EACH_GEN and torch.cuda.is_available():
        torch.cuda.empty_cache()

def _configure_generation(model, duration: float) -> None:
    """Настройка параметров генерации"""
    model.set_generation_params(
        duration=duration,
        temperature=1.0,
        top_k=250,
        cfg_coef=3.0,
    )

def get_model(model_key: str | None = None, *, force_reload: bool = False):
    """Загрузка модели MusicGen"""
    global _MODEL, _ACTIVE_MODEL_KEY, _MODEL_READY
    
    key = (model_key or DEFAULT_MODEL_KEY).strip().lower()
    if key not in MODEL_PRESETS:
        key = DEFAULT_MODEL_KEY
    
    if _MODEL is not None and not force_reload and _ACTIVE_MODEL_KEY == key:
        return _MODEL
    
    from audiocraft.models import MusicGen
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    repo_id = MODEL_PRESETS[key]
    
    logger.info("Loading MusicGen: %s on %s", key, device)
    _MODEL = MusicGen.get_pretrained(repo_id, device=device)
    _configure_generation(_MODEL, CHUNK_DURATION_SEC)
    _ACTIVE_MODEL_KEY = key
    _MODEL_READY = True
    
    logger.info("MusicGen ready: %s", key)
    return _MODEL

def preload_model() -> None:
    """Предзагрузка модели при старте"""
    with _GEN_LOCK:
        get_model()

def is_model_ready() -> bool:
    """Проверка готовности модели"""
    return _MODEL_READY and _MODEL is not None

def get_active_model_info() -> dict:
    """Информация о текущей модели"""
    return {
        "model_key": _ACTIVE_MODEL_KEY or DEFAULT_MODEL_KEY,
        "ready": is_model_ready(),
        "chunk_duration_sec": CHUNK_DURATION_SEC,
    }

def generate_audio(prompt: str, duration_seconds: float | None = None, seed: int | None = None) -> str:
    """
    Генерация аудио по промпту
    
    Args:
        prompt: Текстовый промпт
        duration_seconds: Длительность в секундах
        seed: Seed для воспроизводимости
    
    Returns:
        Путь к сгенерированному файлу
    """
    from datetime import datetime
    import numpy as np
    
    dur = duration_seconds or CHUNK_DURATION_SEC
    
    with _GEN_LOCK:
        try:
            model = get_model()
            _configure_generation(model, dur)
            
            if seed is not None:
                torch.manual_seed(seed)
            
            wav = model.generate([prompt])
            
            # Сохраняем WAV
            os.makedirs(AUDIO_DIR, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            output_path = os.path.join(AUDIO_DIR, f"track_{timestamp}.wav")
            
            # Конвертируем в numpy и сохраняем
            audio_np = wav[0].cpu().numpy()
            if audio_np.ndim > 1:
                audio_np = audio_np.mean(axis=0)
            
            sf.write(output_path, audio_np, model.sample_rate)
            
            _clear_cuda_cache()
            logger.info("Generated: %s", output_path)
            return output_path
            
        except Exception as e:
            logger.error("Generation failed: %s", e)
            raise