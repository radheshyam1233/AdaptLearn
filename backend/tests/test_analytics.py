# tests/test_analytics.py
# Role checks (RBAC) and the tutor's numbers.

NEW_Q = {"text": "Capital of India?", "option_a": "Mumbai", "option_b": "New Delhi",
         "option_c": "Kolkata", "option_d": "Chennai", "answer": "B", "concept": "GK"}


def test_only_tutors_can_add_questions(client, student_headers, tutor_headers):
    assert client.post("/questions", json=NEW_Q, headers=student_headers).status_code == 403
    assert client.post("/questions", json=NEW_Q, headers=tutor_headers).status_code == 201


def test_students_cannot_see_tutor_dashboard(client, student_headers):
    assert client.get("/analytics/dashboard", headers=student_headers).status_code == 403


def test_dashboard_and_heatmap(client, student_headers, tutor_headers, question):
    for choice in ["A", "A", "B"]:
        client.post("/attempts", json={"question_id": question.id, "selected": choice}, headers=student_headers)
    stats = client.get("/analytics/dashboard", headers=tutor_headers).json()
    assert stats["attempts_24h"] == 3
    assert stats["accuracy_24h"] == 33.3
    heat = client.get("/analytics/concepts", headers=tutor_headers).json()
    assert heat[0]["concept"] == "Arithmetic" and heat[0]["error_rate"] == 66.7
