"""Pick a practice item the student has not answered yet in a skill."""
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

import app.db as database
from app import models

router = APIRouter()


@router.get("/items/next")
def next_item(
    student_id: int = Query(..., description="student id"),
    skill_id: str = Query(None, description="skill id (defaults to the student's current skill)"),
    test: bool = Query(False, description="if true, return a test item instead of a practice item"),
    session: Session = Depends(database.get_db),
):
    student = session.get(models.Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="student not found")

    if skill_id is None:
        skill_id = student.current_skill_id
    if skill_id is None:
        raise HTTPException(status_code=400, detail="no skill selected")

    skill = session.get(models.Skill, skill_id)
    if skill is None:
        raise HTTPException(status_code=404, detail="skill not found")

    items = session.query(models.Item).filter_by(skill_id=skill_id, is_test=test).all()
    if not items:
        raise HTTPException(status_code=404, detail="no items for this skill")

    attempted = {
        a.item_id
        for a in session.query(models.Attempt)
        .join(models.Item, models.Attempt.item_id == models.Item.id)
        .filter(models.Attempt.student_id == student_id, models.Item.skill_id == skill_id, models.Item.is_test == test)
        .all()
    }

    remaining = [i for i in items if i.id not in attempted]
    item = remaining[0] if remaining else items[0]  # fallback: reuse an item

    return {
        "id": item.id,
        "skill_id": item.skill_id,
        "question": item.question,
        "options": json.loads(item.options or "[]"),
        # The correct answer and explanation are intentionally withheld from the browser.
    }