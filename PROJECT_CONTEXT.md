# Project Context

Quick reference for understanding this codebase and onboarding new contributors or AI agents.

## Purpose

This API powers a tech newsletter app where users manage their interests via natural language prompts, and the system generates personalized weekly newsletters with up-to-date content that never repeats. The backend uses LLMs to extract interests, research current topics, and deduplicate content using vector embeddings.

## Architecture & Tech Stack

### High-Level Architecture

```
Flutter App → FastAPI Backend → LLM + Search APIs + PostgreSQL (with pgvector)
```

**Key principle**: LLMs are never called directly from the client. All AI operations happen server-side.

### Directory Structure

- **`app/api/`**: FastAPI routers (HTTP layer). Thin: validation + auth (later) + calls services.
- **`app/services/`**: Business logic (interest parsing/apply, newsletter generation pipeline).
- **`app/llm/`**: LLM client abstraction + prompts + output schemas (mockable for tests).
- **`app/db/`**: SQLAlchemy models + async session management.
- **`app/core/`**: Configuration, logging, lifespan (startup/shutdown).
- **`alembic/`**: Database migrations (schema is migration-first).
- **`tests/`**: API + service tests + (later) prompt regression tests.

### Tech Stack Choices & Rationale

| Technology                          | Why                                                                                        |
| ----------------------------------- | ------------------------------------------------------------------------------------------ |
| **FastAPI**                         | Fast iteration, excellent Pydantic integration, async-first, auto-generated OpenAPI docs   |
| **Pydantic v2 + pydantic-settings** | Strict schema validation (reused for LLM output guardrails), structured config from `.env` |
| **SQLAlchemy 2 (async) + asyncpg**  | Production-grade Postgres with modern typed ORM, async support                             |
| **Alembic**                         | Migration-first approach (required for pgvector columns/indexes), schema as code           |
| **pgvector (extension + library)**  | Embedding similarity for deduplication without separate vector DB in MVP                   |
| **PostgreSQL**                      | Relational DB + vector capabilities via pgvector extension (single database)               |
| **pytest + httpx**                  | Fast API tests, async test support                                                         |
| **ruff + black + mypy**             | Fast linting, consistent formatting, optional type checking                                |

### Design Principles

1. **Business logic stays out of routes** - Routes are thin, services handle logic
2. **LLM calls are stateless** - All context passed explicitly, no implicit "memory"
3. **Schema-validated LLM outputs** - Use Pydantic models to enforce structure
4. **Multiple narrow prompts** - Not one giant prompt (testable, debuggable)
5. **Content history is persistent** - Enables deduplication across newsletter issues
6. **Migration-first schema** - Alembic migrations are source of truth

## Functional Requirements

### MVP Scope (Planned Roadmap)

**Planned MVP features (not yet fully implemented):**

- ⏳ Interest extraction & updates via natural language prompts
- ⏳ Explicit interest management (view/delete directly)
- ⏳ Manual newsletter generation for now (through API endpoint)
- ⏳ Newsletter persistence & retrieval
- ⏳ Basic content deduplication (URLs + embedding similarity)
- ⏳ Prompt regression tests

**Deferred (Future):**

- ⏳ Scheduling/cron for automated newsletters
- ⏳ Email/SMS sharing
- ⏳ Image generation in newsletters
- ⏳ Advanced preference settings

### Core User Flows

1. **Interest Management**

   - User provides natural language prompt (e.g., "I'm interested in Python async patterns and React hooks")
   - LLM extracts structured interests: `{add_interests: [...], remove_interests: [...]}`
   - System upserts interests, marks removed ones inactive (soft delete)
   - User can also view/delete interests explicitly via API

2. **Newsletter Generation**

   - Expand interests into subtopics (LLM, cheap call)
   - Research via search APIs (Tavily/SerpAPI - non-LLM)
   - Deduplicate: no repeated URLs, embedding similarity vs past content
   - Summarize articles (LLM, structured output)
   - Persist newsletter + content items + embeddings

3. **Content Deduplication**
   - URL-based: no repeated source URLs
   - Embedding-based: cosine similarity vs historical content items
   - Prevents repeating content across newsletter issues

### Guardrails

- Schema-validated LLM outputs (Pydantic models)
- Interest whitelist (prevent off-topic interests)
- Mandatory source URLs (all content must have sources)
- Token + item caps (prevent runaway generation)
- Validation layer before persistence

## Current Settings Implementation

**Location**: `app/core/config.py`

Settings use **Pydantic Settings** with `.env` file support:

```python
class Settings(BaseSettings):
    app_name: str = "ai-newsletter-api"
    environment: str = "local"  # "local" | "test" | "production"
    log_level: str = "INFO"
    database_url: PostgresDsn = "postgresql+asyncpg://..."
```

**Key points:**

- Settings are instantiated at module import time (`settings = Settings()`)
- `.env` file is automatically loaded (via `env_file=".env"`)
- Environment variables override defaults
- In tests, use `monkeypatch.setattr(config.settings, "environment", "test")` (not `setenv()`)

**Environment variables** (see `env.example`):

- `APP_NAME`, `ENVIRONMENT`, `LOG_LEVEL`
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_DB`
- `DATABASE_URL` (for local runs)
- `API_PORT` (for Docker Compose)

## Test Suite

**Location**: `tests/`

### Testing Patterns

- **Use `monkeypatch.setattr()`** on settings objects (not `setenv()`) because settings are instantiated at import time
- **Mock at module level**: Patch `"app.core.lifespan.engine"` not `engine.connect` (read-only attributes)
- **Async tests**: Use `@pytest.mark.asyncio` and `pytest-asyncio` (auto mode enabled)
- **Test environment**: Set `settings.environment = "test"` to skip database connection checks

### Future Test Plans

- Prompt regression tests (fixed inputs → validated outputs)
- API endpoint tests
- Property tests (no missing sources, no repeated URLs)
- Mock LLMs for CI

## How to Build & Run

See **`README.md`** for detailed setup instructions. Quick reference:

1. **Environment**: `cp env.example .env`
2. **Dependencies**: `pip install -e ".[dev]"`
3. **Database**: `docker compose up -d db`
4. **Migrations**: `alembic upgrade head`
5. **Run locally**: `uvicorn app.main:app --reload`
6. **Run in Docker**: `docker compose --profile api up -d --build`
7. **Tests**: `pytest`

## Key Files to Understand

- **`app/main.py`**: FastAPI app factory, version from package metadata, lifespan integration
- **`app/core/lifespan.py`**: Startup/shutdown (DB health check, engine disposal)
- **`app/db/session.py`**: Async SQLAlchemy engine + session management
- **`alembic/env.py`**: Alembic configuration (async, reads from settings)
- **`docker-compose.yml`**: Postgres (pgvector) + API service (profile-based)

## Development Workflows

- **Local API + Docker DB**: `docker compose up -d db` then `uvicorn app.main:app --reload`
- **Full Docker stack**: `docker compose --profile api up -d --build`
- **Migrations**: Modify models → `alembic revision --autogenerate -m "msg"` → `alembic upgrade head`
