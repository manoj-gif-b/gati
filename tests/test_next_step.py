"""Unit tests for the adaptivity rules (app/engine/next_step.py)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.engine.next_step import MASTERED, WEAK, next_step
from app.engine.skill_graph import SkillGraph

GRAPH = SkillGraph.from_file(os.path.join("data", "skill_graph_maths_6_8.json"))


def full_mastery(**overrides):
    mastery = {skill.id: 0.30 for skill in GRAPH.all_skills()}
    mastery.update(overrides)
    return mastery


def test_weak_prerequisite_returns_revisit_basics():
    m = full_mastery(m6_numbers=0.20, m6_fractions=0.50)
    step = next_step("m6_fractions", m, GRAPH)
    assert step["action"] == "revisit_basics"
    assert step["skill_id"] == "m6_numbers"
    assert isinstance(step["reason"], str) and step["reason"]


def test_mastered_skill_returns_new_concept():
    m = full_mastery(m6_numbers=0.98)
    step = next_step("m6_numbers", m, GRAPH)
    assert step["action"] == "new_concept"
    # Direct children of m6_numbers with all prerequisites mastered, ordered
    # by (grade, id): m6_algebra comes first.
    assert step["skill_id"] == "m6_algebra"
    assert isinstance(step["reason"], str) and step["reason"]


def test_all_prerequisites_must_be_mastered():
    # m8_data needs m7_ratio mastered; m7_ratio needs m6_fractions mastered.
    m = full_mastery(m7_ratio=0.98, m6_fractions=0.30)
    step = next_step("m7_ratio", m, GRAPH)
    assert step["action"] == "revisit_basics"
    assert step["skill_id"] == "m6_fractions"


def test_weak_current_but_strong_prereqs_returns_practice():
    m = full_mastery(m6_fractions=0.50, m6_numbers=0.90)
    step = next_step("m6_fractions", m, GRAPH)
    assert step["action"] == "practice"
    assert step["skill_id"] == "m6_fractions"
    assert isinstance(step["reason"], str) and step["reason"]


def test_everything_mastered_returns_practice_without_new_concept():
    m = {skill.id: 0.99 for skill in GRAPH.all_skills()}
    step = next_step("m6_numbers", m, GRAPH)
    assert step["action"] == "practice"
    assert isinstance(step["reason"], str) and step["reason"]