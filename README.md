# ai-newsletter-api (backend MVP)

FastAPI backend for an LLM-driven tech newsletter app.

- keep business logic out of routes
- treat LLM calls as _stateless, schema-validated functions_
- persist content history so newsletters don’t repeat

## Architecture (high level)

Flutter client talks only to this API.

- **`app/api/`**: HTTP layer (FastAPI routers). Thin: validation + auth later + calls services.
- **`app/services/`**: business logic (interest parsing/apply, newsletter generation pipeline).
- **`app/llm/`**: LLM client abstraction + prompts + output schemas (mockable for tests).
- **`app/db/`**: SQLAlchemy models + session management.
- **`alembic/`**: migrations (DB schema is migration-first).
- **`tests/`**: API + service tests + (later) prompt regression tests.

## Tech Stack

- **FastAPI**: fast iteration, great Pydantic integration, async-first.
- **Pydantic v2 + pydantic-settings**: strict schemas + structured config from env (guardrails for LLM outputs later too).
- **SQLAlchemy 2 (async) + asyncpg**: production-grade Postgres support with modern typed ORM.
- **Alembic**: migrations are the source of truth for schema (required once you add pgvector columns/indexes).
- **pgvector (library) + Postgres pgvector extension**: enables embedding similarity for deduplication without introducing a separate vector DB in the MVP.
- **pytest + httpx**: fast API tests
- **ruff + mypy (optional)**: quick linting + type checks to keep the codebase maintainable.

## Local setup

### 1) Create environment variables

This workspace blocks committing dotfiles like `.env.example`, so use `env.example`:

```zsh
cp env.example .env
```

Your `.env` contains both **app settings** and **Postgres credentials** for Docker Compose.

### 2) Install Python dependencies

Use any workflow you like. With `pip`:

```zsh
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev]"
```

### 3) Start DB in Docker

```zsh
docker compose up -d db
```

### 4) Run API locally (debugging)

```zsh
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5) Start both DB and API in Docker

```zsh
docker compose --profile api up -d --build
```

### 6) Stop DB (and API if it's running in docker)

```zsh
docker compose --profile api down
```

### 7) Run tests

```zsh
pytest
```
