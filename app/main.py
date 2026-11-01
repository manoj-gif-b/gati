"""Gati app: FastAPI wiring, skill graphs, and startup seed data."""
import json
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

import app.models as models  # noqa: F401  (registers all models with the SQLAlchemy Base)
from app.db import SessionLocal, init_db
from app.engine.skill_graph import SkillGraph
from app.routes import attempts, classes as classes_router, items, skills, students, tests

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "web")
GRAPH_FILES = {
    "maths": "skill_graph_maths_6_8.json",
    "science": "skill_graph_science_6_8.json",
}
CONCEPT_FILES = {
    "maths": "concepts_maths_6_8.json",
    "science": "concepts_science_6_8.json",
}

skill_graphs = {}
concepts = {}


def _seed(session):
    """Load skill graphs and practice items into an empty database, plus a small
    demo set of classes and students so the API works out of the box."""
    if session.query(models.Skill).first() is None:
        for subject, filename in GRAPH_FILES.items():
            with open(os.path.join(DATA_DIR, filename), encoding="utf-8") as f:
                data = json.load(f)
            for entry in data["skills"]:
                session.add(
                    models.Skill(
                        id=entry["id"],
                        name=entry["name"],
                        subject=entry["subject"],
                        class_grade=entry["class"],
                        prerequisites=json.dumps(entry.get("prerequisites", [])),
                    )
                )
            with open(
                os.path.join(DATA_DIR, f"items_{subject}_6_8.json"), encoding="utf-8"
            ) as f:
                items = json.load(f)["items"]
            for it in items:
                session.add(
                    models.Item(
                        id=it["id"],
                        skill_id=it["skill_id"],
                        question=it["question"],
                        options=json.dumps(it.get("options", [])),
                        answer=it.get("answer", ""),
                        explanation=it.get("explanation"),
                        is_test=it.get("test", False),
                    )
                )
        session.flush()

    if session.query(models.SchoolClass).first() is None:
        demo = [
            ("6A", 6, ["Aanya Verma", "Kabir Singh"]),
            ("7A", 7, ["Ira Desai", "Rohan Mehta"]),
            ("8A", 8, ["Sita Iyer", "Arjun Patel"]),
        ]
        for name, grade, student_names in demo:
            school_class = models.SchoolClass(name=name, grade=grade)
            session.add(school_class)
            session.flush()
            for student_name in student_names:
                session.add(models.Student(name=student_name, class_id=school_class.id))
    session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    for subject, filename in GRAPH_FILES.items():
        skill_graphs[subject] = SkillGraph.from_file(os.path.join(DATA_DIR, filename))
    for subject, filename in CONCEPT_FILES.items():
        with open(os.path.join(DATA_DIR, filename), encoding="utf-8") as f:
            concepts[subject] = json.load(f)
    init_db()
    with SessionLocal() as session:
        _seed(session)
    app.state.skill_graphs = skill_graphs
    app.state.concepts = concepts
    yield


app = FastAPI(
    title="Gati — Adaptive Learning Prototype (Phase 1)",
    description="Adaptive learning for Maths and Science, Classes 6 to 8",
    lifespan=lifespan,
)

app.include_router(attempts.router, prefix="/api")
app.include_router(students.router, prefix="/api")
app.include_router(classes_router.router, prefix="/api")
app.include_router(skills.router, prefix="/api")
app.include_router(items.router, prefix="/api")
app.include_router(tests.router, prefix="/api")

# Serve the student web app (plain HTML/CSS/JS) from /web. API routes above take
# precedence; everything else falls back to the static files.
app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")