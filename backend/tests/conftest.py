# tests/conftest.py
# Shared test setup. Tests use an in-memory SQLite database, so they need
# no PostgreSQL, no Redis and no OpenAI key: they run anywhere, including CI.

import os

# Set test settings BEFORE the app is imported, so tests never touch a real
# database, Redis or OpenAI, even if your .env has values for them.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-secret-key-that-is-at-least-32-bytes-long"
os.environ["REDIS_URL"] = ""
os.environ["OPENAI_API_KEY"] = ""

# Imports come AFTER the lines above on purpose
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Question, User
from app.security import hash_password

# StaticPool = every session shares ONE in-memory database
engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


# Every route that asks for get_db now gets the test database instead
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def fresh_db():
    """Empty tables before every test, so tests never affect each other."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def db():
    with TestingSession() as session:
        yield session


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def question(db):
    q = Question(text="2 + 2 = ?", option_a="3", option_b="4", option_c="5", option_d="22",
                 answer="B", concept="Arithmetic", difficulty=1)
    db.add(q)
    db.commit()
    return q


def make_user(db, email, role="student", password="password123"):
    db.add(User(name=email.split("@")[0], email=email, password_hash=hash_password(password), role=role))
    db.commit()


def login(client, email, password="password123") -> dict:
    """Log in and return the Authorization header for later requests."""
    r = client.post("/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def student_headers(client, db):
    make_user(db, "student@test.com")
    return login(client, "student@test.com")


@pytest.fixture
def tutor_headers(client, db):
    make_user(db, "tutor@test.com", role="tutor")
    return login(client, "tutor@test.com")
