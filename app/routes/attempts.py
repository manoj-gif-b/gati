"""Recording attempts and selecting the next step."""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

import app.db as database
from app import models
from app.engine import bkt, next_step as next_step_mod
from app.engine.next_step import MASTERED

router = APIRouter()


class AttemptIn(BaseModel):
    student_id: int
    item_id: str
    answer: str = Field(..., description="the option text the student selected")
    time_taken_s: float = Field(default=0.0, ge=0)


class AttemptOut(BaseModel):
    student_id: int
    item_id: str
    skill_id: str
    correct: bool
    mastery: float
    next_step: dict
    test_required: bool = False


def _next_step_for(session: Session, request: Request, student: models.Student, skill: models.Skill, mastery_map: dict):
    graph = request.app.state.skill_graphs.get(skill.subject)
    return next_step_mod.next_step(skill.id, mastery_map, graph)


@router.post("/attempts", response_model=AttemptOut)
def record_attempt(
    payload: AttemptIn, request: Request, session: Session = Depends(database.get_db)
):
    student = session.get(models.Student, payload.student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="student not found")
    item = session.get(models.Item, payload.item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="item not found")

    skill = item.skill

    # Server-side answer checking: the browser never sees the correct answer.
    correct = payload.answer.strip().lower() == item.answer.strip().lower()

    row = (
        session.query(models.StudentSkillMastery)
        .filter_by(student_id=student.id, skill_id=skill.id)
        .first()
    )
    p_known = row.p_known if row is not None else bkt.initial_mastery()
    row_confirmed = row.confirmed_mastered if row is not None else False
    new_p = bkt.update(p_known, correct)

    if row is None:
        session.add(
            models.StudentSkillMastery(
                student_id=student.id, skill_id=skill.id, p_known=new_p
            )
        )
    else:
        row.p_known = new_p

    session.add(
        models.Attempt(
            student_id=student.id,
            item_id=item.id,
            correct=correct,
            time_taken_s=payload.time_taken_s,
        )
    )

    # Track where the student is in the adaptive loop.
    student.current_skill_id = skill.id
    session.add(student)
    session.commit()

    mastery_map = {
        m.skill_id: m.p_known
        for m in session.query(models.StudentSkillMastery)
        .filter_by(student_id=student.id)
        .all()
    }
    # Unseen skills start at the BKT prior so reasons show accurate mastery.
    for s in session.query(models.Skill).filter_by(subject=skill.subject).all():
        mastery_map.setdefault(s.id, bkt.initial_mastery())
    step = _next_step_for(session, request, student, skill, mastery_map)

    # If mastery just crossed MASTERED, require a 3-question test check.
    test_required = new_p >= MASTERED and not row_confirmed

    return AttemptOut(
        student_id=student.id,
        item_id=item.id,
        skill_id=skill.id,
        correct=correct,
        mastery=round(new_p, 4),
        next_step=step,
        test_required=test_required,
    )