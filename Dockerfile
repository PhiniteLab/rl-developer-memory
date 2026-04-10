FROM python:3.12-slim AS base

LABEL maintainer="PhiniteLab"
LABEL description="rl-developer-memory MCP server"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml MANIFEST.in ./
COPY src/ src/

RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir .

# Runtime data directories — mount or set via env
ENV RL_DEVELOPER_MEMORY_HOME=/data \
    RL_DEVELOPER_MEMORY_DB_PATH=/data/rl_developer_memory.sqlite3 \
    RL_DEVELOPER_MEMORY_STATE_DIR=/data/state \
    RL_DEVELOPER_MEMORY_BACKUP_DIR=/data/backups \
    RL_DEVELOPER_MEMORY_LOG_DIR=/data/state/log \
    RL_DEVELOPER_MEMORY_SERVER_LOCK_DIR=/data/state/run

VOLUME ["/data"]

ENTRYPOINT ["python", "-m", "rl_developer_memory.server"]

# --- Dev stage ---
FROM base AS dev

COPY requirements.txt ./
RUN pip install --no-cache-dir -e ".[dev]"

COPY tests/ tests/
COPY scripts/ scripts/
COPY configs/ configs/

CMD ["python", "-m", "pytest", "tests/"]
