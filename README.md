# Gati

Gati is an adaptive learning app for school students in India. The pilot covers Maths and Science for Classes 6 to 8.

**Problem:** Students learn at different paces, but fixed classroom lessons leave some behind and bore others. Gati adapts to each student's mastery level, giving the right concept at the right time.

## How the adaptive loop works

1. **Map skills** — every subject is split into skills (about 10 per subject) linked by prerequisites, for example "fractions" depends on "whole numbers".
2. **Track mastery** — every answer updates the student's probability of knowing a skill using Bayesian Knowledge Tracing (BKT): correct answers raise mastery, wrong answers lower it.
3. **Choose next step** — rules decide what comes next: revisit basics if a prerequisite is weak (mastery below 0.40), a new concept if the current skill is mastered (mastery at least 0.95), or more practice otherwise.
4. **Check and update** — the student attempts the chosen item, mastery is updated, and the loop repeats.

## How to run locally

```powershell
pip install -r requirements.txt
uvicorn app.main:app --reload
```

> **Note:** If you pull schema changes (new columns/tables), delete `gati.db` (and `tests/test_gati.db`) so the app re-creates and re-seeds the database on startup.

The API serves on `http://127.0.0.1:8000` and the interactive docs are at `/docs`.

## How to run tests

```powershell
pytest
```

To run the browser-based demo test (requires a running uvicorn server on port 8000):

```powershell
$env:RUN_BROWSER_TESTS="1"
pytest -k browser -rs -v
```

## Student web app (Phase 2)

Open the app in the browser:

```powershell
uvicorn app.main:app --reload
```

Then visit `http://127.0.0.1:8000` and pick a demo student from the dropdown (no passwords). The student id is remembered in `localStorage`, so reopening the app resumes your session.

### Demo script (5 steps)

1. **Pick a student** from the dropdown and click **Start**.
2. **Learn** — the concept card and reason for the next skill appear.
3. **Solve** — answer one question wrong to see the revisit reason, then answer correctly until mastery reaches ~95%.
4. **Mastery check** — a 3-question test appears automatically when mastery crosses 95%.
5. **Submit** — click "Submit Mastery Check" to see the pass/fail result.

The app has three screens:
- **Learn** — shows the concept card for the next skill, with the reason it was chosen. A Continue button moves on to Solve.
- **Solve** — shows one practice item fetched from the API (the correct answer is never sent to the browser). After you submit, the server checks the answer, shows Correct/Incorrect, updates the mastery bar for that skill, and gives the next step's reason.
- **Test** — a 3-question mastery check that appears automatically when a skill is mastered.

## Architecture

See [docs/architecture.md](docs/architecture.md) for the system architecture, stack, components, data flow, and adaptivity rules.

## Prototype scope (Phase 1 + Phase 2)

- Subjects: Maths and Science
- Classes: 6 to 8
- Backend web API with one teacher view (class overview)
- SQLite by default; schema is PostgreSQL-compatible

> Note: the skills and items are sample topics based on common syllabus themes — this is **not** an official board syllabus.

### Test mastery rule (Phase 2)

When a skill's mastery crosses MASTERED (0.95) after an answer, the app automatically shows a 3-question mastery check. The student passes if they get at least 2 of 3 correct; the skill is then marked as confirmed mastered and the normal next-step logic continues. On failure, mastery is reset to 0.6 (a starting point toward WEAK = 0.40) and the revisit_basics reason is shown. This 0.6 value was chosen to give the student a second chance to relearn the skill before being retested, rather than dropping straight to WEAK.

## Planned for later

- Android app
- Classes 9 and 10
- Regional languages
- Parent reports
- Full PostgreSQL deployment
- Offline sync
