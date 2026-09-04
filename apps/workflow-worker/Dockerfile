# RevPilot AI — Temporal Workflow Worker Container Definition
# Conforms to docs/30-deployment/DEPLOYMENT-ARCHITECTURE.md §6 and AC-DEP-01

FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY packages/ ./packages/

RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir .

FROM python:3.12-slim AS runner

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 --shell /bin/bash appuser

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY packages/ ./packages/
COPY apps/workflow-worker/ ./apps/workflow-worker/

ENV PYTHONPATH="/app/packages/backend/src:/app" \
    PYTHONUNBUFFERED="1" \
    PYTHONDONTWRITEBYTECODE="1"

USER appuser

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python3 -c "import sys; sys.exit(0)" || exit 1

CMD ["python3", "-m", "apps.workflow-worker.main"]
