"""Unit tests for Bayesian Knowledge Tracing (app/engine/bkt.py)."""
from app.engine.bkt import update, initial_mastery


def test_correct_answer_raises_mastery():
    before = 0.50
    after = update(before, True)
    assert after > before
    assert 0.0 <= after <= 1.0


def test_wrong_answer_lowers_mastery():
    before = 0.50
    after = update(before, False)
    assert after < before
    assert 0.0 <= after <= 1.0


def test_repeated_correct_answers_converge_toward_one():
    p = 0.30
    for _ in range(20):
        p = update(p, True)
    assert p > 0.95


def test_repeated_wrong_answers_decrease_mastery():
    p = 0.80
    values = [p]
    for _ in range(10):
        p = update(p, False)
        values.append(p)
    assert all(values[i + 1] <= values[i] for i in range(len(values) - 1))
    assert values[-1] < values[0]


def test_values_stay_within_unit_interval_even_for_bad_inputs():
    for p in (-1.0, -0.5, 0.0, 1.0, 1.5, 2.0):
        for correct in (True, False):
            assert 0.0 <= update(p, correct) <= 1.0


def test_initial_mastery_is_in_unit_interval():
    assert 0.0 <= initial_mastery() <= 1.0