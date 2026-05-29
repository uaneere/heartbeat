# Heartbeat Music Generator API

API для генерации музыки на основе пульса и активности.

## 🚀 Быстрый старт

### Установка

```bash
# Клонировать репозиторий
git clone <repo-url>
cd backend

# Установить Poetry (если не установлен)
pip install poetry

# Установить зависимости
poetry install --no-root

# Установить Audiocraft
poetry run pip install --no-deps 'git+https://github.com/facebookresearch/audiocraft.git'

# Запустить сервер
poetry run python run.py