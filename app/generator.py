import logging
import os
import threading

import soundfile as sf
import torch

from app.musicgen_config import (
    CHUNK_DURATION_SEC,
    CLEAR_CUDA_CACHE_EACH_GEN,
    CONTINUATION_TAIL_SEC,
    DEFAULT_MODEL_KEY,
    EXTEND_STRIDE_SEC,
    FALLBACK_MODEL_KEY,
    MODEL_PRESETS,
)
from app.wav_paths import new_wav_path

logger = logging.getLogger(__name__)

MODEL = None
_ACTIVE_MODEL_KEY: str | None = None
_MODEL_READY = False
_GEN_LOCK = threading.Lock()


def _resolve_model_key(key: str | None = None) -> str:
    k = (key or DEFAULT_MODEL_KEY).strip().lower()
    return k if k in MODEL_PRESETS else DEFAULT_MODEL_KEY


def _is_melody_model(model_key: str) -> bool:
    return model_key == "melody"


def _apply_cuda_optimizations() -> None:
    if not torch.cuda.is_available():
        return
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True
    try:
        torch.set_float32_matmul_precision("medium")
    except AttributeError:
        pass


def _clear_cuda_cache() -> None:
    if CLEAR_CUDA_CACHE_EACH_GEN and torch.cuda.is_available():
        torch.cuda.empty_cache()


def _configure_generation(model, duration: float) -> None:
    """Параметры, с которыми medium стабильнее на 6GB VRAM."""
    extend = min(EXTEND_STRIDE_SEC, max(2.0, duration - 1))
    model.set_generation_params(
        duration=duration,
        extend_stride=extend,
        two_step_cfg=False,
        top_k=250,
        temperature=1.0,
        cfg_coef=3.0,
    )


def get_model(model_key: str | None = None, *, force_reload: bool = False):
    global MODEL, _ACTIVE_MODEL_KEY, _MODEL_READY
    key = _resolve_model_key(model_key)

    if MODEL is not None and not force_reload and _ACTIVE_MODEL_KEY == key:
        return MODEL

    from audiocraft.models import MusicGen

    _apply_cuda_optimizations()
    repo_id = MODEL_PRESETS[key]
    logger.info("Загрузка MusicGen: %s (%s), duration=%.0fs", key, repo_id, CHUNK_DURATION_SEC)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    MODEL = MusicGen.get_pretrained(repo_id, device=device)
    _configure_generation(MODEL, CHUNK_DURATION_SEC)
    _ACTIVE_MODEL_KEY = key
    _MODEL_READY = True
    logger.info("MusicGen готов: %s на %s", key, device)
    return MODEL


def preload_model() -> None:
    """Вызвать при старте API, чтобы не грузить веса во время /generate."""
    with _GEN_LOCK:
        get_model()


def is_model_ready() -> bool:
    return _MODEL_READY and MODEL is not None


def _reload_fallback_model():
    global MODEL, _ACTIVE_MODEL_KEY, _MODEL_READY
    logger.warning("Переключаемся на %s", FALLBACK_MODEL_KEY)
    MODEL = None
    _ACTIVE_MODEL_KEY = None
    _MODEL_READY = False
    return get_model(FALLBACK_MODEL_KEY, force_reload=True)


def build_prompt(
    *,
    bpm: int,
    mood: str,
    genre: str,
    energy: str,
    activity_type: str,
    goal: str,
    mode: str,
    time_signature: str,
    continuation: bool = False,
) -> str:
    base = (
        f"{genre}, {mood}, {energy} energy, {bpm} bpm, "
        f"time signature {time_signature}, stable groove, consistent instrumentation, "
        f"activity {activity_type}, goal {goal}, mode {mode}, high quality"
    )
    if continuation:
        return (
            f"{base}, seamless continuation of previous section, "
            "same key and instrumentation, natural evolution, no abrupt change"
        )
    return base


def _write_wav(tensor, sample_rate: int) -> str:
    from audiocraft.data.audio import audio_write

    out_wav = new_wav_path("track")
    stem = out_wav[:-4] if out_wav.endswith(".wav") else out_wav
    audio_write(stem, tensor.cpu(), sample_rate)
    return stem + ".wav"


def _load_tail_mono(path: str, tail_seconds: float) -> tuple[torch.Tensor, int]:
    samples, sr = sf.read(path, dtype="float32")
    if samples.ndim > 1:
        samples = samples.mean(axis=1)
    n = max(1, int(tail_seconds * sr))
    tail = samples[-n:]
    wav = torch.from_numpy(tail).float().unsqueeze(0)
    return wav, sr


