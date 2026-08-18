# Libra Galaxy — FastAPI backend
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY apps/api/pyproject.toml ./pyproject.toml
RUN pip install --upgrade pip && pip install ".[dev]"

COPY apps/api ./

# Never run as root in a container that handles banking traffic.
RUN useradd --create-home --uid 10001 libra && chown -R libra:libra /app
USER libra

EXPOSE 8000
CMD ["python", "-m", "libra.main", "serve", "--host", "0.0.0.0", "--port", "8000"]
