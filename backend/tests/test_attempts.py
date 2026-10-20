# tests/test_attempts.py
from app.services.gap import next_score


def test_gap_score_moves_the_right_way():
    assert next_score(0.5, is_correct=False) > 0.5
    assert next_score(0.5, is_correct=True) < 0.5
    score = 0.5
    for _ in range(50):              # many wrong answers in a row
        score = next_score(score, False)
    assert 0.99 < score <= 1.0       # approaches 1, never goes past it


def test_question_hides_the_answer(client, student_headers, question):
    r = client.get("/questions/next", params={"concept": "Arithmetic"}, headers=student_headers)
    assert r.status_code == 200
    assert "answer" not in r.json()


def test_correct_answer(client, student_headers, question):
    r = client.post("/attempts", json={"question_id": question.id, "selected": "B"}, headers=student_headers)
    assert r.status_code == 201
    body = r.json()
    assert body["is_correct"] is True
    assert body["hint"] is None and body["correct_answer"] is None
    assert body["gap_score"] < 0.5


def test_wrong_answer_gets_fallback_hint(client, student_headers, question):
    r = client.post("/attempts", json={"question_id": question.id, "selected": "A"}, headers=student_headers)
    body = r.json()
    assert body["is_correct"] is False
    assert body["correct_answer"] == "B"
    assert body["hint_source"] == "fallback"     # no OpenAI key in tests
    assert body["gap_score"] > 0.5


def test_gaps_endpoint(client, student_headers, question):
    client.post("/attempts", json={"question_id": question.id, "selected": "A"}, headers=student_headers)
    gaps = client.get("/analytics/me/gaps", headers=student_headers).json()
    assert gaps[0]["concept"] == "Arithmetic" and gaps[0]["attempts"] == 1


def test_invalid_option_and_unknown_question(client, student_headers, question):
    assert client.post("/attempts", json={"question_id": question.id, "selected": "E"},
                       headers=student_headers).status_code == 422
    assert client.post("/attempts", json={"question_id": 999, "selected": "A"},
                       headers=student_headers).status_code == 404