def _is_recoverable_gen_error(exc: BaseException) -> bool:
    if isinstance(exc, AssertionError):
        return True
    if isinstance(exc, RuntimeError):
        msg = str(exc).lower()
        return "out of memory" in msg or "cuda" in msg
    return False


def _run_with_fallback(fn):
    try:
        with torch.inference_mode():
            return fn()
    except Exception as exc:
        if not _is_recoverable_gen_error(exc):
            raise
        logger.warning("Ошибка генерации (%s), fallback → %s", type(exc).__name__, FALLBACK_MODEL_KEY)
        _reload_fallback_model()
        with torch.inference_mode():
            return fn()


def generate(prompt: str, duration_seconds: float | None = None, seed: int | None = None) -> str:
    dur = duration_seconds or CHUNK_DURATION_SEC

    def _do():
        model = get_model()
        _configure_generation(model, dur)
        if seed is not None:
            torch.manual_seed(seed)
        wav = model.generate([prompt])
        path = _write_wav(wav[0], model.sample_rate)
        _clear_cuda_cache()
        return path

    with _GEN_LOCK:
        return _run_with_fallback(_do)


def generate_continuation(
    prompt: str,
    previous_fragment_path: str,
    duration_seconds: float | None = None,
    tail_seconds: float = CONTINUATION_TAIL_SEC,
    seed: int | None = None,
) -> str:
    dur = duration_seconds or CHUNK_DURATION_SEC

    def _do():
        model = get_model()
        extend = min(EXTEND_STRIDE_SEC, tail_seconds, max(2.0, dur - 1))
        _configure_generation(model, dur)
        model.set_generation_params(duration=dur, extend_stride=extend)
        if seed is not None:
            torch.manual_seed(seed)

        prompt_wav, prompt_sr = _load_tail_mono(previous_fragment_path, tail_seconds)
        active = _ACTIVE_MODEL_KEY or DEFAULT_MODEL_KEY

        if _is_melody_model(active) and hasattr(model, "generate_with_chroma"):
            logger.info(
                "MusicGen-melody: chroma tail=%.1fs from %s",
                tail_seconds,
                os.path.basename(previous_fragment_path),
            )
            wav = model.generate_with_chroma(
                [prompt],
                melody_wavs=[prompt_wav],
                melody_sample_rate=prompt_sr,
                progress=False,
            )
        else:
            logger.info(
                "MusicGen continuation: tail=%.1fs from %s",
                tail_seconds,
                os.path.basename(previous_fragment_path),
            )
            wav = model.generate_continuation(
                prompt_wav,
                prompt_sample_rate=prompt_sr,
                descriptions=[prompt],
                progress=False,
            )

        path = _write_wav(wav[0], model.sample_rate)
        _clear_cuda_cache()
        return path

    with _GEN_LOCK:
        return _run_with_fallback(_do)


def generate_fragment(
    prompt: str,
    *,
    duration_seconds: float | None = None,
    seed: int | None = None,
    previous_fragment_path: str | None = None,
    use_continuation: bool = False,
    tail_seconds: float = CONTINUATION_TAIL_SEC,
) -> tuple[str, str]:
    dur = duration_seconds or CHUNK_DURATION_SEC
    model_key = _ACTIVE_MODEL_KEY or DEFAULT_MODEL_KEY

    if use_continuation and previous_fragment_path and os.path.isfile(previous_fragment_path):
        try:
            path = generate_continuation(
                prompt,
                previous_fragment_path,
                duration_seconds=dur,
                tail_seconds=tail_seconds,
                seed=seed,
            )
            method = "melody" if _is_melody_model(model_key) else "continuation"
            return path, method
        except Exception as exc:
            logger.warning("Continuation failed, fresh generate: %s", exc)

    path = generate(prompt, duration_seconds=dur, seed=seed)
    return path, "fresh"


def get_active_model_info() -> dict:
    return {
        "model_key": _ACTIVE_MODEL_KEY or DEFAULT_MODEL_KEY,
        "configured": DEFAULT_MODEL_KEY,
        "repo": MODEL_PRESETS.get(_ACTIVE_MODEL_KEY or DEFAULT_MODEL_KEY, ""),
        "chunk_duration_sec": CHUNK_DURATION_SEC,
        "tail_sec": CONTINUATION_TAIL_SEC,
        "extend_stride_sec": EXTEND_STRIDE_SEC,
        "ready": is_model_ready(),
    }
