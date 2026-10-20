# tests/test_auth.py


def test_register_creates_student(client):
    r = client.post("/auth/register", json={"name": "Asha", "email": "Asha@Test.com", "password": "password123"})
    assert r.status_code == 201
    body = r.json()
    assert body["role"] == "student"            # public sign-up can never create a tutor
    assert body["email"] == "asha@test.com"     # emails are stored in lowercase
    assert "password" not in body and "password_hash" not in body


def test_duplicate_email_is_rejected(client):
    data = {"name": "Asha", "email": "asha@test.com", "password": "password123"}
    client.post("/auth/register", json=data)
    assert client.post("/auth/register", json=data).status_code == 409


def test_short_password_is_rejected(client):
    r = client.post("/auth/register", json={"name": "Asha", "email": "a@test.com", "password": "short"})
    assert r.status_code == 422   # Pydantic validation error


def test_login_and_me(client):
    client.post("/auth/register", json={"name": "Asha", "email": "asha@test.com", "password": "password123"})
    r = client.post("/auth/login", data={"username": "asha@test.com", "password": "password123"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["email"] == "asha@test.com"


def test_wrong_password_and_missing_token(client):
    client.post("/auth/register", json={"name": "Asha", "email": "asha@test.com", "password": "password123"})
    r = client.post("/auth/login", data={"username": "asha@test.com", "password": "wrongpass1"})
    assert r.status_code == 401
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer not-a-token"}).status_code == 401
