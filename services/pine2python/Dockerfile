FROM node:24.15.0-bookworm-slim AS node_deps
WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci --omit=dev --ignore-scripts --no-audit --no-fund

FROM python:3.12.7-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    P2P_HOST=0.0.0.0 \
    P2P_PORT=8080 \
    P2P_ARTIFACT_ROOT=/var/lib/pine2python/artifacts \
    P2P_WORK_ROOT=/var/lib/pine2python/work \
    P2P_WORKER_PATH=/app/runtime/worker.mjs
COPY --from=node_deps /usr/local/bin/node /usr/local/bin/node
WORKDIR /app
COPY requirements-lock.txt ./
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates libstdc++6 \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --no-cache-dir -r requirements-lock.txt
COPY pyproject.toml LICENSE NOTICE.md README.md ./
COPY third_party ./third_party
COPY src ./src
COPY runtime ./runtime
COPY --from=node_deps /build/node_modules ./node_modules
RUN python -m pip install --no-cache-dir --no-deps . \
    && addgroup --system pine2python \
    && adduser --system --ingroup pine2python --home /nonexistent pine2python \
    && mkdir -p /var/lib/pine2python/artifacts /var/lib/pine2python/work \
    && chown -R pine2python:pine2python /var/lib/pine2python
USER pine2python
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health/ready', timeout=2)"
CMD ["uvicorn", "pine2python.api:app", "--host", "0.0.0.0", "--port", "8080"]
