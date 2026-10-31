<p align="center">
  <img src="frontend/public/logo-mark.png" alt="SkillGraph AI logo" width="96" />
</p>

# SkillGraph AI

**Understand your skills. Discover your gaps. Build your career.**

SkillGraph AI is a full-stack career-readiness application. It builds an evidence-based skill profile for each signed-in user, compares that profile with a target role, explains the most important gaps and bottlenecks, generates a prerequisite-aware learning roadmap, and connects learning, projects, interview practice, job matching and spaced recall in one workflow.

The application is intentionally transparent: scores and recommendations come from documented deterministic rules over the user's own stored evidence—not from a chatbot, hidden AI scoring, or hard-coded dashboard numbers.

---

## Table of contents

- [Overview](#overview)
- [Main features](#main-features)
- [How the application works](#how-the-application-works)
- [Technology stack](#technology-stack)
- [Project structure](#project-structure)
- [Quick start](#quick-start)
- [Manual setup](#manual-setup)
- [Docker setup](#docker-setup)
- [Configuration](#configuration)
- [First-time user guide](#first-time-user-guide)
- [Scoring and skill intelligence](#scoring-and-skill-intelligence)
- [Database and migrations](#database-and-migrations)
- [API guide](#api-guide)
- [Security and data isolation](#security-and-data-isolation)
- [Testing](#testing)
- [Production notes](#production-notes)
- [Troubleshooting](#troubleshooting)
- [Limitations and future work](#limitations-and-future-work)
- [Repository hygiene](#repository-hygiene)

---

## Overview

A learner usually has evidence scattered across a resume, self-assessment, completed lessons, projects, quizzes and interview practice. SkillGraph AI combines that evidence into one skill model and answers practical questions:

1. **Where am I now?** — What skills do I appear to have, and what evidence supports them?
2. **What does my target role need?** — Which role skills are strong, weak or missing?
3. **What is holding me back most?** — Which weak foundation blocks the largest amount of future progress?
4. **What should I do next?** — What is the next prerequisite-ready learning step, project or practice activity?
5. **Is my confidence realistic?** — Does my own rating agree with objectively scored practice?
6. **What should I revise?** — Which completed skills are due for a short recall check?

### Included catalog

The seeded curated catalog currently contains:

| Content | Count | Notes |
|---|---:|---|
| Skills | 53 | Includes aliases and prerequisite relationships |
| Career roles | 10 | Each role has required/optional skills and importance weights |
| Skill taxonomies | 12 | Topic checklists for supported skills |
| Practice questions | 59 | MCQ, technical, scenario, coding, behavioural, project and HR categories |
| Project ideas | 15 | Demo/sample portfolio projects |
| Job listings | 17 | Demo/sample listings with fictional companies |

Sample jobs, projects and questions are labelled as demo content in the application. User profiles, progress, attempts and recommendations are real per-user database records.

---

## Main features

### Account and profile

- Email/password registration and login with JWT authentication.
- UUID user identity derived only from the verified token.
- Profile details and optional profile photo.
- Target-role selection, including clearly labelled generated/custom roles derived from the nearest curated role.
- Save/Discard workflow for profile, role and assessment forms; drafts are not applied until the user saves.
- Unsaved-change indicators and navigation warnings.

### Resume analysis

- Upload `.pdf`, `.docx` or `.txt` resumes up to 5 MB.
- Resume upload is staged first; it does not affect the profile until the user reviews the extracted skills and confirms.
- Users can exclude incorrectly detected skills before saving.
- Shows matched and missing skills for the selected target role.
- Resume files are not publicly served.

### Skill assessment

- Per-skill self-level (for example beginner/intermediate/advanced).
- Topic checklists where a curated taxonomy exists.
- A separate 0–100 confidence rating: “I could use this independently.”
- Saving an assessment recalculates skill estimates, gaps, readiness, roadmap order and recommendations.

### Dashboard

- Overall and component readiness.
- Next Best Action with a plain-English reason.
- “What is preventing you reaching 80%?” blockers, calculated by simulating candidate improvements.
- Skill overview, skill network preview, roadmap preview, recommended projects and jobs.
- Biggest current bottleneck and due/upcoming recall checks.
- Recent user activity.
- Honest onboarding state for new/sparse accounts instead of invented scores.

### Skill Graph and Skill Gap

- Interactive SVG graph of target-role skills and prerequisite relationships.
- Skill states: acquired/strong, in progress/weak and missing.
- Select a skill to see its evidence, score, verification status, prerequisites, unlocks and next action.
- Amber bottleneck markers and review-due markers, also described in accessible text.
- Skill Gap page groups critical, weak, missing and strong skills in learning-priority order.

### Learning Roadmap

- Prerequisite-safe order based on importance, unlock value, demand, readiness and ease.
- Completed/current/available/locked step states.
- Completion is preserved when scores or review schedules change.
- Due reviews can appear beside completed work without reopening the milestone.
- “Why prioritized” explanations help users understand ordering.

### Learn & Build

For each selected skill, the page combines:

- Learning resources and documentation links, where available.
- YouTube search links by default, or real YouTube API results when `YOUTUBE_API_KEY` is configured.
- Practice questions and short knowledge checks.
- Project ideas that build the skill.
- “Prove” suggestions such as finishing a project, passing a check or adding a certificate.
- Confidence calibration and recall schedule panels.

### Projects and certifications

- Project recommendations filtered by level, readiness, skill and status.
- Project status: planned, in progress or completed.
- Completed projects become skill evidence and can create recall schedules for gained skills.
- Users can record certifications and link them to a skill where supported.

### Job matching and job-description analysis

- Demo job listings matched against the user's evidence-based skills.
- Filters for search, minimum match, experience, location, saved/applied status and sorting.
- Save/apply/undo state is persisted per user.
- Users can paste a job description to identify known catalog skills and gaps.

### Interview preparation

- Practice sessions based on target role, weakest skills, a selected skill, a job or a pasted job description.
- MCQ answers are scored exactly.
- Supported open answers are scored by transparent keyword coverage.
- Coding, behavioural, HR and project questions may be self-rated; self-ratings are never treated as objective calibration evidence.
- Attempts are stored with category, purpose, session, topic and correctness where applicable.

### Integrated skill intelligence

Three newer capabilities are integrated into the existing pages rather than added as separate modules:

1. **Bottleneck detection** — finds weak foundations that block many important unfinished skills.
2. **Confidence calibration** — compares self-confidence with objectively scored practice.
3. **Adaptive recall** — schedules short spaced checks after learning and adjusts the next interval from the result.

See [Scoring and skill intelligence](#scoring-and-skill-intelligence) for formulas and limitations.

---

## How the application works

```text
React frontend
    │
    │  Same-origin /api requests + JWT
    ▼
FastAPI routes
    │
    ├── UserScope repository (forces the authenticated user_id on user-owned data)
    │
    ├── SQLAlchemy database (PostgreSQL in Docker/production, SQLite for local development)
    │
    └── Analysis pipeline
          ├── load resume, assessment, learning, project and attempt evidence
          ├── estimate each skill once
          ├── calculate role gap and readiness
          ├── order the roadmap respecting prerequisites
          ├── calculate bottlenecks, calibration and recall state
          └── build page-ready dashboard, graph, roadmap and recommendation payloads
```

Every major mutation—assessment save, resume confirmation, learning completion, project status, certification, interview/knowledge-check answer or target-role change—refreshes the same analysis pipeline. This keeps Dashboard, Skill Graph, Roadmap, Learn and recommendations consistent.

### Sparse-data behaviour

The application does not invent a readiness score for a brand-new account. Until at least **25% of the target role's skills have some evidence**, learning modules return onboarding guidance and withhold scores/gaps/recommendations. Evidence can come from the assessment and/or a confirmed resume.

---

## Technology stack

| Area | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite 5, React Router, TanStack Query, Tailwind CSS |
| Backend | FastAPI, Uvicorn, SQLAlchemy 2, Pydantic 2 |
| Authentication | JWT (`PyJWT`), bcrypt password hashing |
| Database | PostgreSQL via Docker, or SQLite for local/single-instance development |
| Resume parsing | Built-in text/DOCX handling and `pypdf` for PDF text extraction |
| Scoring | Deterministic Python engines in `backend/app/engine` |
| Optional semantic helpers | Hashing/brute-force fallback included; external embedding/FAISS packages are optional and not required |
| Tests | Pytest plus a dependency-free pure-Python test runner |

### Prerequisites

For the recommended local setup:

- **Python 3.12 recommended** (the code requires Python 3.10+; Docker uses 3.12).
- **Node.js 20 or newer** (Docker uses Node 22) and npm.
- Bash for `scripts/run_local.sh` (Linux, macOS, WSL or Git Bash).
- Docker and Docker Compose only if using the Docker setup.

---

## Project structure

```text
skillgraph-ai/
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI route modules and authentication dependencies
│   │   ├── core/             # Settings, database, security and schema migrations
│   │   ├── data/             # Curated skills, roles, jobs, projects and questions
│   │   ├── engine/           # Knowledge, gap, roadmap, jobs, interview and intelligence logic
│   │   ├── graph/            # Skill graph helpers
│   │   ├── ml/               # Small semantic-search helpers used by the backend
│   │   ├── models/           # SQLAlchemy models
│   │   ├── nlp/              # Resume text extraction/parsing
│   │   ├── repositories/     # User-scoped data access
│   │   ├── schemas/          # API request/response schemas
│   │   ├── services/         # Analysis pipeline, page payloads, seeding and integrations
│   │   └── utils/            # Shared backend utilities such as rate limiting
│   ├── migrations/           # Data-preserving schema-upgrade notes/wrapper
│   ├── uploads/              # Runtime uploads (only .gitkeep is packaged)
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── public/               # Final logo/favicon assets used by the web app
│   ├── src/
│   │   ├── components/       # Shared UI, forms, graph and intelligence panels
│   │   ├── hooks/            # API/profile/motion hooks
│   │   ├── layouts/          # Authenticated and authentication layouts
│   │   ├── pages/            # Route pages
│   │   ├── services/         # Frontend API client and token storage
│   │   ├── store/            # Auth, dirty-form and notice state
│   │   └── types/            # Shared TypeScript types
│   ├── Dockerfile
│   ├── package.json
│   └── package-lock.json
├── design/                   # Original logo source and asset-generation script
├── ml/                       # Experimental ranking/model code and pure evaluation helpers
├── scripts/
│   ├── init_db.py            # Create tables, migrate older schemas and seed the catalog
│   ├── migrate_db.py         # Upgrade an existing database in place
│   ├── run_local.sh          # One-command local backend + frontend runner
│   └── seed_demo.py          # Optional demo-account seeding (DEMO_MODE only)
├── tests/                    # Backend, API, isolation, engine and intelligence tests
├── .env.example              # Documented configuration template
├── docker-compose.yml
├── pytest.ini
└── README.md
```

Runtime files such as `.env`, local databases, uploaded resumes/photos, `node_modules`, frontend build output and Python caches are intentionally excluded from the clean ZIP.

---

## Quick start

This is the easiest way to run the complete application locally without Docker.

From the extracted project root:

```bash
cd skillgraph-ai
bash scripts/run_local.sh
```

Then open:

```text
http://localhost:5173
```

Create a new account on first use.

### What the script does

On the first run it:

1. Creates a local `.env` with a generated `SECRET_KEY` and a SQLite database path.
2. Creates `data/` and `backend/uploads/` if needed.
3. Installs backend Python dependencies if FastAPI is not importable.
4. Runs `scripts/init_db.py` to create/seed the database.
5. Runs `scripts/migrate_db.py` so an older existing database is upgraded in place.
6. Installs frontend dependencies if `frontend/node_modules` is missing.
7. Starts the backend on port **8000** and the frontend on port **5173**.
8. Checks `http://127.0.0.1:8000/health`.

Press **Ctrl+C** to stop both servers.

> Accounts are stored in your local database. If you delete the database or use a different `DATABASE_URL`, previously created local accounts will not exist there.

---

## Manual setup

Use this method if you prefer separate terminals or cannot run the Bash script.

### 1. Configure the environment

From the project root:

```bash
cp .env.example .env
```

Generate a secret key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Edit `.env` and set at least:

```dotenv
DEMO_MODE=false
SECRET_KEY=replace-with-the-generated-secret
DATABASE_URL=sqlite:////absolute/path/to/skillgraph-ai/data/skillgraph.db
CORS_ORIGINS=http://localhost:5173
UPLOAD_DIR=/absolute/path/to/skillgraph-ai/backend/uploads
```

For PostgreSQL, use a URL such as:

```dotenv
DATABASE_URL=postgresql+psycopg2://skillgraph:your-password@localhost:5432/skillgraph
```

SQLite is suitable for local development and a small single-instance deployment. Use PostgreSQL for a real multi-user production deployment.

### 2. Install and initialize the backend

```bash
python -m pip install -r backend/requirements.txt
python scripts/init_db.py
python scripts/migrate_db.py
```

`init_db.py` creates missing tables, applies the data-preserving intelligence migration and seeds the curated catalog. `migrate_db.py` is a safe no-op when the database is already current.

Start the API:

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Backend URLs:

- Health: `http://localhost:8000/health`
- OpenAPI/Swagger UI: `http://localhost:8000/docs`

### 3. Install and start the frontend

In a second terminal, from the project root:

```bash
cd frontend
npm ci
npm run dev -- --host 0.0.0.0 --port 5173
```

Open `http://localhost:5173`.

The browser calls same-origin `/api/...` URLs. During development, Vite proxies those requests to the backend (`VITE_API_PROXY`, default `http://localhost:8000`). Do not point browser code directly at `localhost:8000` unless you intentionally configure a separate API origin.

### 4. Optional production-style frontend build

```bash
cd frontend
npm run typecheck
npm run build
npm run preview -- --host 0.0.0.0 --port 4173
```

For real production hosting, serve the generated `frontend/dist` with a static host or reverse proxy and proxy `/api` to the backend. The included frontend Dockerfile currently runs the Vite development server and should be treated as a development/demo setup.

---

## Docker setup

Create and edit `.env` first:

```bash
cp .env.example .env
# Set SECRET_KEY to a random value of at least 32 characters.
docker compose up --build
```

Services:

| Service | URL/port | Purpose |
|---|---|---|
| `frontend` | `http://localhost:5173` | Vite web application |
| `backend` | `http://localhost:8000` | FastAPI API |
| `db` | `localhost:5432` | PostgreSQL 16 |
| `redis` | `localhost:6379` | Included in the Compose stack; the current application code does not require it |

Docker Compose overrides `DATABASE_URL` so the backend connects to the `db` service. The backend container runs `scripts/init_db.py` before starting Uvicorn; that creates/seeds tables and applies the current data-preserving migration.

Stop the stack with:

```bash
docker compose down
```

Add `-v` only if you also want to delete the PostgreSQL/uploads volumes and all local Docker data.

> Verify the Docker/PostgreSQL path on your target Docker host before production use. The automated verification performed for this package used SQLite locally; Docker was not available in the verification environment.

---

## Configuration

Configuration is read from real environment variables first, then from `.env` in the current directory, `backend/.env`, or the project-root `.env`.

| Variable | Required | Default/example | Description |
|---|---:|---|---|
| `DEMO_MODE` | No | `false` | Keep `false` for normal use. Demo accounts only work when `true`. |
| `SECRET_KEY` | **Yes** when `DEMO_MODE=false` | generated random value | JWT signing secret; must be at least 32 characters. Never commit it. |
| `DATABASE_URL` | Yes for real deployments | PostgreSQL or SQLite URL | SQLAlchemy database connection string. |
| `CORS_ORIGINS` | No | `http://localhost:5173` | Comma-separated browser origins allowed to call the API directly. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `60` | JWT lifetime. |
| `UPLOAD_DIR` | No | `uploads` | Directory for profile photos/runtime uploads. Use an absolute path outside the code directory for production. |
| `YOUTUBE_API_KEY` | No | empty | If set and reachable, Learn pages can show specific videos; otherwise they show clearly marked YouTube search links. |
| `VITE_API_PROXY` | Frontend only | `http://localhost:8000` | Backend target used by Vite's server-side `/api` proxy. Docker Compose sets `http://backend:8000`. |
| `VITE_API_URL` | Frontend only | unset | Only for a genuinely separate API origin, for example `https://api.example.com` with no trailing slash. Leave unset for the normal same-origin `/api` setup. |

The backend also has settings for maximum resume/photo sizes and authentication rate limiting in `backend/app/core/config.py`.

---

## First-time user guide

1. **Create an account** or log in.
2. **Complete your profile** and save.
3. **Choose a target role** and save.
4. Add evidence in either or both ways:
   - Upload a resume, review extracted skills, remove incorrect detections and save; and/or
   - Complete the skill assessment, including levels, topic checklists and confidence ratings, then save.
5. Continue until at least 25% of the role's skills have evidence; full gap/roadmap intelligence then becomes available.
6. Open the **Dashboard** to see readiness, Next Best Action, blockers, the top bottleneck and due reviews.
7. Open **Skill Graph** and select skills to understand their evidence, prerequisites and unlocks.
8. Follow the **Learning Roadmap** or the bottleneck action into **Learn & Build**.
9. Complete learning steps/resources and mark them complete. This creates spaced recall work.
10. Use knowledge checks and interview practice to test understanding. Results update evidence and calibration.
11. Build recommended projects and mark them completed to add stronger skill evidence.
12. Revisit Dashboard/Skill Graph/Roadmap as new evidence changes priorities.

### Example intelligence loop

```text
Target role selected
        ↓
Weak foundation identified as a bottleneck
        ↓
User studies it in Learn & Build and completes a step
        ↓
A recall check is scheduled
        ↓
User answers scored questions
        ↓
Attempts + evidence update the skill estimate and confidence calibration
        ↓
Next review interval, bottleneck priority, roadmap order and Next Best Action refresh
```

---

## Scoring and skill intelligence

### 1. Single skill estimate

Each user/skill has one authoritative cached estimate in `user_skills`, recomputed from stored evidence by the analysis pipeline. Evidence and attempt history are retained separately; new activity does not erase earlier history.

Default source weights are:

| Evidence source | Weight |
|---|---:|
| Resume | 15% |
| Self-assessment | 20% |
| Scored assessment/questions | 25% |
| Projects | 20% |
| Completed learning | 10% |
| Interview/open-answer practice | 10% |

Only sources that exist are included, and their weights are normalized. If a skill has only resume/self-report evidence, its score is capped at **60** and estimate confidence is capped at **0.35**, so a checkbox or resume mention cannot by itself make a user an expert.

### 2. Role readiness

- A role skill earns full readiness credit at a score of **70**.
- Required skills use their full importance weight; optional skills use half weight.
- Overall readiness is **70% skills, 15% projects and 15% interview** when interview data exists.
- Three completed role-relevant projects earn full project credit.
- If the user has not practised interviews yet, interview is shown as not measured and the remaining weights are renormalized rather than assigning an invented zero/invented score.

### 3. Gap and roadmap priority

Skill status thresholds:

- **Strong:** score ≥ 55
- **Weak:** 20 ≤ score < 55
- **Missing:** score < 20

Roadmap priority weights:

| Component | Weight |
|---|---:|
| Role importance | 35% |
| Unlock value | 25% |
| Demand | 15% |
| Readiness/prerequisite readiness | 15% |
| Ease | 10% |

Unlock value blends the number of unfinished downstream skills and their career importance. Final ordering remains prerequisite-safe. Completed progress is preserved; a due review does not reopen a completed roadmap step.

### 4. Bottleneck detection

A bottleneck candidate must be not yet strong and must have at least one unfinished downstream skill in the role/gap analysis.

```text
weakness = 1 − min(current_score, 70) / 70
downstream_count_n = min(1, unfinished_downstream_count / 6)
downstream_importance_n = min(1, summed_downstream_importance / 3)

current_stage =
  1.0 if the skill is/blocks the current roadmap step
  0.5 if it blocks a near/current available step
  0.0 otherwise

bottleneck_score = 100 × (
  0.35 × weakness +
  0.30 × downstream_importance_n +
  0.15 × downstream_count_n +
  0.20 × current_stage
)
```

Only the curated prerequisite edges in the catalog are used. The application explains the current score, downstream skills, formula components and recommended action.

### 5. Confidence calibration

Calibration compares:

- **Self-confidence:** the explicit Assessment slider when present; otherwise the mapped self-level/checklist rating.
- **Demonstrated performance:** objectively scored attempts only.
- **System estimate:** the blended skill estimate above.

Objective attempts are weighted as follows:

| Question type | Calibration weight | Scoring |
|---|---:|---|
| MCQ | 1.0 | Exact correct/incorrect |
| Technical open answer with keywords | 0.6 | Keyword coverage |
| Scenario open answer with keywords | 0.6 | Keyword coverage |
| Self-rated coding/behavioural/HR/project | Excluded | Not objective evidence |

Demonstrated performance uses up to the last 8 objective attempts and applies recency weighting with a 90-day half-life:

```text
recency_weight = 0.5 ^ (attempt_age_days / 90)
```

A calibration label is produced only when:

- a self-rating exists;
- at least **3 objective attempts** exist; and
- the latest objective attempt is within **90 days**.

Then:

```text
difference = self_confidence − demonstrated_performance

|difference| ≤ 15  → aligned
difference > 15    → rating higher than recent practice
difference < −15   → practice stronger than rating
otherwise           → Needs more evidence
```

The panel shows the system estimate, self-rating, demonstrated score, latest result, freshness, question coverage, missed topics and next action. Short checks are treated as one signal, not a final verdict.

### 6. Adaptive recall

Completing one of the following can create or preserve a recall schedule:

- Roadmap step
- Learning resource
- Skill-linked certification
- Completed project (for skills gained from that project)

Initial review: **1 day after learning**.

Interval ladder:

```text
1 → 3 → 7 → 14 → 30 → 60 days
```

After a recall check:

| Score | Result | Next interval |
|---:|---|---|
| ≥ 80% | Strong | Advance one stage, capped at 60 days |
| 50–79% | Partial | Keep the stage and halve the current interval, minimum 1 day |
| < 50% | Weak | Return to stage 0 / 1 day and revisit learning material |

Review states are **overdue**, **due today**, **upcoming** (within 7 days) and **scheduled**. If there is no objective evidence or it is older than 90 days, the check is presented as a diagnostic; the app does not assume the user has forgotten the skill.

Recall question selection prioritizes questions/topics previously missed, then unseen objective questions. A completed milestone stays completed regardless of recall status.

### Scheduling/configuring the rules

The main intelligence constants are centralized near the top of:

- `backend/app/engine/intelligence.py` — bottleneck weights, calibration thresholds and recall intervals.
- `backend/app/engine/knowledge.py` — evidence-source weights and self-only cap.
- `backend/app/engine/gap.py` — strong/weak thresholds, readiness target and roadmap priority weights.

Change tests and documentation whenever these policies are tuned.

---

## Database and migrations

SQLAlchemy models define 35 tables covering:

- Users, profiles and revoked tokens.
- Shared catalog data: skills, aliases, dependencies, taxonomies, roles and role skills.
- User skill estimates, assessments, evidence and certifications.
- Resumes and extracted resume skills.
- Roadmaps, roadmap items and user progress.
- Projects, resources and user project status.
- Jobs, job skills and applications/status.
- Interview questions and attempts.
- Activity, search/recommendation support tables.
- `skill_recall_schedules` for spaced recall.

### Fresh database

```bash
python scripts/init_db.py
```

This creates missing tables, applies the current additive intelligence migration and seeds the catalog.

### Existing database

Back up the database first, then run:

```bash
python scripts/migrate_db.py
```

The migration is designed to be idempotent and data-preserving. It adds the confidence/calibration fields, interview-attempt metadata, `completed_at`, recall schedules and required indexes/uniqueness constraints. Duplicate assessment rows are merged before uniqueness is enforced. Existing users and progress are not deleted and no reseed is required.

`scripts/run_local.sh` runs initialization followed by migration on every start.

For production, back up both:

- the PostgreSQL database (or SQLite file if intentionally used); and
- the uploads directory/volume.

---

## API guide

The FastAPI application exposes interactive documentation at:

```text
http://localhost:8000/docs
```

Routes are available both unprefixed (for direct API use) and under `/api` (used by the frontend proxy). For example, `POST /auth/login` and `POST /api/auth/login` reach the same handler.

### Authentication

Register:

```http
POST /api/auth/register
Content-Type: application/json

{
  "full_name": "Example User",
  "email": "user@example.com",
  "password": "a-strong-password",
  "confirm_password": "a-strong-password"
}
```

Login:

```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "a-strong-password"
}
```

Send the returned token on authenticated requests:

```http
Authorization: Bearer <token>
```

The web client also sends `X-Auth-Token` as a resilience fallback for proxy environments that damage/strip `Authorization`; API clients should normally use the standard Bearer header.

No endpoint accepts a client-supplied user ID. Identity always comes from the verified JWT.

### Main endpoint groups

| Area | Examples |
|---|---|
| Health | `GET /health` |
| Auth | `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`, `POST /api/auth/logout` |
| Profile | `GET/PUT /api/profile`, `POST/GET /api/profile/photo` |
| Roles | `GET /api/roles`, `GET /api/roles/{role_id}`, `PUT /api/roles/target` |
| Assessment | `GET/POST /api/assessment` |
| Resume | `POST /api/resume/upload`, `POST /api/resume/confirm`, `GET /api/resume`, `DELETE /api/resume`, `DELETE /api/resume/pending`, `POST /api/resume/analyze` |
| Skills/search | `GET /api/skills`, `GET /api/skills/{slug}`, `/taxonomy`, `/projects`, `/jobs`, `/resources`, `GET /api/search` |
| Gap/graph | `GET /api/skill-gap`, `GET /api/skill-graph`, `POST /api/skill-gap/analyze` |
| Roadmap | `GET /api/roadmap`, `POST /api/roadmap/generate`, `PUT /api/roadmap/{slug}/complete` |
| Learn/build | `GET /api/learn`, `GET /api/learn/{slug}`, `PUT /api/learn/{slug}/complete`, `GET /api/build` |
| Projects | `GET /api/projects`, `GET /api/projects/recommended`, `POST /api/projects/{key}/status` |
| Certifications/activity | `GET/POST /api/certifications`, `POST /api/activity` |
| Jobs | `GET /api/jobs`, `GET /api/jobs/recommended`, `POST /api/jobs/analyze`, `GET /api/jobs/{key}`, `POST/DELETE /api/jobs/{key}/status` |
| Interview | `GET /api/interview`, `POST /api/interview/start`, `POST /api/interview/answer`, `GET /api/interview/readiness` |
| Recommendations | `GET /api/recommendations`, `/next-best-action`, `/next-skill` |
| Dashboard/progress | `GET /api/dashboard`, `GET /api/progress` |

### Skill-intelligence endpoints

Save explicit confidence through the existing assessment endpoint:

```http
POST /api/assessment

{
  "answers": [
    {
      "skill": "python",
      "level": "intermediate",
      "checklist": {"Functions": true},
      "confidence": 75
    }
  ]
}
```

Start a short scored check:

```http
POST /api/interview/check/start

{
  "skill": "python",
  "purpose": "calibration",
  "count": 3
}
```

Submit the whole check:

```http
POST /api/interview/check/submit

{
  "skill": "python",
  "purpose": "recall",
  "session_id": "returned-by-start",
  "answers": [
    {"question_key": "example-key", "choice": 1},
    {"question_key": "example-open-key", "answer": "..."}
  ]
}
```

Get due/upcoming reviews:

```http
GET /api/learn/recall/due
```

Important check responses/errors:

| Status | Meaning |
|---:|---|
| 401 | Missing/invalid/expired authentication |
| 404 | Unknown skill, question or owned record |
| 409 | Recall requested before any learning activity for that skill; use calibration or learn first |
| 413 | Upload is too large |
| 422 | Validation failure, unknown assessment skill/checklist item, invalid answer, or no scored questions exist for the skill |
| 429 | Authentication rate limit exceeded |
| 503 | Database unavailable |

Dashboard, Skill Graph, Skill Gap, Roadmap, Learn, Assessment, Interview and recommendation payloads also embed the shared `intelligence` object.

---

## Security and data isolation

- Passwords are hashed with bcrypt; plaintext passwords are not stored.
- JWTs include an expiry and token ID; logout revocation is supported.
- Normal (`DEMO_MODE=false`) startup refuses a missing/placeholder/short `SECRET_KEY`.
- User identity is taken only from the verified JWT subject.
- User-owned reads/writes go through `backend/app/repositories/scoped.py::UserScope`, which injects the authenticated `user_id` into queries and forces it on writes.
- User-owned tables use indexed `user_id` foreign keys with cascading deletion.
- Static tests fail if API/service code directly queries user-owned models outside the scoped repository pattern or if an endpoint accepts a client user ID.
- Profile photos are served only through the authenticated owner endpoint; uploads are not mounted as a public directory.
- Resumes are never served back through a public file route.
- Auth endpoints are rate-limited per client IP by default.
- The browser stores only the access token (with an in-memory fallback when browser storage is blocked). Treat token storage as an XSS-sensitive area and keep dependencies/content security under review before production.

PostgreSQL Row Level Security is **not** enabled; isolation is enforced at the application/repository layer and covered by tests. Add database RLS as a second layer for a high-assurance production deployment.

---

## Testing

Run commands from the project root unless stated otherwise.

### Full backend test suite

Install backend dependencies first, then run:

```bash
python -m pytest -q
```

`pytest.ini` already sets `pythonpath = backend` and `testpaths = tests`.

Latest verified result for this package:

```text
209 passed
```

There is one known third-party Starlette/anyio deprecation warning in the test environment; it does not fail the suite.

### Dependency-free engine/static tests

```bash
PYTHONPATH=backend python tests/run_pure.py
```

Latest verified result:

```text
95 passed, 0 failed
```

### Skill-intelligence tests only

```bash
python -m pytest -q tests/test_intelligence.py
```

These 15 tests are included in the 209-test full-suite count and cover formulas, the assessment → check → learning → recall API flow, user isolation, error paths and schema migration.

### Frontend checks

```bash
cd frontend
npm ci
npm run typecheck
npm run build
```

Latest verified result: TypeScript passes and the Vite production build succeeds.

### Test areas

| File | Coverage |
|---|---|
| `tests/test_auth.py` | Registration, login, token handling and auth regressions |
| `tests/test_profile.py` | Profile and schema behaviour |
| `tests/test_api_modules.py` | Main API modules and end-to-end API payloads |
| `tests/test_multi_user.py` | Per-user isolation and multi-user behaviour |
| `tests/test_engine.py` | Scoring, catalog, gap, roadmap, jobs, interview and search engines |
| `tests/test_intelligence.py` | Bottlenecks, calibration, recall and migration |
| `tests/test_isolation_static.py` | UserScope rules, routes/navigation, saved-form and frontend integrity checks |
| `tests/test_ml_pure.py` | Pure ML preprocessing/ranking/metrics helpers |
| `tests/run_pure.py` | Runs dependency-free test modules without pytest |

There are currently no committed React component or browser end-to-end tests. Browser verification for this package was performed separately with Chromium/Playwright against the live local application.

---

## Production notes

Before exposing the application publicly:

1. Use PostgreSQL rather than SQLite for multi-user traffic.
2. Set a long random `SECRET_KEY` through your secret manager, not source control.
3. Run `python scripts/migrate_db.py` against a backed-up database during deployment.
4. Serve the frontend build (`frontend/dist`) from a static host/reverse proxy over HTTPS; do not rely on the Vite dev server for production.
5. Proxy same-origin `/api` requests to the backend, or carefully configure `VITE_API_URL` and `CORS_ORIGINS` for a separate API origin.
6. Put uploads on durable backed-up storage.
7. Back up the database and uploads together and test restoration.
8. Review token-storage/XSS risk, add per-account lockout and consider PostgreSQL RLS.
9. Add browser end-to-end tests for registration, onboarding, resume confirmation, assessment, roadmap completion, projects/jobs and knowledge checks.
10. Consider Alembic for future schema versions beyond the current additive migration utility.

---

## Troubleshooting

### “Can't reach the server” on the login page

The frontend is running but cannot reach the backend. Confirm both processes are running and check:

```bash
curl http://127.0.0.1:8000/health
```

If using `run_local.sh`, keep its terminal open. If running manually, start Uvicorn in one terminal and Vite in another.

### Backend refuses to start because of `SECRET_KEY`

When `DEMO_MODE=false`, set a random secret of at least 32 characters:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Put the value in the project-root `.env` or your deployment environment.

### Login says the account does not exist

Accounts belong to the currently configured database. A fresh SQLite/PostgreSQL database will not contain accounts from another local run or hosted preview. Create an account, or point `DATABASE_URL` back to the intended database.

### Port 8000 or 5173 is already in use

Stop the process using that port, or start the services on different ports and update the proxy/CORS settings accordingly. The default expectation is backend `8000` and frontend `5173`.

### Frontend loads but API requests return 401 after login

- Make sure the browser is using the current backend/database and the token has not expired.
- Check backend logs; authentication failures log a reason category without logging token values.
- If using a separate API origin, confirm `VITE_API_URL` and `CORS_ORIGINS` are correct.
- If using the normal setup, leave `VITE_API_URL` unset so requests use same-origin `/api`.

### Database table/column errors after upgrading code

Back up the database and run:

```bash
python scripts/migrate_db.py
python scripts/init_db.py
```

Do not delete a production database to fix a migration problem.

### Resume text is empty or incomplete

Supported formats are `.pdf`, `.docx` and `.txt`, up to 5 MB. Scanned/image-only PDFs are not OCR-processed. Use a text-based PDF or DOCX/TXT version.

### No scored questions for a skill

Some catalog skills have no MCQ or keyword-scored technical/scenario questions. The check endpoint returns a clear `422` message. Use learning resources, projects and other evidence for that skill, or extend `backend/app/data/questions_data.py` and its tests.

### YouTube results are search links

That is the default no-key behaviour. Set `YOUTUBE_API_KEY` to request specific videos. If the API is unavailable or over quota, the application falls back to search links rather than inventing video URLs.

---

## Limitations and future work

Current limitations are intentionally documented rather than hidden:

- The skill/role/question catalog is small and curated; some roles have limited coverage.
- Job listings and project ideas are demo/sample data, not live job-board/project data.
- Open-answer scoring is keyword coverage, not expert or LLM grading.
- Short checks provide a signal; they do not definitively prove expertise.
- No OTP, email verification, forgot-password flow, admin portal, RBAC, settings page or notifications module is included.
- Assessment/profile drafts are browser-side until Save; there is no server-side autosave/resume-later assessment state.
- The top-level `ml/` Two-Tower and SASRec code is experimental and untrained. The running recommender uses transparent rules and activity recency; API responses report this under `model_status`.
- Custom roles borrow requirements from the nearest curated role and are labelled as generated/derived.
- PostgreSQL Row Level Security and per-account login lockout are not implemented.
- The Docker frontend uses Vite dev mode; see [Production notes](#production-notes).
- Docker/PostgreSQL should be verified on the target host; this package's live database verification used SQLite.

Recommended future work, in practical order:

1. Production static frontend hosting + HTTPS reverse proxy and Docker/PostgreSQL deployment verification.
2. Alembic-managed migrations.
3. Forgot-password/email verification and stronger account recovery.
4. Browser E2E tests and React component tests.
5. Larger curated skill/role/question catalog.
6. Settings, notifications and a fuller applications tracker.
7. Admin/RBAC/content management.
8. Train/evaluate ML recommenders only after sufficient consented activity data exists.

---

## Repository hygiene

Keep the repository and release ZIP clean. Do not commit or package:

- `.env` or any real secret/API key
- Local `.db`, `.sqlite` or `.sqlite3` files
- Uploaded resumes or profile photos
- `frontend/node_modules/`
- `frontend/dist/`
- Python `__pycache__/`, `.pytest_cache/` and `*.pyc`
- TypeScript `*.tsbuildinfo`
- Logs, coverage output and editor/OS metadata

The included `.gitignore` covers these paths. The clean release package keeps source code, tests, lockfiles, configuration templates, final web assets and the original logo source/generator, but excludes the duplicate standalone browser-preview prototype and all generated/runtime artifacts.
