# Backend Delivery Plan

## Phase 0 – Environment Ready
- Confirm Python 3.11+ and PostgreSQL are installed locally or accessible via Docker.
- Initialize virtualenv (`python -m venv venv`) and install base dependencies from `requirements.txt` once defined.
- Create `.env` with placeholder values for `DATABASE_URL`, `SECRET_KEY`, and token settings.

## Phase 1 – Persistence Layer
- Translate `docs/db_schema.md` into SQLAlchemy models (`app/models/`) and Base metadata.
- Configure `app/db/session.py` factory and ensure Alembic references `target_metadata`.
- Generate initial migration (`alembic revision --autogenerate`) and apply against local database.

## Phase 2 – Domain Schemas & Utilities
- Build Pydantic v2 schemas in `app/schemas/` aligned with `docs/openapi_spec.md`.
- Implement security helpers (hashing, JWT issue/verify) under `app/core/security.py`.
- Add shared dependencies in `app/deps.py` (DB session, `get_current_user`).

## Phase 3 – API Routers
- Scaffold routers (`app/routers/`) for auth, users, workspaces, projects, tasks, comments.
- Implement endpoints per OpenAPI contract: CRUD, filtering, pagination, ownership checks.
- Wire routers into `app/main.py` and ensure tags/paths match the spec.

## Phase 4 – Quality Gates
- Author pytest suite in `tests/` exercising happy paths, permission boundaries, and error responses.
- Add tooling scripts or Make targets for `pytest`, `ruff check`, `ruff format`, and migrations.
- Target ≥80% coverage; configure CI pipeline (GitHub Actions) to run lint and tests.

## Phase 5 – Operations & Launch
- Document local and Docker-based runbooks in README and `docs/docker_compose_setup.md`.
- Provide sample data fixtures or seeding scripts for demos.
- Prepare production checklist: environment variables, migrations, monitoring hooks, backup policy.
