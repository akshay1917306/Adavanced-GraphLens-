# GraphLens pipeline image (development). Python 3.11.17, same as the API image.
FROM python:3.11-slim@sha256:b7a9e5f6a93d6d4a31f129bbd4bdee69efccb6ded0fb230d78aafaf37af98377

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    TIKTOKEN_CACHE_DIR=/opt/tiktoken \
    PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir uv==0.11.32

WORKDIR /pipeline
COPY pyproject.toml uv.lock ./
# Dev tools (pytest, ruff) are included so tests can run in this container.
RUN uv sync --frozen --no-install-project

# Download the token vocabulary once at build time, so runs work offline afterwards.
RUN python -c "import tiktoken; tiktoken.get_encoding('o200k_base')"

COPY graphlens_pipeline ./graphlens_pipeline
COPY tests ./tests

# Run as a normal user, not root.
RUN useradd --create-home --uid 10001 graphlens && chmod -R a+rX /opt/tiktoken
USER graphlens

ENTRYPOINT ["python", "-m", "graphlens_pipeline"]
