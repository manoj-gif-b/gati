"""Class overview for the teacher view."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import app.db as database
from app import models
from app.engine import bkt, next_step as next_step_mod

router = APIRouter()


@router.get("/classes/{class_id}/overview")
def class_overview(class_id: int, session: Session = Depends(database.get_db)):
    school_class = session.get(models.SchoolClass, class_id)
    if school_class is None:
        raise HTTPException(status_code=404, detail="class not found")

    students = (
        session.query(models.Student)
        .filter_by(class_id=class_id)
        .order_by(models.Student.name)
        .all()
    )

    result_students = []
    for student in students:
        rows = {
            m.skill_id: m.p_known
            for m in session.query(models.StudentSkillMastery)
            .filter_by(student_id=student.id)
            .all()
        }
        all_skills = session.query(models.Skill).all()
        weakest = [
            {
                "skill_id": s.id,
                "name": s.name,
                "subject": s.subject,
                "grade": s.class_grade,
                "mastery": round(rows.get(s.id, bkt.initial_mastery()), 4),
            }
            for s in all_skills
            if rows.get(s.id, bkt.initial_mastery()) < next_step_mod.WEAK
        ]
        weakest.sort(key=lambda s: s["mastery"])
        result_students.append(
            {"student_id": student.id, "name": student.name, "weakest_skills": weakest[:5]}
        )

    return {
        "class_id": school_class.id,
        "name": school_class.name,
        "grade": school_class.grade,
        "students": result_students,
    }