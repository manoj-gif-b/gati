"""Student views: list, skill map, and next step."""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

import app.db as database
from app import models
from app.engine import bkt, next_step as next_step_mod

router = APIRouter()


@router.get("/students")
def list_students(session: Session = Depends(database.get_db)):
    students = session.query(models.Student).order_by(models.Student.name).all()
    return [
        {
            "student_id": s.id,
            "name": s.name,
            "class": s.class_.name,
            "grade": s.class_.grade,
        }
        for s in students
    ]


@router.get("/students/{student_id}/map")
def student_map(student_id: int, session: Session = Depends(database.get_db)):
    student = session.get(models.Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="student not found")

    rows = {
        m.skill_id: m.p_known
        for m in session.query(models.StudentSkillMastery)
        .filter_by(student_id=student.id)
        .all()
    }
    skills = (
        session.query(models.Skill)
        .order_by(models.Skill.subject, models.Skill.class_grade, models.Skill.id)
        .all()
    )
    return {
        "student_id": student.id,
        "name": student.name,
        "class": student.class_.name,
        "skills": [
            {
                "skill_id": s.id,
                "name": s.name,
                "subject": s.subject,
                "grade": s.class_grade,
                "mastery": round(rows.get(s.id, bkt.initial_mastery()), 4),
            }
            for s in skills
        ],
    }


@router.get("/students/{student_id}/next")
def student_next(
    request: Request,
    student_id: int,
    subject: str = Query(..., description="maths or science"),
    session: Session = Depends(database.get_db),
):
    """Return the adaptive next step for a student in a subject.

    Uses the Phase 1 rule engine (revisit basics / new concept / practice).
    """
    student = session.get(models.Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="student not found")

    graph = request.app.state.skill_graphs.get(subject)
    if graph is None:
        raise HTTPException(status_code=400, detail="unknown subject")

    skills = session.query(models.Skill).filter_by(subject=subject).all()
    if not skills:
        raise HTTPException(status_code=404, detail="no skills for this subject")

    initial = bkt.initial_mastery()

    rows = {
        m.skill_id: m.p_known
        for m in session.query(models.StudentSkillMastery)
        .filter_by(student_id=student.id)
        .all()
    }
    # Unseen skills start at the BKT prior so reasons show accurate mastery.
    for s in skills:
        rows.setdefault(s.id, initial)

    # Current skill: the student's tracked skill, else the weakest unmastered
    # skill in this subject (fall back to the weakest skill overall).
    current = None
    if student.current_skill_id:
        candidate = session.get(models.Skill, student.current_skill_id)
        if candidate is not None and candidate.subject == subject:
            current = candidate
    if current is None:
        weak = [s for s in skills if rows.get(s.id, initial) < next_step_mod.MASTERED]
        if weak:
            current = min(weak, key=lambda s: rows.get(s.id, initial))
        else:
            current = min(skills, key=lambda s: rows.get(s.id, initial))

    step = next_step_mod.next_step(current.id, rows, graph)
    target = graph.get(step["skill_id"])

    student.current_skill_id = target.id
    session.add(student)
    session.commit()

    return {
        "action": step["action"],
        "skill_id": target.id,
        "name": target.name,
        "subject": target.subject,
        "grade": target.grade,
        "mastery": round(rows.get(target.id, initial), 4),
        "reason": step["reason"],
    }