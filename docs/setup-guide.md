# Setup Guide

> **This file is read by the automated evaluation pipeline. Be precise and complete.**

## Prerequisites

Before you begin, ensure you have the following installed:

- [ ] Python 3.11+ (developed and tested on 3.12)
- [ ] [Bun](https://bun.sh) (frontend package manager and dev server)
- [ ] Docker Desktop (for PostgreSQL)
- [ ] An IBM Bob account with an **Inference-scoped** API key (`bob.ibm.com` -> API Keys). Optional - the app runs fully without one, using its deterministic fallback parser (see [Known limitation: Bob connectivity](#known-limitation-bob-connectivity) below).

## Environment Variables

Copy `src/.env.example` to `src/.env` and fill in the values:

```bash
cp src/.env.example src/.env
```

| Variable | Description | Required |
|---|---|---|
| `BOB_API_KEY` | Your IBM Bob Inference-scoped API key | No - falls back to the deterministic parser if absent/unreachable |
| `BOB_API_BASE_URL` | Base URL for Bob's inference API | No - defaults to `https://api.us-east.bob.ibm.com` |
| `BOB_MODEL` | Model id to use for extraction | No - auto-discovered from Bob's `/inference/v1/model/info` if blank |
| `DATABASE_URL` | PostgreSQL connection string | Yes - defaults to the docker-compose service on port 5544 |
| `APP_PORT` | Backend port | No - defaults to `8010` |
| `CORS_ORIGINS` | Allowed frontend origin(s) | No - defaults to `http://localhost:5199` |
| `MO_EMBEDDING_MODEL` | sentence-transformers model for MO similarity | No - defaults to `all-MiniLM-L6-v2` |
| `MO_SIMILARITY_THRESHOLD` | Cosine similarity cutoff for an inter-district MO edge | No - defaults to `0.90` |
| `ENTITY_FUZZY_THRESHOLD` | RapidFuzz token-sort-ratio cutoff for a name match | No - defaults to `82` |

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/samSRaina/bob-ai-hackathon-cyber-elevate.git
cd bob-ai-hackathon-cyber-elevate

# 2. Backend: create a venv and install dependencies
cd src/backend
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt      # Windows
# source .venv/bin/activate && pip install -r requirements.txt   # macOS/Linux

# 3. Frontend: install dependencies
cd ../frontend
bun install
```

## Running the Application

```bash
# 1. Start PostgreSQL (from the repo root)
docker compose up -d postgres

# 2. Start the backend (from src/backend, with the venv active)
uvicorn app.main:app --reload --port 8010

# 3. Seed the database with 100 sample FIRs and run detection
#    (from src/backend, in a separate terminal)
python -m app.seed

# 4. Start the frontend (from src/frontend, in a separate terminal)
bun run dev
```

The dashboard will be available at: `http://localhost:5199`
The backend's interactive API docs are at: `http://localhost:8010/docs`

Alternatively, from the repo root, `npm install && npm run dev` runs all three
(Postgres, backend, frontend) concurrently in one terminal, once the backend venv
and frontend dependencies from step 2/3 above have already been installed once.

## Quick Demo

1. Follow **Running the Application** above, including `python -m app.seed`.
2. Open `http://localhost:5199`. With the default **State DGP** role, the
   dashboard summary should show **100 total FIRs**, **19 repeat-offender
   clusters**, and **1 flagged syndicate**.
3. In the **Flagged Repeat Offenders** table, the top row (confidence **0.97**,
   marked `SYNDICATE`) is the seeded Jamtara-style cyber-fraud crew - six FIRs
   across three districts (Lucknow, Gautam Buddh Nagar, Gorakhpur), linked by a
   shared phone number, a shared vehicle, transliteration-variant names, and a
   reused fraud script - exactly the pattern this project is built to surface.
4. Switch the **Role** dropdown to **Station Officer**, pick a station (e.g.
   Hazratganj) - the dashboard immediately re-scopes to that station's ~14 FIRs
   only. This is the RBAC demonstration: the same UI, the same syndicate cluster
   (since it touches this station), but every unrelated FIR disappears.
5. Scroll to the **Criminal Syndicate Graph** and click any red (suspect) or
   purple (syndicate hub) node - a dossier panel slides in from the right with
   that suspect's full identifier and cluster history.

## Known limitation: Bob connectivity

This prototype was built and demoed without a confirmed, documented base URL for
IBM Bob's inference REST API - IBM Bob's own docs describe API-key-based
programmatic access (`bob.ibm.com/docs/ide/account/api-keys`) but do not publish a
REST reference for the inference endpoint at the time of writing. `engine/bob_client.py`
implements the integration against the most plausible endpoint shape
(`{BOB_API_BASE_URL}/inference/v1/chat/completions`, OpenAI-compatible, Bearer
auth) and is fully wired into the extraction path as the **primary** source of
truth for every ingested FIR. In this environment that endpoint currently returns
`403` (a Cloudflare edge challenge, not an application-level error), so every FIR
in the seed dataset was extracted via the deterministic fallback parser instead -
visible per-FIR as `extraction_source: "fallback_parser"` in `/ingest` responses
and the `FIRRecord.extraction_source` column. The moment a working
`BOB_API_BASE_URL` is confirmed, ingestion will use Bob automatically with zero
code changes - the fallback logs a clear warning per call at
`bob_engine.services: Bob extraction failed, falling back to deterministic
parser: ...` so this is easy to verify.

## Troubleshooting

| Issue | Solution |
|---|---|
| `ModuleNotFoundError` on backend start | Re-run `pip install -r requirements.txt` inside the activated `.venv` |
| `psycopg.OperationalError: connection refused` | Postgres isn't running - `docker compose up -d postgres`, then wait a few seconds for its healthcheck |
| Port `5544`, `8010`, or `5199` already in use | Another process is bound to it - stop it, or change the port in `docker-compose.yml` / `.env` / `vite.config.ts` (keep `CORS_ORIGINS` in sync with the frontend port) |
| Frontend loads but every panel shows a fetch error | Backend isn't running, or `CORS_ORIGINS` in `src/.env` doesn't match the frontend's actual origin |
| Dashboard shows 0 FIRs | The database hasn't been seeded yet - run `python -m app.seed` from `src/backend` |
| `X-User-Station header is required` (400) | You selected Station Officer / District SP but no station has loaded yet in the Role Switcher - wait a moment for `/stations/all` to populate, or reselect the role |
| Bob extraction always falls back | Expected in this environment - see [Known limitation: Bob connectivity](#known-limitation-bob-connectivity) above |
