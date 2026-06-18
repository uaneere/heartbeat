FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libsndfile1 \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install poetry

COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
    && poetry install --no-root --no-interaction --no-ansi

RUN pip install --no-deps 'git+https://github.com/facebookresearch/audiocraft.git'

COPY . .

RUN mkdir -p /app/data /app/logs

EXPOSE 8000

CMD ["python", "run.py"]
