"""Skills list with concept cards, keyed by subject."""
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

import app.db as database
from app import models

router = APIRouter()


@router.get("/skills")
def list_skills(
    request: Request,
    subject: str = Query(..., description="maths or science"),
    session: Session = Depends(database.get_db),
):
    concepts = getattr(request.app.state, "concepts", {}).get(subject, {})
    skills = (
        session.query(models.Skill)
        .filter_by(subject=subject)
        .order_by(models.Skill.class_grade, models.Skill.id)
        .all()
    )
    return [
        {
            "skill_id": s.id,
            "name": s.name,
            "subject": s.subject,
            "grade": s.class_grade,
            "prerequisites": s.prerequisites,
            "concept": concepts.get(s.id, {"title": s.name, "text": ""}),
        }
        for s in skills
    ]