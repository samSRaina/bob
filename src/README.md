# Source Code

```
src/
  backend/    FastAPI service (SQLModel + PostgreSQL). Entity resolution, MO
              similarity, graph building, RBAC, and the Bob extraction client
              all live under backend/app/. See backend/app/main.py for the
              app entrypoint.
  frontend/   React 19 + TypeScript (Vite, Bun), styled with Tailwind CSS.
              Dashboard stats, the flagged repeat-offender list, and the
              interactive syndicate graph, with a light/dark theme toggle.
  openapi.json  Generated API contract (backend/export_openapi.py) - the
              frontend's typed client (frontend/src/api/schema.d.ts) is
              generated from this file via `bunx openapi-typescript`.
  .env.example  Every environment variable the backend reads, with dummy
              values. Copy to .env and fill in real values - .env is
              git-ignored.
```

See [`../docs/setup-guide.md`](../docs/setup-guide.md) for exact install/run
commands and [`../docs/architecture.md`](../docs/architecture.md) for how the
pieces fit together.
