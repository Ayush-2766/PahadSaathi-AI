# PahadSaathi AI — Phase 3

PahadSaathi AI is an offline-conscious disaster incident intelligence and response coordination project for Uttarakhand. This repository currently contains **only Phase 1 foundations**: a FastAPI health service, SQLite schema migrations, and a responsive React placeholder interface.

Phase 3 adds local, deterministic intelligence: explainable incident classification, severity recommendations that always require human verification, potential duplicate detection, and village-level impact aggregation. No external AI service, API key, or report mutation is used.

## Intelligence API

- `POST /api/v1/intelligence/analyze` accepts `description`, with optional `category`, `village_name`, `district`, and `submitted_at`; it returns classification, a non-confirmatory severity recommendation, and possible duplicate reports.
- `GET /api/v1/intelligence/villages` returns village incident, category, severity, and potential-duplicate aggregates.

## Prerequisites

- Python 3.11 or newer
- Node.js 20 or newer and npm

## Backend setup

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp backend/.env.example backend/.env
cd backend
alembic upgrade head
uvicorn app.main:app --reload
```

The API starts at `http://localhost:8000`. Confirm it with:

```bash
curl http://localhost:8000/api/v1/health
```

Expected response:

```json
{"status":"ok","database":"ok"}
```

To run backend tests (from the repository root, with the virtual environment active):

```bash
PYTHONPATH=backend pytest backend/tests -q
```

Configuration uses environment variables. Copy `backend/.env.example` to `backend/.env` for reference, then export variables in your shell or use your preferred environment loader. The default SQLite database is created as `backend/pahadsaathi.db` when migrations run from `backend/`.

## Frontend setup

In a second terminal, from the repository root:

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Vite prints the local URL, normally `http://localhost:5173`. `VITE_API_BASE_URL` controls the backend base URL and defaults to `http://localhost:8000/api/v1`.

## Project layout

- `backend/app`: API, configuration, database, and model modules
- `backend/alembic`: database migration configuration and revisions
- `backend/tests`: backend test suite
- `frontend/src`: React shell, placeholder pages, styles, and API client configuration
- `docs`: future documentation
- `scripts`: future development helpers

