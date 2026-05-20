#!/usr/bin/env python3
"""
Автономная сессия: генерация 30-с фрагментов, переходы по разнице параметров,
воспроизведение по сегментам (голова → переход → тело).
"""

import json
import logging
import math
import os
import random
import threading
import time
from datetime import datetime

import requests

from audio_player import SegmentAudioPlayer

os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/session.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class AutonomousMusicSession:
    def __init__(self, api_url: str = "http://localhost:8000"):
        self.api_url = api_url
        self.session_id = None
        self.tick = 0
        self.running = True

        self.profile = {
            "age": 28,
            "sex": "female",
            "weight": 65,
            "height": 170,
            "resting_hr": 68,
            "avg_active_hr": 155,
            "blood_pressure": "118/75",
            "conditions": [],
            "preferred_genres": ["electronic", "house", "ambient", "lofi"],
        }

        self.daily_schedule = [
            {"time": 0, "activity": "sleep", "duration": 8, "goal": "recovery_run", "intensity_base": 0.1},
            {"time": 8, "activity": "meditation", "duration": 0.5, "goal": "stress_reduction", "intensity_base": 0.1},
            {"time": 8.5, "activity": "studying", "duration": 2, "goal": "general_fitness", "intensity_base": 0.2},
            {"time": 10.5, "activity": "gaming", "duration": 1.5, "goal": "general_fitness", "intensity_base": 0.4},
            {"time": 12, "activity": "walking", "duration": 1, "goal": "fat_burning", "intensity_base": 0.5},
            {"time": 13, "activity": "studying", "duration": 3, "goal": "general_fitness", "intensity_base": 0.2},
            {"time": 16, "activity": "yoga", "duration": 1, "goal": "stress_reduction", "intensity_base": 0.3},
            {"time": 17, "activity": "gym", "duration": 1.5, "goal": "hypertrophy", "intensity_base": 0.7},
            {"time": 18.5, "activity": "running", "duration": 0.5, "goal": "sprint", "intensity_base": 0.85},
            {"time": 19, "activity": "walking", "duration": 1, "goal": "cooldown", "intensity_base": 0.4},
            {"time": 20, "activity": "gaming", "duration": 2, "goal": "general_fitness", "intensity_base": 0.3},
            {"time": 22, "activity": "meditation", "duration": 0.5, "goal": "sleep_prep", "intensity_base": 0.1},
            {"time": 22.5, "activity": "sleep", "duration": 8, "goal": "recovery_run", "intensity_base": 0.05},
        ]

        self.current_activity = "sleep"
        self.current_goal = "recovery_run"
        self.current_intensity = 0.1
        self.current_stress = 0.2
        self.current_hr = 68
        self.day_hour = 7.0
        self._last_patched_activity: str | None = None

        self.generated_tracks = []
        self.last_playback_plan: list[dict] = []

        self.audio_player = SegmentAudioPlayer()
        self._generating = False
        self._gen_lock = threading.Lock()
        self._last_gen_finished = 0.0
        self._last_repeat_enqueue = 0.0
        # За сколько секунд до конца очереди заказывать следующий фрагмент
        self.prefetch_lead_sec = float(os.getenv("GEN_PREFETCH_LEAD_SEC", "50"))

        # Скорость «виртуального дня»: N реальных минут = 1 виртуальный час
        # Было *2 (слишком быстро: сон→медитация→учёба за минуту). По умолчанию 4 мин/час.
        self.real_minutes_per_virtual_hour = float(
            os.getenv("SIM_MINUTES_PER_VIRTUAL_HOUR", "4")
        )

    def start_playback(self) -> None:
        self.audio_player.start()

    def get_current_activity(self) -> tuple:
        hour_mod = self.day_hour % 24
        for schedule in self.daily_schedule:
            if schedule["time"] <= hour_mod < schedule["time"] + schedule["duration"]:
                return schedule["activity"], schedule["goal"], schedule["intensity_base"]
        return "walking", "general_fitness", 0.3

    def update_hr_and_intensity(self) -> tuple:
        activity, goal, intensity_base = self.get_current_activity()

        if activity != self.current_activity:
            logger.info(
                f"🔄 Смена активности: {self.current_activity} → {activity} "
                f"(вирт. время {self.day_hour:.2f}h)"
            )
            self.current_activity = activity
            self.current_goal = goal
            self.update_context()

        circadian = 0.1 * math.sin((self.day_hour - 14) * math.pi / 12)
        noise = random.uniform(-0.1, 0.1)
        target_intensity = max(0.05, min(0.95, intensity_base + circadian + noise))
        self.current_intensity += (target_intensity - self.current_intensity) * 0.3

        if activity == "sleep":
            target_hr = self.profile["resting_hr"] - 5
        elif activity == "meditation":
            target_hr = self.profile["resting_hr"] + 5
        elif activity == "running":
            target_hr = self.profile["avg_active_hr"] + 10 * self.current_intensity
        elif activity == "gym":
            target_hr = self.profile["resting_hr"] + 50 * self.current_intensity
        else:
            target_hr = self.profile["resting_hr"] + 30 * self.current_intensity

        if random.random() < 0.05:
            self.current_stress = min(0.9, self.current_stress + random.uniform(0.1, 0.3))
        else:
            self.current_stress = max(0.1, self.current_stress - random.uniform(0.05, 0.1))

        hr_change = (target_hr - self.current_hr) * 0.2 + random.randint(-3, 3)
        self.current_hr = max(40, min(200, self.current_hr + hr_change))
        return self.current_hr, self.current_intensity, self.current_stress

    def wait_for_model_ready(self, timeout_sec: float = 600) -> bool:
        """Ждём предзагрузку MusicGen (/ready), чтобы не ловить 500 на первом generate."""
        deadline = time.time() + timeout_sec
        logger.info("⏳ Ожидание готовности MusicGen (/ready)...")
        while time.time() < deadline:
            try:
                r = requests.get(f"{self.api_url}/ready", timeout=10)
                if r.status_code == 200 and r.json().get("ready"):
                    info = r.json()
                    logger.info(
                        "✅ Модель готова: %s, фрагмент %.0fs",
                        info.get("model_key"),
                        info.get("chunk_duration_sec", 0),
                    )
                    return True
                if r.status_code == 503:
                    logger.info("   …ещё загружается (%s)", r.json().get("message", ""))
            except Exception as e:
                logger.debug("ready poll: %s", e)
            time.sleep(5)
        logger.error("❌ Таймаут ожидания модели")
        return False

    def start_session(self) -> bool:
        payload = {
            "profile": self.profile,
            "session": {
                "activity_type": self.current_activity,
                "goal": self.current_goal,
                "manual_tempo_preference": "medium",
                "time_signature": "4/4",
            },
        }
        try:
            response = requests.post(
                f"{self.api_url}/sessions/start", json=payload, timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                self.session_id = data["session_id"]
                self.tick = data["tick"]
                self._last_patched_activity = self.current_activity
                logger.info(f"✅ Сессия создана: {self.session_id}")
                return True
            logger.error(f"❌ Ошибка создания сессии: {response.status_code}")
            return False
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
            return False

    def update_context(self) -> bool:
        if self._last_patched_activity == self.current_activity:
            return True
        payload = {
            "activity_type": self.current_activity,
            "goal": self.current_goal,
        }
        try:
            response = requests.patch(
                f"{self.api_url}/sessions/{self.session_id}/context",
                json=payload,
                timeout=5,
            )
            if response.status_code == 200:
                self._last_patched_activity = self.current_activity
            return response.status_code == 200
        except Exception:
            return False

    def _enqueue_playback(self, playback: list[dict]) -> None:
        if not playback:
            return
        self.last_playback_plan = playback
        self._last_repeat_enqueue = 0.0
        n = self.audio_player.enqueue_segments(playback)
        logger.info(f"▶️ В очередь добавлено сегментов: {n}")

    def _enqueue_repeat_fallback(self) -> None:
        if self.last_playback_plan:
            logger.warning("🔁 Повтор последнего плана воспроизведения (генерация не успела)")
            self.audio_player.enqueue_segments(self.last_playback_plan)
            return
        logger.warning("⚠️ Нет плана для повтора")

    def _generate_once(self) -> None:
        with self._gen_lock:
            if self._generating:
                return
            self._generating = True

        try:
            tick_payload = {
                "movement_intensity": self.current_intensity,
                "stress_level": self.current_stress,
            }
            tick_response = requests.post(
                f"{self.api_url}/sessions/{self.session_id}/tick",
                json=tick_payload,
                timeout=10,
            )
            if tick_response.status_code != 200:
                logger.error(f"❌ tick: {tick_response.status_code}")
                self._enqueue_repeat_fallback()
                return

            tick_data = tick_response.json()
            self.tick = tick_data["tick"]
            current_hr = tick_data["realtime"]["current_hr"]

            gen_payload = {
                "movement_intensity": self.current_intensity,
                "stress_level": self.current_stress,
                "force_regenerate": True,
                "generate_audio": True,
                "seed": int(time.time()),
            }

            logger.info("⏳ Генерация фрагмента (ожидайте ~1 мин)...")
            gen_response = requests.post(
                f"{self.api_url}/sessions/{self.session_id}/generate",
                json=gen_payload,
                timeout=300,
            )

            if gen_response.status_code != 200:
                logger.error(f"❌ generate: {gen_response.status_code}")
                self._enqueue_repeat_fallback()
                return

            result = gen_response.json()["result"]
            if result.get("transition_mode") == "error":
                logger.error("❌ Сервер не сгенерировал аудио — см. логи run.py")
                self._enqueue_repeat_fallback()
                return

            playback = result.get("playback") or []

            if playback:
                self._enqueue_playback(playback)
            elif result.get("fragment_file") and os.path.isfile(result["fragment_file"]):
                from stream_logic import playback_plan_first_fragment, segments_to_dicts

                fade = float(result.get("fade_seconds", 2.5))
                plan = segments_to_dicts(
                    playback_plan_first_fragment(result["fragment_file"], fade)
                )
                self._enqueue_playback(plan)
            elif not playback:
                logger.warning("⚠️ Пустой playback — повтор")
                self._enqueue_repeat_fallback()

            logger.info(
                f"📊 Тик {self.tick}: {result['target_bpm']} BPM | {result['target_genre']} | "
                f"fade={result.get('fade_seconds', 2.5)}s | mode={result.get('transition_mode')}"
            )
            if result.get("fragment_file"):
                logger.info(f"   Фрагмент: {os.path.basename(result['fragment_file'])}")
            if result.get("transition_file"):
                logger.info(f"   Переход: {os.path.basename(result['transition_file'])}")

            self.generated_tracks.append(
                {
                    "tick": self.tick,
                    "time": datetime.now().isoformat(),
                    "activity": self.current_activity,
                    "hr": current_hr,
                    "bpm": result["target_bpm"],
                    "genre": result["target_genre"],
                    "fade_seconds": result.get("fade_seconds"),
                    "transition_mode": result.get("transition_mode"),
                    "playback": playback,
                }
            )

        except requests.exceptions.Timeout:
            logger.error("❌ Таймаут генерации")
            self._enqueue_repeat_fallback()
        except Exception as e:
            logger.error(f"❌ Ошибка генерации: {e}")
            self._enqueue_repeat_fallback()
        finally:
            with self._gen_lock:
                self._generating = False
            self._last_gen_finished = time.time()
            if self.running:
                self.schedule_generation()

    def schedule_generation(self) -> None:
        """Следующий фрагмент — только если предыдущая генерация завершена."""
        with self._gen_lock:
            if self._generating:
                return
        threading.Thread(target=self._generate_once, daemon=True).start()

    def _maybe_buffer_while_generating(self) -> None:
        """Пока GPU генерирует — крутим последний план, чтобы не было тишины."""
        if not self.last_playback_plan:
            return
        with self._gen_lock:
            if not self._generating:
                return
        remaining = self.audio_player.estimated_remaining_seconds()
        if remaining > 12.0:
            return
        now = time.time()
        if now - self._last_repeat_enqueue < 20.0:
            return
        self._last_repeat_enqueue = now
        self._enqueue_repeat_fallback()

    def run_autonomous(self, duration_minutes: float = 20, min_gap_between_gen: float = 0.0):
        logger.info("=" * 70)
        logger.info("🚀 АВТОНОМНАЯ СЕССИЯ (фрагмент + переход x с + сегменты)")
        logger.info(
            f"   Длительность: {duration_minutes} мин | префетч за {self.prefetch_lead_sec:.0f} с до конца"
        )
        logger.info(
            f"   Симуляция: 1 вирт. час = {self.real_minutes_per_virtual_hour:.0f} реальных мин"
        )
        logger.info(f"   API: {self.api_url}")
        logger.info("=" * 70)

        try:
            if requests.get(f"{self.api_url}/docs", timeout=5).status_code != 200:
                logger.warning("⚠️ API ответил не 200")
        except requests.exceptions.ConnectionError:
            logger.error("❌ API недоступен. Запустите: python3 run.py")
            return

        if not self.start_session():
            return

        if not self.wait_for_model_ready():
            return

        self.update_context()
        self.start_playback()

        start_time = time.time()
        end_time = start_time + duration_minutes * 60

        logger.info("🎵 Старт первой генерации...")
        self.schedule_generation()

        last_status = 0.0
        while time.time() < end_time and self.running:
            now = time.time()
            elapsed_real_min = (now - start_time) / 60
            self.day_hour = 7.0 + elapsed_real_min / self.real_minutes_per_virtual_hour

            hr, intensity, stress = self.update_hr_and_intensity()

            remaining = self.audio_player.estimated_remaining_seconds()
            with self._gen_lock:
                gen_idle = not self._generating

            self._maybe_buffer_while_generating()

            # Следующий фрагмент — пока играет текущий (префетч), не после долгой паузы
            if gen_idle and (now - self._last_gen_finished) >= min_gap_between_gen:
                need_gen = (
                    self._last_gen_finished == 0.0
                    or remaining < self.prefetch_lead_sec
                )
                if need_gen:
                    self.schedule_generation()

            if now - last_status >= 5:
                activity, _, _ = self.get_current_activity()
                q = self.audio_player.get_queue_size()
                busy = "ген..." if not gen_idle else "ожидание"
                logger.info(
                    f"⏱️ {self.day_hour:.1f}h | {activity} | HR:{int(hr)} | "
                    f"очередь:{q} | ~{remaining:.0f}s аудио | {busy}"
                )
                last_status = now

            time.sleep(1)

        logger.info("=" * 70)
        logger.info(f"📊 Треков в истории: {len(self.generated_tracks)}")
        history_file = f"logs/session_{int(start_time)}.json"
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(self.generated_tracks, f, indent=2, ensure_ascii=False)
        self.audio_player.stop()
        logger.info("✅ Сессия завершена")


if __name__ == "__main__":
    session = AutonomousMusicSession(api_url="http://localhost:8000")
    session.run_autonomous(duration_minutes=20, min_gap_between_gen=0.0)
