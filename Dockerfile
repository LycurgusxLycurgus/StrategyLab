FROM python:3.12.7-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_HOST=0.0.0.0 \
    APP_PORT=8000
WORKDIR /app
COPY services/pine2python ./services/pine2python
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY agents ./agents
COPY strategies ./strategies
COPY pre-strategies ./pre-strategies
COPY README.md ./
RUN addgroup --system strategylab \
    && adduser --system --ingroup strategylab --home /nonexistent strategylab \
    && mkdir -p /app/artifacts \
    && chown -R strategylab:strategylab /app/artifacts
USER strategylab
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=2)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
