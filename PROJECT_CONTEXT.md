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

- **`app/api/`**: FastAPI routers (HTTP layer). Thin: validation + JWT auth + calls services.
- **`app/services/`**: Business logic (interest parsing/apply, newsletter generation pipeline).
- **`app/llm/`**: LLM client abstraction + prompts + output schemas (mockable for tests).
- **`app/db/`**: SQLAlchemy models + async session management.
- **`app/core/`**: Configuration, logging, lifespan (startup/shutdown), and JWT authentication utilities.
- **`alembic/`**: Database migrations (schema is migration-first).
- **`tests/`**: API + service tests + (later) prompt regression tests.

### Tech Stack Choices & Rationale

| Technology                          | Why                                                                                        |
| ----------------------------------- | ------------------------------------------------------------------------------------------ |
| **FastAPI**                         | Fast iteration, excellent Pydantic integration, async-first, auto-generated OpenAPI docs   |
| **Pydantic v2 + pydantic-settings** | Strict schema validation (reused for LLM output guardrails), structured config from `.env` |
| **JWT authentication**              | python-jose for JWT tokens, passlib for password hashing (stateless, scalable auth)        |
| **OpenAI SDK**                      | LLM client for interest extraction and newsletter generation                               |
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

### MVP Scope (Current)

**Included:**

- ✅ Interest extraction & updates via natural language prompts
- ✅ JWT authentication (user registration, login, protected routes)
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
- `OPENAI_API_KEY` (OpenAI API key for LLM operations)
- `JWT_SECRET_KEY` (Secret key for signing JWT tokens)

## Test Suite

**Location**: `tests/`

### Testing Strategy

The project follows a layered testing approach, testing each layer appropriately:

| Layer | Test Type | Rationale |
|-------|-----------|-----------|
| **API Routes** (`app/api/`) | Integration tests (TestClient) | Test full HTTP flow, validation, authentication, and integration with services |
| **Services** (`app/services/`) | Unit tests (mocked dependencies) | Test business logic in isolation without external dependencies |
| **LLM Client** (`app/llm/`) | Unit tests (mocked OpenAI) | Test LLM integration and error handling without real API calls |
| **Core Utils** (`app/core/`) | Unit tests | Test pure functions (password hashing, JWT operations) |
| **Database Models** | Integration tests | Test relationships, constraints, and database operations |

### Testing Patterns

- **Use `monkeypatch.setattr()`** on settings objects (not `setenv()`) because settings are instantiated at import time
- **Mock at module level**: Patch `"app.core.lifespan.engine"` not `engine.connect` (read-only attributes)
- **Async tests**: Use `@pytest.mark.asyncio` and `pytest-asyncio` (auto mode enabled)
- **Test environment**: Set `settings.environment = "test"` to skip database connection checks
- **API tests**: Use `TestClient` from `fastapi.testclient` for integration testing of endpoints
- **Mock external services**: Always mock LLM clients, external APIs, and database in unit tests

### What to Test

**✅ Test (Integration Tests):**
- API endpoints - Full HTTP request/response cycle, validation, authentication
- Database operations - Model relationships, constraints, queries
- End-to-end flows - Complete user workflows through the API

**✅ Test (Unit Tests):**
- Service layer business logic - With mocked dependencies (LLM, DB)
- LLM client - Mock OpenAI responses, test error handling
- Core utilities - Password hashing, JWT operations, pure functions
- Input validation - Pydantic model validation

**❌ Don't Test:**
- Framework internals (FastAPI, SQLAlchemy core functionality)
- Third-party library code
- Simple pass-through functions without logic

### Test Structure

```
tests/
├── test_api_auth.py          # Integration: Full API endpoints (register, login, delete)
├── test_api_interests.py     # Integration: Full API endpoints (extract interests)
├── test_services_interest.py # Unit: Service layer with mocked LLM client
├── test_llm_client.py        # Unit: LLM client with mocked OpenAI API
├── test_core_auth.py         # Unit: Auth utilities (password hashing, JWT)
└── test_health.py            # Integration: Simple health check endpoint
```

### Key Principles

1. **Test behavior, not implementation** - Test that the API does what it should, not how it does it
2. **Fast unit tests** - Mock external dependencies to keep tests fast and isolated
3. **Integration tests for API** - Test the full stack to catch integration issues
4. **Mock expensive operations** - Never call real LLM APIs or external services in tests

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
- **`app/core/auth.py`**: JWT token creation/verification, password hashing utilities
- **`app/db/session.py`**: Async SQLAlchemy engine + session management
- **`alembic/env.py`**: Alembic configuration (async, reads from settings)
- **`docker-compose.yml`**: Postgres (pgvector) + API service (profile-based)

## Development Workflows

- **Local API + Docker DB**: `docker compose up -d db` then `uvicorn app.main:app --reload`
- **Full Docker stack**: `docker compose --profile api up -d --build`
- **Migrations**: Modify models → `alembic revision --autogenerate -m "msg"` → `alembic upgrade head`
