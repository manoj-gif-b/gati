# Gati — Architecture (Phase 1)

## Stack

- FastAPI backend, SQLAlchemy ORM, SQLite by default
- `DATABASE_URL` environment variable overrides the database; only PostgreSQL-compatible column types are used, so Postgres can be swapped in later
- No frontend framework yet

## Components

- `app/db.py` — engine/session factory, reads `DATABASE_URL`, `check_same_thread=False` for SQLite
- `app/models.py` — `SchoolClass`, `Student`, `Skill`, `Item`, `StudentSkillMastery`, `Attempt`
- `app/engine/skill_graph.py` — loads prerequisite graphs from `data/*.json` and queries them
- `app/engine/bkt.py` — Bayesian Knowledge Tracing update (documented formulas)
- `app/engine/next_step.py` — adaptivity rules: `MASTERED = 0.95`, `WEAK = 0.40`
- `app/routes/` — `POST /api/attempts`, `GET /api/students/{id}/map`, `GET /api/classes/{id}/overview`
- `app/main.py` — app wiring; lifespan loads the skill graphs and seeds the database

## Data flow

1. Client POSTs an attempt (`student_id`, `item_id`, `correct`, `time_taken_s`)
2. Endpoint resolves the item to its skill, loads the student's current mastery (defaults to `p_init`)
3. BKT updates mastery; the attempt and the new mastery are persisted
4. The rule engine picks the next step — revisit basics / new concept / practice — with a plain-English reason
5. Teacher views: student skill map (`/api/students/{id}/map`) and class overview of weakest skills (`/api/classes/{id}/overview`)

## Adaptivity rules

- If any prerequisite of the current skill is below `WEAK` (0.40) → `revisit_basics`, naming that prerequisite
- Else if the current skill is at least `MASTERED` (0.95) → `new_concept` for the next skill whose prerequisites are all mastered
- Else → `practice` the current skill

## Later phases

Android app, Classes 9–10, regional languages, parent reports, full PostgreSQL deployment, offline sync.