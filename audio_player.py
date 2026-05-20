#!/usr/bin/env python3
"""
Плеер по сегментам: ffplay -ss START -t DURATION для непрерывного стрима.
"""

import logging
import os
import queue
import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class PlaySegment:
    file: str
    start: float
    duration: float
    kind: str = "segment"

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "PlaySegment":
        return cls(
            file=d["file"],
            start=float(d.get("start", 0)),
            duration=float(d["duration"]),
            kind=d.get("kind", "segment"),
        )


class SegmentAudioPlayer:
    """Очередь сегментов (фрагмент / переход), воспроизведение без пауз между ними."""

    def __init__(self):
        self._queue: queue.Queue[PlaySegment | None] = queue.Queue()
        self._running = True
        self._process: subprocess.Popen | None = None
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._queued_seconds = 0.0
        self._playing_until = 0.0

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("🎵 Плеер сегментов запущен")

    def enqueue_segments(self, segments: list[dict[str, Any]] | list[PlaySegment]) -> int:
        n = 0
        for item in segments:
            seg = item if isinstance(item, PlaySegment) else PlaySegment.from_dict(item)
            if os.path.isfile(seg.file):
                with self._lock:
                    self._queued_seconds += seg.duration
                self._queue.put(seg)
                n += 1
                logger.info(
                    "📁 Сегмент: %s [%s %.1f-%.1f] %.1fs",
                    os.path.basename(seg.file),
                    seg.kind,
                    seg.start,
                    seg.start + seg.duration,
                    seg.duration,
                )
            else:
                logger.error("❌ Нет файла: %s", seg.file)
        return n

    def append_audio(self, audio_path: str) -> bool:
        """Совместимость: целый файл = один сегмент с начала."""
        if not os.path.isfile(audio_path):
            logger.error("❌ Файл не найден: %s", audio_path)
            return False
        self._queue.put(PlaySegment(file=audio_path, start=0.0, duration=30.0, kind="full"))
        return True

    def _loop(self) -> None:
        while self._running:
            try:
                seg = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue
            if seg is None:
                break
            self._play_segment(seg)

    def _play_segment(self, seg: PlaySegment) -> None:
        with self._lock:
            self._queued_seconds = max(0.0, self._queued_seconds - seg.duration)
            self._playing_until = time.time() + seg.duration
        try:
            logger.info(
                "🎵 %s | %s start=%.2fs dur=%.2fs",
                seg.kind,
                os.path.basename(seg.file),
                seg.start,
                seg.duration,
            )
            cmd = [
                "ffplay",
                "-nodisp",
                "-autoexit",
                "-loglevel",
                "error",
                "-ss",
                str(seg.start),
                "-t",
                str(seg.duration),
                seg.file,
            ]
            self._process = subprocess.Popen(cmd)
            self._process.wait()
        except Exception as e:
            logger.error("Ошибка воспроизведения: %s", e)

    def stop(self) -> None:
        self._running = False
        self._queue.put(None)
        if self._process:
            try:
                self._process.terminate()
            except OSError:
                pass
        logger.info("⏹️ Воспроизведение остановлено")

    def get_queue_size(self) -> int:
        return self._queue.qsize()

    def estimated_remaining_seconds(self) -> float:
        """Сколько аудио ещё в очереди + текущий сегмент (ffplay)."""
        with self._lock:
            playing_left = max(0.0, self._playing_until - time.time())
            return playing_left + self._queued_seconds


# Алиас для старого кода
SimpleAudioPlayer = SegmentAudioPlayer
