# ai-newsletter-api (backend MVP)

FastAPI backend for an LLM-driven tech newsletter app. This repo is intentionally scaffolded for a **testable MVP**:
- keep business logic out of routes
- treat LLM calls as *stateless, schema-validated functions*
- persist content history so newsletters don’t repeat

## Architecture (high level)

Flutter client talks only to this API.

- **`app/api/`**: HTTP layer (FastAPI routers). Thin: validation + auth later + calls services.
- **`app/services/`**: business logic (interest parsing/apply, newsletter generation pipeline).
- **`app/llm/`**: LLM client abstraction + prompts + output schemas (mockable for tests).
- **`app/db/`**: SQLAlchemy models + session management.
- **`alembic/`**: migrations (DB schema is migration-first).
- **`tests/`**: API + service tests + (later) prompt regression tests.

## Dependency decisions (why these)

- **FastAPI**: fast iteration, great Pydantic integration, async-first.
- **Pydantic v2 + pydantic-settings**: strict schemas + structured config from env (guardrails for LLM outputs later too).
- **SQLAlchemy 2 (async) + asyncpg**: production-grade Postgres support with modern typed ORM.
- **Alembic**: migrations are the source of truth for schema (required once you add pgvector columns/indexes).
- **pgvector (library) + Postgres pgvector extension**: enables embedding similarity for deduplication without introducing a separate vector DB in the MVP.
- **pytest + httpx**: fast API tests; later you’ll add mocked LLM/search tests and regression fixtures.
- **ruff + mypy (optional)**: quick linting + type checks to keep the codebase maintainable.

## Local setup

### 1) Create environment variables

This workspace blocks committing dotfiles like `.env.example`, so use `env.example`:

```bash
cp env.example .env
```

### 2) Start Postgres (with pgvector)

```bash
docker compose up -d
```

### 3) Install Python dependencies

Use any workflow you like. With `pip`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev]"
```

### 4) Run the API

```bash
uvicorn app.main:app --reload
```

### Alternative: run API + DB via Docker Compose

```bash
docker compose up -d --build
```

Health check:
- `GET /api/health`

### 5) Run tests

```bash
pytest
```

## Next steps (MVP build order)

- Interest extraction endpoint (`POST /api/interests/parse`) returning `{add_interests, remove_interests}`
- Persist interests and allow explicit list/delete
- Manual newsletter generation endpoint
- Research service (search API)
- Deduplication (URLs + embeddings vs history)
- Prompt regression tests (fixed inputs → schema-validated outputs)

