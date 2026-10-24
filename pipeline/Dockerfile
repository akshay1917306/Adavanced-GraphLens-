# GraphLens pipeline image (development). Python 3.11.17, same as the API image.
FROM python:3.11-slim@sha256:b7a9e5f6a93d6d4a31f129bbd4bdee69efccb6ded0fb230d78aafaf37af98377

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    TIKTOKEN_CACHE_DIR=/opt/tiktoken \
    PREFECT_HOME=/tmp/prefect \
    PREFECT_SERVER_ANALYTICS_ENABLED=false \
    DO_NOT_TRACK=1 \
    PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir uv==0.11.32

WORKDIR /pipeline
COPY pyproject.toml uv.lock ./
# Dev tools (pytest, ruff) are included so tests can run in this container.
# The connection can drop, so: system certificates, few parallel downloads, a download cache that
# survives between tries and builds, and up to 5 tries.
ENV UV_SYSTEM_CERTS=1 UV_CONCURRENT_DOWNLOADS=2 UV_HTTP_TIMEOUT=180 UV_HTTP_RETRIES=8
RUN --mount=type=cache,target=/root/.cache/uv \
    for i in 1 2 3 4 5; do uv sync --frozen --no-install-project && break; \
    [ "$i" = 5 ] && exit 1; sleep 10; done

# Download the models once at build time (about 300 MB), so runs work offline afterwards:
# the token vocabulary, the dense and sparse embedding models, and the bge tokenizer.
ENV FASTEMBED_CACHE_PATH=/opt/fastembed \
    HF_HOME=/opt/hf
# Each download is its own step with up to 3 tries, because the connection can drop.
RUN for i in 1 2 3; do python -c "import tiktoken; tiktoken.get_encoding('o200k_base')" && break; \
    [ "$i" = 3 ] && exit 1; sleep 5; done
RUN for i in 1 2 3; do python -c "from fastembed import SparseTextEmbedding, TextEmbedding; \
TextEmbedding('BAAI/bge-base-en-v1.5'); SparseTextEmbedding('Qdrant/bm25')" && break; \
    [ "$i" = 3 ] && exit 1; sleep 5; done
RUN for i in 1 2 3; do python -c "from tokenizers import Tokenizer; \
Tokenizer.from_pretrained('BAAI/bge-base-en-v1.5')" && break; \
    [ "$i" = 3 ] && exit 1; sleep 5; done
ENV HF_HUB_OFFLINE=1

COPY graphlens_pipeline ./graphlens_pipeline
COPY tests ./tests

# Run as a normal user, not root.
RUN useradd --create-home --uid 10001 graphlens \
 && chmod -R a+rX /opt/tiktoken /opt/fastembed /opt/hf
USER graphlens

ENTRYPOINT ["python", "-m", "graphlens_pipeline"]
