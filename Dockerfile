FROM python:3.13-slim AS runtime
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 STATIC_DIRECTORY=/app/static
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt
RUN useradd --create-home --uid 10001 wecode
COPY backend/ /app/backend/
COPY recovered-publication/ /app/static/
COPY scripts/prepare_runtimes.py scripts/runtime-manifest.json /app/scripts/
RUN python /app/scripts/prepare_runtimes.py /app/static/runtimes
COPY scripts/prepare_frontend.py /app/scripts/prepare_frontend.py
RUN python /app/scripts/prepare_frontend.py /app/static
USER wecode
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=5 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/health', timeout=3)" || exit 1
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1", "--no-proxy-headers"]
