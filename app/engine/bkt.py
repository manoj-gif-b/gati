"""Bayesian Knowledge Tracing (BKT) for a single skill.

Tracks P(student knows the skill) given a sequence of correct/incorrect answers.

Parameters
----------
p_init : float
    P(knows) before any observation of this skill.
p_transit : float
    P(learns the skill between two opportunities), i.e. P(L_{t+1} | not L_t).
p_slip : float
    P(wrong answer | knows the skill).
p_guess : float
    P(correct answer | does not know the skill).

Formulas
--------
Let p = P(L_t) be the current mastery and o the observed answer.

Posterior after observing o (Bayes rule):

    P(L_t | o) = P(o | L_t) * p / (P(o | L_t) * p + P(o | not L_t) * (1 - p))

    correct:  P(correct  | L_t)   = 1 - p_slip,  P(correct  | not L_t) = p_guess
    wrong:    P(wrong    | L_t)   = p_slip,      P(wrong    | not L_t)  = 1 - p_guess

Then allow learning before the next opportunity:

    P(L_{t+1}) = P(L_t | o) + (1 - P(L_t | o)) * p_transit

All results are clamped to [0, 1].
"""
from __future__ import annotations

DEFAULT_P_INIT = 0.30
DEFAULT_P_TRANSIT = 0.20
DEFAULT_P_SLIP = 0.10
DEFAULT_P_GUESS = 0.20


def clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def initial_mastery(p_init: float = DEFAULT_P_INIT) -> float:
    """Mastery before any observation of a skill."""
    return clamp(p_init)


def update(
    p_known: float,
    correct: bool,
    *,
    p_transit: float = DEFAULT_P_TRANSIT,
    p_slip: float = DEFAULT_P_SLIP,
    p_guess: float = DEFAULT_P_GUESS,
) -> float:
    """Return the updated P(knows) after one observed answer.

    p_known : current mastery in [0, 1]
    correct : whether the learner answered correctly
    """
    p = clamp(p_known)

    if correct:
        p_lik_know = 1.0 - p_slip   # P(correct | knows)
        p_lik_not = p_guess         # P(correct | does not know)
    else:
        p_lik_know = p_slip         # P(wrong | knows)
        p_lik_not = 1.0 - p_guess   # P(wrong | does not know)

    numerator = p_lik_know * p
    denominator = numerator + p_lik_not * (1.0 - p)
    posterior = numerator / denominator if denominator > 0 else p

    # A student who does not know the skill yet may still acquire it before
    # the next opportunity (p_transit).
    updated = posterior + (1.0 - posterior) * p_transit
    return clamp(updated)