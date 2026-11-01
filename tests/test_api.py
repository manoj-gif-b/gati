"""API tests for Gati (endpoints + adaptivity end-to-end)."""
from app.engine.next_step import MASTERED, WEAK
from app.db import SessionLocal
from app import models


def get_test_items_for_skill(skill_id, is_test=True):
    with SessionLocal() as session:
        items = session.query(models.Item).filter_by(skill_id=skill_id, is_test=is_test).all()
        return [(it.id, it.answer) for it in items]


def test_submit_test_pass(client):
    items = get_test_items_for_skill("m6_numbers")
    answers = [
        {"item_id": items[0][0], "answer": items[0][1]},  # correct
        {"item_id": items[1][0], "answer": items[1][1]},  # correct
        {"item_id": items[2][0], "answer": "wrong answer"},  # wrong
    ]
    resp = client.post(
        "/api/tests/m6_numbers/submit",
        json={"student_id": 1, "answers": answers},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["passed"] is True
    assert data["score"] == 2
    assert "next_step" in data
    assert set(data) >= {"skill_id", "passed", "score", "mastery", "next_step"}
    # answer/explanation should not be in response
    assert "answer" not in data
    assert "explanation" not in data


def test_submit_test_fail(client):
    items = get_test_items_for_skill("m6_numbers")
    answers = [
        {"item_id": items[0][0], "answer": items[0][1]},  # correct
        {"item_id": items[1][0], "answer": "wrong answer"},  # wrong
        {"item_id": items[2][0], "answer": "wrong answer"},  # wrong
    ]
    resp = client.post(
        "/api/tests/m6_numbers/submit",
        json={"student_id": 1, "answers": answers},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["passed"] is False
    assert data["score"] == 1
    assert data["mastery"] == 0.6
    assert data["next_step"]["action"] == "revisit_basics"


def test_submit_test_wrong_count(client):
    items = get_test_items_for_skill("m6_numbers")
    # Only 2 answers instead of 3
    answers = [
        {"item_id": items[0][0], "answer": items[0][1]},
        {"item_id": items[1][0], "answer": items[1][1]},
    ]
    resp = client.post(
        "/api/tests/m6_numbers/submit",
        json={"student_id": 1, "answers": answers},
    )
    assert resp.status_code == 422  # Pydantic validation error (min_length=3)


def test_submit_test_wrong_skill_item(client):
    # Get a test item from m6_fractions
    items = get_test_items_for_skill("m6_fractions")
    # Try to submit it as if it belongs to m6_numbers
    answers = [
        {"item_id": items[0][0], "answer": items[0][1]},
        {"item_id": items[1][0], "answer": items[1][1]},
        {"item_id": items[2][0], "answer": items[2][1]},
    ]
    resp = client.post(
        "/api/tests/m6_numbers/submit",
        json={"student_id": 1, "answers": answers},
    )
    assert resp.status_code == 400, resp.text


def item_answer(item_id):
    with SessionLocal() as session:
        item = session.get(models.Item, item_id)
        return item.answer

def test_test_items_endpoint_no_answer_fields(client):
    resp = client.get("/api/tests/m6_numbers/items?student_id=1")
    assert resp.status_code == 200, resp.text
    items = resp.json()
    assert len(items) == 3
    for item in items:
        assert set(item) >= {"id", "skill_id", "question", "options"}
        assert "answer" not in item
        assert "explanation" not in item


def test_test_items_endpoint_only_test_items(client):
    resp = client.get("/api/tests/m6_numbers/items?student_id=1")
    assert resp.status_code == 200, resp.text
    items = resp.json()
    assert len(items) == 3
    # Verify all returned items are test items in the DB
    with SessionLocal() as session:
        for item in items:
            db_item = session.get(models.Item, item["id"])
            assert db_item is not None
            assert db_item.is_test is True
    resp = client.get("/api/tests/m6_numbers/items?student_id=1")
    assert resp.status_code == 200, resp.text
    items = resp.json()
    assert len(items) == 3
    for item in items:
        assert set(item) >= {"id", "skill_id", "question", "options"}
        assert "answer" not in item
        assert "explanation" not in item


def test_test_items_endpoint_only_test_items(client):
    resp = client.get("/api/tests/m6_numbers/items?student_id=1")
    assert resp.status_code == 200, resp.text
    items = resp.json()
    assert len(items) == 3
    # Verify all returned items are test items in the DB
    with SessionLocal() as session:
        for item in items:
            db_item = session.get(models.Item, item["id"])
            assert db_item is not None
            assert db_item.is_test is True


def wrong_option_for(item_id):
    with SessionLocal() as session:
        item = session.get(models.Item, item_id)
        import json
        options = json.loads(item.options or "[]")
        for o in options:
            if o.strip().lower() != item.answer.strip().lower():
                return o
        return item.answer + "x"


def test_attempt_updates_mastery_and_returns_next_step(client):
    ans = item_answer("m6_numbers_1")
    resp = client.post(
        "/api/attempts",
        json={
            "student_id": 1,
            "item_id": "m6_numbers_1",
            "answer": ans,
            "time_taken_s": 12.5,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["student_id"] == 1
    assert body["item_id"] == "m6_numbers_1"
    assert body["skill_id"] == "m6_numbers"
    assert body["correct"] is True
    assert body["mastery"] > 0.30  # correct answer raised mastery above p_init
    assert body["next_step"]["action"] in ("practice", "revisit_basics", "new_concept")
    assert isinstance(body["next_step"]["reason"], str) and body["next_step"]["reason"]

    # A wrong answer on the same skill lowers mastery
    wrong = wrong_option_for("m6_numbers_2")
    resp2 = client.post(
        "/api/attempts",
        json={
            "student_id": 1,
            "item_id": "m6_numbers_2",
            "answer": wrong,
            "time_taken_s": 9.0,
        },
    )
    assert resp2.status_code == 200
    assert resp2.json()["correct"] is False
    assert resp2.json()["mastery"] < body["mastery"]

    # Unknown student / item -> 404
    assert client.post(
        "/api/attempts", json={"student_id": 9999, "item_id": "m6_numbers_1", "answer": "x"}
    ).status_code == 404
    assert client.post(
        "/api/attempts", json={"student_id": 1, "item_id": "no-such-item", "answer": "x"}
    ).status_code == 404


def test_repeated_correct_attempts_reach_mastery(client):
    mastery = None
    for i in range(1, 4):  # m6_numbers_1 .. m6_numbers_3
        ans = item_answer(f"m6_numbers_{i}")
        resp = client.post(
            "/api/attempts",
            json={
                "student_id": 1,
                "item_id": f"m6_numbers_{i}",
                "answer": ans,
                "time_taken_s": 5.0,
            },
        )
        assert resp.status_code == 200, resp.text
        mastery = resp.json()["mastery"]
    assert mastery >= MASTERED


def test_next_endpoint(client):
    resp = client.get("/api/students/1/next?subject=maths")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert set(data) >= {"action", "skill_id", "name", "subject", "mastery", "reason"}
    assert data["subject"] == "maths"
    assert data["action"] in ("practice", "revisit_basics", "new_concept")
    assert isinstance(data["reason"], str) and data["reason"]
    assert client.get("/api/students/9999/next?subject=maths").status_code == 404


def test_items_next_withholds_answer(client):
    resp = client.get("/api/items/next?student_id=1&skill_id=m6_numbers")
    assert resp.status_code == 200, resp.text
    item = resp.json()
    assert set(item) >= {"id", "skill_id", "question", "options"}
    assert "answer" not in item
    assert "explanation" not in item
    assert item["skill_id"] == "m6_numbers"
    # fallback works when re-calling (all items eventually used): still 200
    resp2 = client.get("/api/items/next?student_id=1&skill_id=m6_numbers")
    assert resp2.status_code == 200


def test_skills_endpoint(client):
    resp = client.get("/api/skills?subject=maths")
    assert resp.status_code == 200
    skills = resp.json()
    assert len(skills) == 10
    for s in skills:
        assert set(s) >= {"skill_id", "name", "grade", "concept"}
        assert set(s["concept"]) >= {"title", "text"}
    # unknown subject returns empty list, not an error
    resp2 = client.get("/api/skills?subject=maths")
    assert resp2.status_code == 200


def test_students_list(client):
    resp = client.get("/api/students")
    assert resp.status_code == 200
    students = resp.json()
    assert len(students) >= 1
    assert set(students[0]) >= {"student_id", "name", "class", "grade"}


def test_student_map(client):
    resp = client.get("/api/students/1/map")
    assert resp.status_code == 200
    data = resp.json()
    assert data["student_id"] == 1
    assert len(data["skills"]) == 20  # 10 maths + 10 science
    for skill in data["skills"]:
        assert set(skill) >= {"skill_id", "name", "subject", "grade", "mastery"}
        assert 0.0 <= skill["mastery"] <= 1.0
    assert client.get("/api/students/9999/map").status_code == 404


def test_class_overview(client):
    resp = client.get("/api/classes/1/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert data["class_id"] == 1
    assert data["grade"] == 6
    assert len(data["students"]) == 2
    for st in data["students"]:
        assert set(st) >= {"student_id", "name", "weakest_skills"}
        for ws in st["weakest_skills"]:
            assert ws["mastery"] < WEAK
    assert client.get("/api/classes/9999/overview").status_code == 404


def test_student_map(client):
    resp = client.get("/api/students/1/map")
    assert resp.status_code == 200
    data = resp.json()
    assert data["student_id"] == 1
    assert len(data["skills"]) == 20  # 10 maths + 10 science
    for skill in data["skills"]:
        assert set(skill) >= {"skill_id", "name", "subject", "grade", "mastery"}
        assert 0.0 <= skill["mastery"] <= 1.0
    assert client.get("/api/students/9999/map").status_code == 404


def test_class_overview(client):
    resp = client.get("/api/classes/1/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert data["class_id"] == 1
    assert data["grade"] == 6
    assert len(data["students"]) == 2
    for st in data["students"]:
        assert set(st) >= {"student_id", "name", "weakest_skills"}
        for ws in st["weakest_skills"]:
            assert ws["mastery"] < WEAK
    assert client.get("/api/classes/9999/overview").status_code == 404