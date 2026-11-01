"""SQLAlchemy models for Gati."""
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db import Base


class SchoolClass(Base):
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)      # e.g. "6A"
    grade = Column(Integer, nullable=False)    # 6, 7 or 8

    students = relationship("Student", back_populates="class_", cascade="all, delete-orphan")


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False, index=True)
    current_skill_id = Column(String, ForeignKey("skills.id"), nullable=True, index=True)

    class_ = relationship("SchoolClass", back_populates="students")
    masteries = relationship("StudentSkillMastery", back_populates="student", cascade="all, delete-orphan")
    attempts = relationship("Attempt", back_populates="student", cascade="all, delete-orphan")
    current_skill = relationship("Skill", foreign_keys=[current_skill_id])


class Skill(Base):
    __tablename__ = "skills"

    id = Column(String, primary_key=True, index=True)    # e.g. "m6_numbers"
    name = Column(String, nullable=False)
    subject = Column(String, nullable=False)             # "maths" | "science"
    class_grade = Column(Integer, nullable=False)        # 6, 7 or 8
    prerequisites = Column(Text, nullable=False, default="[]")  # JSON list of skill ids

    masteries = relationship("StudentSkillMastery", back_populates="skill", cascade="all, delete-orphan")
    items = relationship("Item", back_populates="skill", cascade="all, delete-orphan")


class Item(Base):
    __tablename__ = "items"

    id = Column(String, primary_key=True, index=True)
    skill_id = Column(String, ForeignKey("skills.id"), nullable=False, index=True)
    question = Column(Text, nullable=False)
    options = Column(Text, nullable=False, default="[]")      # JSON list of option strings
    answer = Column(Text, nullable=False)                     # correct option text
    explanation = Column(Text, nullable=True)
    is_test = Column(Boolean, nullable=False, default=False)  # test items only, used for the 3-question check

    skill = relationship("Skill", back_populates="items")


class StudentSkillMastery(Base):
    __tablename__ = "student_skill_mastery"

    student_id = Column(Integer, ForeignKey("students.id"), primary_key=True, index=True)
    skill_id = Column(String, ForeignKey("skills.id"), primary_key=True, index=True)
    p_known = Column(Float, nullable=False, default=0.30)
    confirmed_mastered = Column(Boolean, nullable=False, default=False)  # set True after passing the 3-question check

    student = relationship("Student", back_populates="masteries")
    skill = relationship("Skill", back_populates="masteries")


class Attempt(Base):
    __tablename__ = "attempts"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    item_id = Column(String, ForeignKey("items.id"), nullable=False)
    correct = Column(Boolean, nullable=False)
    time_taken_s = Column(Float, nullable=False)
    is_test = Column(Boolean, nullable=False, default=False)  # True for attempts made during the 3-question check
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    student = relationship("Student", back_populates="attempts")