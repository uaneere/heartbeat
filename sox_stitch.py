import subprocess
import os
import time

def sox_crossfade(path_a: str, path_b: str, fade_seconds: float = 4.0) -> str:
    """Использует SoX для идеального crossfade без щелчков"""
    timestamp = int(time.time())
    output_path = f"data/sox_stitch_{timestamp}.wav"
    
    # Получаем длительность первого файла
    dur_cmd = ["soxi", "-D", path_a]
    duration = float(subprocess.check_output(dur_cmd).decode().strip())
    
    # Точка начала crossfade
    splice_point = duration - fade_seconds
    
    cmd = [
        "sox",
        path_a, path_b,
        output_path,
        "splice", str(splice_point), str(fade_seconds)
    ]
    
    subprocess.run(cmd, check=True)
    return output_path

def sox_smooth_transition(path_a: str, path_b: str, fade_seconds: float = 5.0) -> str:
    """Максимально плавный переход через SoX"""
    timestamp = int(time.time())
    output_path = f"data/sox_smooth_{timestamp}.wav"
    
    # Нормализуем громкость
    norm_a = path_a.replace(".wav", "_norm.wav")
    norm_b = path_b.replace(".wav", "_norm.wav")
    
    subprocess.run(["sox", path_a, norm_a, "norm", "-3"], capture_output=True)
    subprocess.run(["sox", path_b, norm_b, "norm", "-3"], capture_output=True)
    
    # Создаем переход с fade in/out
    cmd = [
        "sox",
        norm_a, norm_b,
        output_path,
        "splice", f"$(soxi -D {norm_a})-{fade_seconds}", str(fade_seconds)
    ]
    
    subprocess.run(" ".join(cmd), shell=True)
    
    # Очистка
    for f in [norm_a, norm_b]:
        if os.path.exists(f) and f != path_a and f != path_b:
            os.remove(f)
    
    return output_path