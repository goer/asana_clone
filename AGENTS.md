# Repository Guidelines

## Project Structure & Module Organization
Use `docs/` as the source of truth for architectural plans (`coding_tasks.md`, `db_schema.md`, `openapi_spec.md`). Place FastAPI application code under `app/` with subpackages `core/`, `db/`, `models/`, `schemas/`, and `routers/`; keep Alembic migrations in `alembic/`. Tests belong in `tests/` mirroring the `app/` layout. Configuration files such as `.env`, `alembic.ini`, and `requirements.txt` should live at the repository root.

## Build, Test, and Development Commands
Create an isolated environment before installing dependencies:
```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```
Launch the API locally with `uvicorn app.main:app --reload`. Run database migrations via `alembic upgrade head`. Execute the test suite with `pytest` and reformat code with `ruff format` followed by linting with `ruff check` (add both to `requirements-dev.txt`).

## Coding Style & Naming Conventions
Follow Python 3.11+ typing standards and Pydantic v2 models (`ConfigDict(from_attributes=True)`). Use 4-space indentation, descriptive snake_case for modules and functions, PascalCase for classes, and ALL_CAPS for constants. Keep routers focused on request handling—push data access into service helpers when logic grows. Document nontrivial functions with docstrings and add focused inline comments sparingly.

## Testing Guidelines
Write pytest cases under `tests/` with filenames ending in `_test.py` and functions starting with `test_`. Cover authentication, permission edges, and query filtering. When feasible, use a transactional test database seeded through Alembic fixtures. Aim for ≥80% line coverage; run `pytest --cov=app` before opening a PR.

## Commit & Pull Request Guidelines
Match existing history: concise, Title-Case commit subjects under 60 chars (e.g., `Add User Router Skeleton`). Include body details only when context is complex. Each PR should describe the change, list testing evidence, link relevant issues, and note schema or API contract updates. Request review once CI passes and migrations, if added, are documented in the PR summary.

## Security & Configuration Tips
Store secrets only in `.env` and never commit them. Regenerate JWT `SECRET_KEY` when rotating environments. Verify database URLs point to non-production instances during local development. Review `docs/docker_compose_setup.md` before exposing services publicly.
