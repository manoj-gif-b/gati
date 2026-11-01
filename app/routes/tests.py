"""Submit a 3-question mastery test for a skill."""
import json
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

import app.db as database
from app import models
from app.engine import bkt, next_step as next_step_mod
from app.engine.next_step import MASTERED, WEAK
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

import app.db as database
from app import models
from app.engine import bkt, next_step as next_step_mod
from app.engine.next_step import MASTERED, WEAK

router = APIRouter()


@router.get("/tests/{skill_id}/items")
def get_test_items(
    skill_id: str,
    student_id: int = Query(..., description="student id"),
    session: Session = Depends(database.get_db),
):
    """Return the 3 test items for a skill (without answers or explanations)."""
    skill = session.get(models.Skill, skill_id)
    if skill is None:
        raise HTTPException(status_code=404, detail="skill not found")

    items = session.query(models.Item).filter_by(skill_id=skill_id, is_test=True).all()
    if not items:
        raise HTTPException(status_code=404, detail="no test items for this skill")

    return [
        {
            "id": item.id,
            "skill_id": item.skill_id,
            "question": item.question,
            "options": json.loads(item.options or "[]"),
        }
        for item in items
    ]

# A test pass requires at least 2 of 3 correct.
TEST_PASS_THRESHOLD = 2
TEST_TOTAL = 3
# On test failure, mastery is reset to this value (toward WEAK = 0.40).
# This gives the student a second chance to relearn before being retested.
FAILED_TEST_MASTERY = 0.6


class TestAnswer(BaseModel):
    item_id: str
    answer: str


class TestSubmitIn(BaseModel):
    student_id: int
    answers: list[TestAnswer] = Field(..., min_length=TEST_TOTAL, max_length=TEST_TOTAL)


class TestSubmitOut(BaseModel):
    skill_id: str
    passed: bool
    score: int  # number correct out of 3
    mastery: float
    next_step: dict


@router.post("/tests/{skill_id}/submit", response_model=TestSubmitOut)
def submit_test(
    skill_id: str,
    payload: TestSubmitIn,
    request: Request,
    session: Session = Depends(database.get_db),
):
    student = session.get(models.Student, payload.student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="student not found")

    skill = session.get(models.Skill, skill_id)
    if skill is None:
        raise HTTPException(status_code=404, detail="skill not found")

    # Verify all answers belong to this skill and are test items.
    item_map = {}
    for it in session.query(models.Item).filter_by(skill_id=skill_id, is_test=True).all():
        item_map[it.id] = it

    correct_count = 0
    for ans in payload.answers:
        item = item_map.get(ans.item_id)
        if item is None:
            raise HTTPException(status_code=400, detail=f"item {ans.item_id} is not a test item for this skill")
        if ans.answer.strip().lower() == item.answer.strip().lower():
            correct_count += 1
        # Record every test answer as an Attempt with is_test=True.
        session.add(
            models.Attempt(
                student_id=student.id,
                item_id=item.id,
                correct=(ans.answer.strip().lower() == item.answer.strip().lower()),
                time_taken_s=0.0,
                is_test=True,
            )
        )

    passed = correct_count >= TEST_PASS_THRESHOLD

    row = (
        session.query(models.StudentSkillMastery)
        .filter_by(student_id=student.id, skill_id=skill.id)
        .first()
    )
    if row is None:
        session.add(
            models.StudentSkillMastery(
                student_id=student.id, skill_id=skill.id, p_known=0.30
            )
        )
        session.flush()
        row = session.query(models.StudentSkillMastery).filter_by(
            student_id=student.id, skill_id=skill.id
        ).first()

    if passed:
        row.confirmed_mastered = True
        # Mastery stays at its current (already high) value.
    else:
        row.confirmed_mastered = False
        row.p_known = FAILED_TEST_MASTERY

    student.current_skill_id = skill.id
    session.add(student)
    session.commit()

    mastery_map = {
        m.skill_id: m.p_known
        for m in session.query(models.StudentSkillMastery)
        .filter_by(student_id=student.id)
        .all()
    }
    graph = request.app.state.skill_graphs.get(skill.subject)

    if passed:
        step = next_step_mod.next_step(skill.id, mastery_map, graph)
    else:
        # On fail: show the revisit_basics reason for this skill itself.
        step = {
            "action": "revisit_basics",
            "skill_id": skill.id,
            "reason": (
                f"You got {correct_count} of {TEST_TOTAL} right on the '{skill.name}' check, "
                f"so let's review the basics before trying again."
            ),
        }

    return TestSubmitOut(
        skill_id=skill.id,
        passed=passed,
        score=correct_count,
        mastery=round(row.p_known, 4),
        next_step=step,
    )