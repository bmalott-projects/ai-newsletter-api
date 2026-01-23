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
- **`app/services/`**: Domain-specific business logic (user operations, interest extraction, newsletter generation). Contains business rules and orchestrates multiple components (DB, LLM, etc.).
- **`app/llm/`**: LLM client abstraction + prompts + output schemas (mockable for tests).
- **`app/db/`**: SQLAlchemy models + async session management.
- **`app/core/`**: Infrastructure and cross-cutting utilities (configuration, logging, lifespan, password hashing, JWT token creation). Low-level utilities with NO business rules.
- **`alembic/`**: Database migrations (schema is migration-first).
- **`tests/`**: Test suite organized by type:
  - **`tests/integration/`**: Integration tests (full HTTP + database flows)
  - **`tests/unit/`**: Unit tests (mocked dependencies, isolated functions)
  - **`tests/conftest.py`**: Shared fixtures

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
| **ruff (lint+format) + mypy**       | Fast linting, consistent formatting, **strict type checking** (type hints required)        |

### Design Principles

1. **Business logic stays out of routes** - Routes are thin, services handle logic
2. **Separation of infrastructure and business logic** - Core layer provides utilities, services layer contains domain business rules
3. **LLM calls are stateless** - All context passed explicitly, no implicit "memory"
4. **Schema-validated LLM outputs** - Use Pydantic models to enforce structure
5. **Multiple narrow prompts** - Not one giant prompt (testable, debuggable)
6. **Content history is persistent** - Enables deduplication across newsletter issues
7. **Migration-first schema** - Alembic migrations are source of truth

### Core vs Services Layer

**Core Layer (`app/core/`)** - Infrastructure & Cross-Cutting Utilities:
- **Purpose**: Low-level utilities used across the entire application
- **Characteristics**: No business rules, domain-agnostic, infrastructure concerns
- **Examples**: Password hashing (`get_password_hash()`), JWT token creation (`create_access_token()`), configuration, logging
- **Think of it as**: Tools in a toolbox - reusable utilities

**Services Layer (`app/services/`)** - Domain Business Logic:
- **Purpose**: Domain-specific business logic that orchestrates multiple components
- **Characteristics**: Contains business rules, domain-specific, coordinates core utilities + DB + LLM
- **Examples**: User registration (`register_user()`), authentication (`authenticate_user()`), interest extraction
- **Think of it as**: Building something - uses tools to accomplish tasks with business rules

**Relationship**: Services use Core utilities. For example, `register_user()` (service) calls `get_password_hash()` (core) to hash passwords before storing them.

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
- **Required fields validated on startup**
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
├── conftest.py                    # Shared fixtures (auto-discovered by all tests)
├── integration/                   # Integration tests
└── unit/                          # Unit tests
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
- **`app/core/config.py`**: Settings with validation (exits on missing required fields)
- **`app/db/session.py`**: Async SQLAlchemy engine + session management
- **`app/services/auth.py`**: User authentication business logic (register, login, delete)
- **`app/api/auth.py`**: Thin HTTP layer for authentication endpoints
- **`alembic/env.py`**: Alembic configuration (async, reads from settings)
- **`docker-compose.yml`**: Postgres (pgvector) + API service (profile-based)
- **`tests/conftest.py`**: Shared pytest fixtures (auto-discovered by all tests)

## Development Workflows

- **Local API + Docker DB**: `docker compose up -d db` then `uvicorn app.main:app --reload`
- **Full Docker stack**: `docker compose --profile api up -d --build`
- **Migrations**: Modify models → `alembic revision --autogenerate -m "msg"` → `alembic upgrade head`
- **Run tests**: `pytest` (all tests) or `pytest tests/integration/` (integration only)

## Code Quality & Standards

### Type Hints

- **Required on all functions** (enforced by mypy: `disallow_untyped_defs = true`)
- Use `from __future__ import annotations` in all Python files (allows forward references)
- Tests are exempt from type hint requirements
- Exception: `self` and `cls` parameters don't need type hints

### Linting Rules

- **Ruff**: Linting and formatting (enforces PEP 8, type hints (ANN rules), code quality (B, PIE, SIM rules))
- **MyPy**: Strict type checking with `disallow_untyped_defs = true`
- **Ignored rules**: `B008` (FastAPI `Depends()` in argument defaults is intentional)

### SQLAlchemy Async Patterns

- **Use Core-style statements** for async operations: `select()`, `delete()`, `insert()`, `update()`
- **Pattern**: `await db.execute(select(User).where(...))` or `await db.execute(delete(User).where(...))`
- **Avoid**: `db.delete(obj)` or `db.query()` (old SQLAlchemy 1.x patterns, unreliable in async)

### Editor Configuration

- **Settings**: Configured in `.vscode/settings.json` for automatic formatting and linting
