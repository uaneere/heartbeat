#!/usr/bin/env python3
"""
Клиент для ручного управления API
"""

import requests
import json
import time
import sys

API_URL = "http://localhost:8000"

def test_health():
    """Проверка доступности API"""
    try:
        response = requests.get(f"{API_URL}/docs")
        print("✅ API доступен")
        return True
    except:
        print("❌ API не доступен")
        return False

def create_session():
    """Создание сессии"""
    payload = {
        "profile": {
            "age": 28,
            "sex": "female",
            "weight": 65,
            "height": 170,
            "resting_hr": 68,
            "avg_active_hr": 155,
            "blood_pressure": "118/75",
            "conditions": [],
            "preferred_genres": ["electronic", "house", "ambient"]
        },
        "session": {
            "activity_type": "running",
            "goal": "fat_burning",
            "manual_tempo_preference": "medium",
            "time_signature": "4/4"
        }
    }
    
    response = requests.post(f"{API_URL}/sessions/start", json=payload)
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Сессия создана: {data['session_id']}")
        return data['session_id']
    else:
        print(f"❌ Ошибка: {response.status_code}")
        return None

def update_context(session_id, activity, goal):
    """Обновление контекста"""
    payload = {
        "activity_type": activity,
        "goal": goal
    }
    
    response = requests.patch(f"{API_URL}/sessions/{session_id}/context", json=payload)
    if response.status_code == 200:
        print(f"✅ Контекст обновлен: {activity}, {goal}")
        return True
    else:
        print(f"❌ Ошибка: {response.status_code}")
        return False

def generate_music(session_id, intensity=0.5, stress=0.3):
    """Генерация музыки"""
    # Сначала тик
    tick_payload = {
        "movement_intensity": intensity,
        "stress_level": stress
    }
    
    tick_response = requests.post(f"{API_URL}/sessions/{session_id}/tick", json=tick_payload)
    if tick_response.status_code != 200:
        print("❌ Ошибка tick")
        return None
    
    # Генерация
    gen_payload = {
        "movement_intensity": intensity,
        "stress_level": stress,
        "force_regenerate": True,
        "generate_audio": True
    }
    
    gen_response = requests.post(f"{API_URL}/sessions/{session_id}/generate", json=gen_payload)
    if gen_response.status_code == 200:
        data = gen_response.json()
        result = data["result"]
        print(f"🎵 Сгенерирован трек:")
        print(f"   BPM: {result['target_bpm']}")
        print(f"   Жанр: {result['target_genre']}")
        print(f"   Энергия: {result['target_energy']}")
        print(f"   Файл: {result['file']}")
        return result
    else:
        print(f"❌ Ошибка генерации: {gen_response.status_code}")
        return None

def interactive_mode():
    """Интерактивный режим"""
    print("Heartbeat Music Generator - Интерактивный режим")
    print("=" * 50)
    
    if not test_health():
        return
    
    session_id = create_session()
    if not session_id:
        return
    
    print("\nКоманды:")
    print("  a <activity> <goal> - сменить активность")
    print("  g <intensity> - сгенерировать музыку (intensity 0-1)")
    print("  s - показать статус")
    print("  q - выход")
    
    while True:
        cmd = input("\n> ").strip().split()
        if not cmd:
            continue
        
        if cmd[0] == 'q':
            break
        elif cmd[0] == 'a' and len(cmd) >= 3:
            update_context(session_id, cmd[1], cmd[2])
        elif cmd[0] == 'g':
            intensity = float(cmd[1]) if len(cmd) > 1 else 0.5
            generate_music(session_id, intensity)
        elif cmd[0] == 's':
            print(f"Сессия: {session_id}")

if __name__ == "__main__":
    interactive_mode()