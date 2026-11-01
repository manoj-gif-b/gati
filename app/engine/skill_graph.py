"""Loads and queries the prerequisite skill graph."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class Skill:
    id: str
    name: str
    subject: str
    grade: int
    prerequisites: List[str]


class SkillGraph:
    """A subject's prerequisite graph: skills plus the 'requires' edges."""

    def __init__(self, skills: List[Skill]):
        self._skills: Dict[str, Skill] = {s.id: s for s in skills}
        # Reverse edges: skill id -> ids of skills that require it
        self._children: Dict[str, List[str]] = {s.id: [] for s in skills}
        for s in skills:
            for p in s.prerequisites:
                self._children.setdefault(p, []).append(s.id)

    @classmethod
    def from_file(cls, path: str) -> "SkillGraph":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # The JSON uses "class" for the class/grade number; map it to `grade`.
        skills = [
            Skill(
                id=entry["id"],
                name=entry["name"],
                subject=entry["subject"],
                grade=entry["class"],
                prerequisites=entry.get("prerequisites", []),
            )
            for entry in data["skills"]
        ]
        return cls(skills)

    def get(self, skill_id: str) -> Optional[Skill]:
        return self._skills.get(skill_id)

    def prerequisites(self, skill_id: str) -> List[Skill]:
        """Return the prerequisite skills of a skill (empty list if unknown)."""
        skill = self.get(skill_id)
        if skill is None:
            return []
        return [self._skills[p] for p in skill.prerequisites if p in self._skills]

    def all_skills(self) -> List[Skill]:
        return list(self._skills.values())

    def skills_for(self, subject: str, grade: Optional[int] = None) -> List[Skill]:
        result = [s for s in self._skills.values() if s.subject == subject]
        if grade is not None:
            result = [s for s in result if s.grade == grade]
        return sorted(result, key=lambda s: s.id)