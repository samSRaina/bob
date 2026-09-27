# 🚀 Bob Engine — FIR Intelligence & Crime Pattern Detector

> **IBM Bob AI Hackathon × NFSU — Problem Statement #10 (Track 4: AI & Predictive)**

---

## 👥 Team

| Field | Value |
|---|---|
| **Team Name** | Cyber Elevate *(inferred from the repo name — confirm/edit)* |
| **Track** | AI |
| **Team Lead** | `[TODO: fill in — not fabricated]` |
| **Members** | `[TODO: fill in — not fabricated]` |

---

## 🎯 Problem Statement

UP Police's CCTNS holds 3+ crore digitized FIRs with no NLP layer — pattern
analysis across FIRs is entirely manual. Serial, inter-district offenders (the
real-world anchor: the Jamtara SIM-swap/UPI-fraud ring, 95,000+ FY2023 cases)
evade detection specifically because FIR-to-FIR links — a reused phone number, a
name spelled three ways, a fraud script repeated two districts over — are never
surfaced. See [`docs/problem-statement.md`](docs/problem-statement.md) for the
full brief.

---

## 💡 Solution

Bob Engine ingests digitized FIRs, uses **IBM Bob** to extract structured fields
from the raw text (with a deterministic fallback if Bob is unavailable), then
**deterministically** resolves suspects across name variants and shared
identifiers, clusters crimes by modus-operandi similarity, and flags cross-district
repeat offenders with an explainable confidence score — never a black-box number.
An RBAC-scoped dashboard (Station Officer / District SP / State DGP) shows station
statistics, the flagged offender list, and an interactive syndicate graph. See
[`docs/solution-overview.md`](docs/solution-overview.md).

---

## ✨ Key Features

- **Explainable repeat-offender detection** — every link between suspects carries
  a human-readable reason (exact phone/vehicle match, phonetic name match, or
  cross-station modus-operandi similarity), not just a score.
- **Transliteration-aware identity resolution** — "Mohd. Aslam" / "Mohammad
  Aslaam" / "M. Aslam" resolve to one canonical person via Double Metaphone +
  RapidFuzz, without any literal string overlap.
- **No-name suspects still link** — identifier- and description-only suspects
  (no name given in the FIR) are resolved by shared phone/vehicle/MO alone.
- **RBAC enforced server-side, not cosmetically** — every read (stats, offender
  list, graph, dossier) is scoped by a FastAPI dependency resolved against the
  database, before any query runs.
- **IBM Bob as the extraction copilot** — Bob turns a raw digitized FIR into
  structured JSON; every other engine (entity resolution, MO clustering, graph,
  RBAC) is deterministic by design, so the whole pipeline is auditable.
- **Interactive syndicate graph** — click any suspect node to open a full dossier
  with their cluster's confidence, districts involved, and match reasons.

---

## 🛠️ Tech Stack

| Category | Technologies |
|---|---|
| **Languages** | Python, TypeScript |
| **Frameworks** | FastAPI, SQLModel, React 19, Vite |
| **IBM Technologies** | IBM Bob (inference API — FIR extraction) |
| **Databases** | PostgreSQL 16 (Docker) |
| **Other** | RapidFuzz, Double Metaphone, sentence-transformers, NetworkX, Bun, Docker Compose |

---

## 📁 Repository Structure

```
├── src/                  # All source code (backend/, frontend/, openapi.json)
├── docs/                 # Written documentation
│   ├── problem-statement.md
│   ├── solution-overview.md
│   ├── architecture.md
│   └── setup-guide.md
├── demo/                 # Demo artifacts
│   ├── screenshots/      # App screenshots
│   └── demo-video-link.txt  # Link to demo video
├── presentation/         # Slide deck
├── docker-compose.yml    # PostgreSQL container
├── package.json          # Root orchestration (npm run dev)
└── submission.yaml       # Structured submission metadata
```

---

## ⚡ How to Run

> Full, tested steps: [`docs/setup-guide.md`](docs/setup-guide.md)

```bash
# 1. Clone the repo
git clone https://github.com/samSRaina/bob-ai-hackathon-cyber-elevate.git
cd bob-ai-hackathon-cyber-elevate

# 2. Backend
cd src/backend
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # Windows; use bin/pip on macOS/Linux

# 3. Frontend
cd ../frontend
bun install

# 4. Configure environment
cd ..
cp .env.example .env
# Edit src/.env — BOB_API_KEY is optional (falls back to a deterministic parser)

# 5. Run everything
cd ..
docker compose up -d postgres
# in one terminal: cd src/backend && uvicorn app.main:app --reload --port 8010
# seed once:        cd src/backend && python -m app.seed
# in another:        cd src/frontend && bun run dev
```

Dashboard: `http://localhost:5199` · API docs: `http://localhost:8010/docs`

---

## 🖥️ Demo

| Artifact | Link |
|---|---|
| 📹 Demo Video | [See demo/demo-video-link.txt](demo/demo-video-link.txt) |
| 🌐 Live Demo | [See demo/live-demo-url.txt](demo/live-demo-url.txt) |
| 🖼️ Screenshots | [See demo/screenshots/](demo/screenshots/) |
| 📊 Presentation | [See presentation/](presentation/) |

---

## ⚠️ Known Limitations

- **Bob's inference REST endpoint could not be confirmed working in this
  environment.** `engine/bob_client.py` is fully implemented against the most
  plausible documented endpoint shape (Bearer-auth, OpenAI-compatible chat
  completions), but the guessed base URL currently returns a Cloudflare edge
  challenge rather than an API response. Every seeded FIR was therefore
  extracted via the deterministic fallback parser (`extraction_source:
  "fallback_parser"`, visible per-FIR via the API) — see [Known limitation: Bob
  connectivity](docs/setup-guide.md#known-limitation-bob-connectivity) in the
  setup guide. The extraction contract (raw text in, structured JSON out) is
  identical either way, so plugging in a confirmed base URL requires no code
  change.
- **MO similarity is a heuristic, not proof.** Two unrelated crimes that happen
  to read very similarly can still surface as a low-confidence lead (capped
  below identifier- and name-based evidence in the confidence score precisely
  because of this) — it is designed to prompt human review, not to auto-confirm
  a link.
- **RBAC is a demo-grade role switcher, not authentication.** There is no login;
  the Navbar's Role Switcher sets request headers directly. This is intentional
  for a hackathon prototype focused on proving server-side scoping works, not
  building an auth system.
- **No copilot / chat UI, no real-time alerting.** Cut deliberately from an
  earlier, broader design so the core pipeline — ingest, link, explain, scope —
  is fully built and fully working end-to-end, rather than partially building a
  larger surface.
- **Frontend is intentionally unstyled** — a functional prototype, not a
  polished UI. Scope decision, not an oversight.
- **100 sample FIRs are synthetic**, built on the real, public CCTNS/NCRB FIR
  e-format schema (not scraped or fabricated real citizen case data) — see
  `src/backend/app/data/generate_seed_firs.py`.

---

## 🏅 What We're Most Proud Of

The entity-resolution + MO-similarity pipeline genuinely does what the problem
statement asks: 6 synthetic FIRs describing the same 3-person cyber-fraud crew —
filed under 5 different name spellings, across 3 different districts, with one FIR
naming no accused at all — collapse into **exactly one** flagged, explainable
syndicate cluster (confidence 0.97), while 94 unrelated noise FIRs correctly stay
separate. That result is verified end-to-end against the live database, not just
asserted.

---
