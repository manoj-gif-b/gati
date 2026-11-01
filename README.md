
# Gati: Adaptive Learning for Classes 6 to 8

Team Apex · Code Kernel '26

## The problem

In a class, students learn at different speeds. Fast students get bored, slow students fall behind, and teachers can't see who is stuck.

## What Gati does

Gati finds what each student knows and decides what they learn next:

- Weak basic skill? It sends the student back to revise the basic skill first.
- Skill mastered? It moves the student to the next skill.
- Otherwise, it gives more practice on the current skill.
- Mastered a skill? A short 3-question check confirms it. Pass 2 of 3 to move on.

Mastery is tracked with Bayesian Knowledge Tracing (BKT). Each answer updates the chance that the student knows the skill.

## Run it

Use PowerShell in the gati folder:

pip install -r requirements.txt
uvicorn app.main:app --reload

Open http://127.0.0.1:8000 and pick a demo student.

To run the tests:

pytest

## Demo steps

1. Pick a student and click Start.
2. Read the concept card and the reason it was chosen.
3. Answer one question wrong. The revisit reason appears.
4. Keep answering correctly until mastery is high. The check appears automatically.
5. Answer the 3 questions. You see pass or fail.

## Project files

- app/engine/bkt.py: mastery tracking (BKT)
- app/engine/next_step.py: rules for what comes next
- app/routes/: API endpoints
- web/: student app (plain HTML, CSS, JavaScript)
- data/: skills, concept cards, practice and test items
- docs/architecture.md: system diagram and data flow

## Limits of this prototype

- Pilot scope: Maths and Science, Classes 6 to 8, web app only
- Skills are sample topics. They are not the official NCERT or CBSE syllabus.
- Teacher view is available through the API for now (/docs). A dashboard screen is planned.
- Not built yet: Android app, Classes 9 and 10, regional languages, offline mode, parent reports