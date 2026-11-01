"""Adaptivity rules: pick the next learning step for a student on a skill."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# Rule thresholds. Teachers read the reasons, so they are kept in plain English.
MASTERED = 0.95   # p_known >= MASTERED  => the skill is considered learned
WEAK = 0.40       # p_known < WEAK      => the skill needs a revisit


def next_step(
    skill_id: str,
    mastery: Dict[str, float],
    skill_graph: Any,
) -> Dict[str, Any]:
    """Decide what the student should do next on ``skill_id``.

    Parameters
    ----------
    skill_id : the skill the student is currently working on
    mastery : mapping of skill id -> current P(knows)
    skill_graph : loaded SkillGraph used to look up prerequisites

    Returns a dict with keys: action, skill_id, reason.
    """
    skill = skill_graph.get(skill_id)
    if skill is None:
        return {
            "action": "practice",
            "skill_id": skill_id,
            "reason": f"Unknown skill '{skill_id}'; continuing practice.",
        }

    # Rule 1: if any prerequisite is weak, revisit basics first.
    for prereq in skill_graph.prerequisites(skill_id):
        p = mastery.get(prereq.id, 0.0)
        if p < WEAK:
            return {
                "action": "revisit_basics",
                "skill_id": prereq.id,
                "reason": (
                    f"Strengthen '{prereq.name}' first (mastery {p:.0%}) "
                    f"before continuing with '{skill.name}'."
                ),
            }

    current_p = mastery.get(skill_id, 0.0)

    # Rule 2: current skill mastered -> move to a new concept whose prerequisites
    # are all mastered. Prefer skills that build directly on the current one.
    if current_p >= MASTERED:
        nxt = _next_ready_skill(skill_id, mastery, skill_graph)
        if nxt is not None:
            return {
                "action": "new_concept",
                "skill_id": nxt.id,
                "reason": (
                    f"You've mastered '{skill.name}' ({current_p:.0%}). "
                    f"All prerequisites for '{nxt.name}' are solid — try it next."
                ),
            }
        return {
            "action": "practice",
            "skill_id": skill_id,
            "reason": (
                f"'{skill.name}' is mastered ({current_p:.0%}) and no new concept "
                f"is ready yet. Keep practicing."
            ),
        }

    # Rule 3: otherwise keep practicing the current skill.
    return {
        "action": "practice",
        "skill_id": skill_id,
        "reason": (
            f"Keep practicing '{skill.name}' (mastery {current_p:.0%}). "
            f"Not yet mastered, but the basics are in place."
        ),
    }


def _next_ready_skill(
    skill_id: str,
    mastery: Dict[str, float],
    skill_graph: Any,
) -> Optional[Any]:
    """First unmastered skill whose prerequisites are all MASTERED.

    Skills that directly require ``skill_id`` are preferred so the learner
    follows a natural progression through the graph.
    """
    ready: List[Any] = []
    for candidate in skill_graph.all_skills():
        if candidate.id == skill_id:
            continue
        if mastery.get(candidate.id, 0.0) >= MASTERED:
            continue
        if all(
            mastery.get(p.id, 0.0) >= MASTERED
            for p in skill_graph.prerequisites(candidate.id)
        ):
            ready.append(candidate)

    direct = [s for s in ready if skill_id in s.prerequisites]
    ready = direct or ready
    ready.sort(key=lambda s: (s.grade, s.id))
    return ready[0] if ready else None