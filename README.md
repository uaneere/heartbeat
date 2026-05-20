python3 -m venv venv
source venv/bin/activate
pip install poetry
poetry install --no-root
poetry run pip install --no-deps 'git+https://github.com/facebookresearch/audiocraft.git'
poetry run python3 -c "import torch; print(f'CUDA: {torch.cuda.is_available()}, версия: {torch.__version__}')"
poetry run python -m spacy download en_core_web_sm