FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install build tooling (kept minimal); psycopg2 isn't used, but some deps may compile wheels.
RUN apt-get update \
  && apt-get install -y --no-install-recommends build-essential \
  && rm -rf /var/lib/apt/lists/*

# Install dependencies first for better layer caching
COPY pyproject.toml README.md /app/
RUN pip install -U pip && pip install .

# Copy application code
COPY app /app/app
COPY alembic /app/alembic
COPY alembic.ini /app/alembic.ini

# Create unprivileged user and adjust ownership
RUN groupadd -r appuser && useradd -r -g appuser appuser && chown -R appuser:appuser /app

EXPOSE 8000

# Run the application as the unprivileged user
USER appuser
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

