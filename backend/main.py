import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

import httpx
import jwt
from fastapi import Cookie, Depends, FastAPI, HTTPException, Response, WebSocket
from fastapi.concurrency import run_in_threadpool
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field
from pwdlib import PasswordHash
from pymongo import DESCENDING, MongoClient
from pymongo.errors import DuplicateKeyError, OperationFailure, PyMongoError, ServerSelectionTimeoutError
from redis.asyncio import Redis
from redis.exceptions import RedisError
from starlette.responses import JSONResponse

ROOT = Path(__file__).resolve().parents[1]
QUESTIONS = {item["id"]: item for item in json.loads((ROOT / "questions.json").read_text())}
TOPICS = list(dict.fromkeys(item["topic"] for item in QUESTIONS.values()))
PASSWORD = PasswordHash.recommended()
DUMMY_HASH = PASSWORD.hash("Dummy password used for uniform login timing")
COOKIE_NAME = "adaptlearn_session"
COOKIE_TTL = 8 * 60 * 60
LOG = logging.getLogger(__name__)
CACHE_KEY = "adaptlearn:dashboard:v1"


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)


class Registration(Credentials):
    role: Literal["student", "tutor"] = "student"
    invite_code: str = Field(default="", max_length=32)
    name: str = Field(min_length=2, max_length=60, pattern=r"^\S.*\S$")


class Answer(BaseModel):
    question_id: str
    choice: int = Field(ge=0, le=3)
    submission_id: UUID


@asynccontextmanager
async def lifespan(app):
    uri = os.getenv("MONGODB_URI")
    app.state.jwt_secret = os.getenv("JWT_SECRET", "")
    app.state.secure = os.getenv("COOKIE_SECURE", "true").lower() != "false"
    app.state.db = None
    app.state.last_database_problem = None
    app.state.indexed = False
    app.state.index_lock = asyncio.Lock()
    app.state.redis = Redis.from_url(os.environ["REDIS_URL"], decode_responses=True, socket_timeout=0.5,
                                    socket_connect_timeout=0.5) if os.getenv("REDIS_URL") else None
    app.state.http = httpx.AsyncClient(timeout=4)
    app.state.changed = asyncio.Condition()
    app.state.revision = 0
    app.state.cache_namespace = uuid4().hex
    client = MongoClient(uri, serverSelectionTimeoutMS=3500, connectTimeoutMS=3500,
                         socketTimeoutMS=5500) if uri else None
    if client is not None and len(app.state.jwt_secret) >= 32:
        app.state.db = client[os.getenv("MONGODB_DB", "adaptlearn")]
    if app.state.db is None:
        LOG.warning("Account storage unavailable: MongoDB URI missing or JWT secret shorter than 32 characters")
    try:
        yield
    finally:
        await app.state.http.aclose()
        if app.state.redis is not None:
            await app.state.redis.aclose()
        if client is not None:
            client.close()


app = FastAPI(title="AdaptLearn API", lifespan=lifespan, docs_url="/api/docs", openapi_url="/api/openapi.json")


@app.exception_handler(PyMongoError)
async def database_error(_request, _error):
    LOG.warning("MongoDB operation failed")
    return JSONResponse({"detail": "Atlas is temporarily unavailable. Try again shortly."}, status_code=503)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/status")
async def status():
    connected = False
    if app.state.db is not None:
        try:
            await run_in_threadpool(app.state.db.command, "ping")
            connected = True
        except PyMongoError as error:
            if isinstance(error, OperationFailure) and error.code in {13, 18, 8000}:
                problem = "database authentication or permission rejected"
            elif isinstance(error, ServerSelectionTimeoutError):
                problem = "no database server reachable before timeout"
            else:
                problem = type(error).__name__
            if problem != app.state.last_database_problem:
                LOG.warning("Account storage unavailable: %s", problem)
                app.state.last_database_problem = problem
        else:
            app.state.last_database_problem = None
    return {"accounts": connected}


async def database():
    db = app.state.db
    if db is None:
        raise HTTPException(503, "Accounts are temporarily unavailable.")
    if not app.state.indexed:
        async with app.state.index_lock:
            if not app.state.indexed:
                await run_in_threadpool(db.attempts.create_index, [("student_id", 1), ("created_at", DESCENDING)])
                await run_in_threadpool(db.attempts.create_index, [("created_at", DESCENDING)])
                await run_in_threadpool(db.attempts.create_index, [("classroom_id", 1), ("created_at", DESCENDING)])
                await run_in_threadpool(db.users.create_index, "invite_code", unique=True, sparse=True)
                app.state.indexed = True
    return db


def public_user(user):
    profile = {"name": user["name"], "role": user["role"]}
    if user["role"] == "tutor" and user.get("invite_code"):
        profile["invite_code"] = user["invite_code"]
    return profile


def session_user(token):
    if token:
        try:
            return jwt.decode(token, app.state.jwt_secret, algorithms=["HS256"],
                              options={"require": ["sub", "exp", "role", "name"]})
        except jwt.InvalidTokenError:
            pass
    return None


def require_user(adaptlearn_session: str | None = Cookie(default=None)):
    user = session_user(adaptlearn_session)
    if user is None:
        raise HTTPException(401, "Sign in to continue.")
    return user


def require_tutor(user=Depends(require_user)):
    if user["role"] != "tutor":
        raise HTTPException(403, "Tutor access is required.")
    return user


def require_student(user=Depends(require_user)):
    if user["role"] != "student":
        raise HTTPException(403, "Student access is required.")
    return user


def start_session(response, user):
    now = int(time.time())
    token = jwt.encode({"sub": user["_id"], **public_user(user), "classroom_id": user.get("classroom_id"), "iat": now, "exp": now + COOKIE_TTL},
                       app.state.jwt_secret, algorithm="HS256")
    response.set_cookie(COOKIE_NAME, token, max_age=COOKIE_TTL, httponly=True, secure=app.state.secure,
                        samesite="strict", path="/api")
    return public_user(user)


@app.post("/api/register", status_code=201)
def register(body: Registration, response: Response, db=Depends(database)):
    user = {"_id": body.email.lower(), "name": body.name.strip(),
            "password": PASSWORD.hash(body.password), "role": body.role}
    invite_code = body.invite_code.strip().lower()
    if body.role == "tutor":
        user["invite_code"] = uuid4().hex
    elif invite_code:
        tutor = db.users.find_one({"invite_code": invite_code, "role": "tutor"}, {"_id": 1})
        if tutor is None:
            raise HTTPException(400, "This tutor invite code is invalid.")
        user["classroom_id"] = tutor["_id"]
    try:
        db.users.insert_one(user)
    except DuplicateKeyError:
        if db.users.find_one({"_id": user["_id"]}, {"_id": 1}):
            raise HTTPException(409, "This email is already registered.")
        raise HTTPException(503, "Could not create the account. Try again.")
    return start_session(response, user)


@app.post("/api/login")
def login(body: Credentials, response: Response, db=Depends(database)):
    user = db.users.find_one({"_id": body.email.lower()})
    valid = PASSWORD.verify(body.password, user["password"] if user else DUMMY_HASH)
    if user is None or not valid:
        raise HTTPException(401, "Email or password is incorrect.")
    return start_session(response, user)


@app.post("/api/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/api", secure=app.state.secure, httponly=True, samesite="strict")
    return {"ok": True}


@app.get("/api/me")
def me(user=Depends(require_user)):
    return public_user(user)


def visible_question(question):
    return {key: value for key, value in question.items() if key not in {"correct", "hints"}}


@app.get("/api/questions")
def questions(_user=Depends(require_student)):
    return [visible_question(question) for question in QUESTIONS.values()]


def public_attempt(attempt):
    return {key: value for key, value in attempt.items() if key not in {"_id", "student_id", "student", "classroom_id"}}


def recent_attempts(db, query, limit=500):
    return list(db.attempts.find(query).sort("created_at", DESCENDING).limit(limit))


@app.get("/api/attempts")
def history(user=Depends(require_student), db=Depends(database)):
    return [public_attempt(attempt) for attempt in recent_attempts(db, {"student_id": user["sub"]})]


async def hint_for(question, choice):
    fallback = question["hints"][choice]
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return fallback, "Concept hint"
    messages = [
        {"role": "system", "content": "You tutor beginners. In two short sentences, explain the misconception in the selected wrong option and give one next step. Never state the correct option or its position."},
        {"role": "user", "content": json.dumps({"question": question["prompt"], "code": question.get("code"),
                                                  "wrong_answer": question["options"][choice],
                                                  "teaching_note": fallback})},
    ]
    try:
        result = await app.state.http.post("https://api.openai.com/v1/chat/completions",
                                           headers={"Authorization": f"Bearer {key}"},
                                           json={"model": os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
                                                 "messages": messages, "max_completion_tokens": 120})
        result.raise_for_status()
        hint = result.json()["choices"][0]["message"]["content"].strip()
        if 12 <= len(hint) <= 600:
            return hint, "AI hint"
    except (httpx.HTTPError, KeyError, IndexError, AttributeError, ValueError, TypeError):
        pass
    return fallback, "Concept hint"


@app.post("/api/attempts")
async def submit(body: Answer, user=Depends(require_student), db=Depends(database)):
    question = QUESTIONS.get(body.question_id)
    if question is None:
        raise HTTPException(404, "Question unavailable.")

    attempt_id = f'{user["sub"]}:{body.submission_id}'
    prior = await run_in_threadpool(db.attempts.find_one, {"_id": attempt_id})
    if prior:
        return public_attempt(prior)
    correct = body.choice == question["correct"]
    hint, source = ("Good work. You applied the concept correctly.", "Feedback")
    if not correct:
        hint, source = await hint_for(question, body.choice)
    attempt = {"_id": attempt_id, "student_id": user["sub"], "student": user["name"],
               "question_id": body.question_id, "choice": body.choice, "topic": question["topic"],
               "classroom_id": user.get("classroom_id"),
               "correct": correct, "hint": hint, "source": source,
               "created_at": datetime.now(timezone.utc).isoformat(timespec="microseconds")}
    try:
        await run_in_threadpool(db.attempts.insert_one, attempt)
    except DuplicateKeyError:
        return public_attempt(await run_in_threadpool(db.attempts.find_one, {"_id": attempt_id}))
    async with app.state.changed:
        app.state.revision += 1
        app.state.changed.notify_all()
    return public_attempt(attempt)


def summarize(rows):
    topics = []
    for topic in TOPICS:
        attempts = [row for row in rows if row["topic"] == topic]
        topics.append({"topic": topic, "attempts": len(attempts), "misses": sum(not row["correct"] for row in attempts)})
    groups = {}
    for attempt in rows:
        key = (attempt["student_id"], attempt["topic"])
        group = groups.setdefault(key, {"student": attempt["student"], "topic": attempt["topic"], "attempts": 0, "misses": 0})
        group["attempts"] += 1
        group["misses"] += not attempt["correct"]
    needs_review = [group for group in groups.values() if group["misses"] >= 2 and group["misses"] * 2 >= group["attempts"]]
    return {"topics": topics, "students": len({row["student_id"] for row in rows}), "attempts": len(rows),
            "correct": sum(row["correct"] for row in rows), "needs_review": needs_review[:15],
            "recent": [{key: attempt[key] for key in ("student", "topic", "correct", "created_at")} for attempt in rows[:12]]}


@app.get("/api/dashboard")
async def dashboard(tutor=Depends(require_tutor), db=Depends(database)):
    # Provisioned tutors retain access to legacy attempts. Self-registered tutors see their classroom only.
    classroom_id = tutor["sub"] if tutor.get("invite_code") else None
    query = {"classroom_id": classroom_id} if classroom_id else {"classroom_id": {"$exists": False}}
    redis = app.state.redis
    revision = app.state.revision
    key = f"{CACHE_KEY}:{app.state.cache_namespace}:{revision}:{classroom_id or 'legacy'}"
    if redis is not None:
        try:
            cached = await redis.get(key)
            if cached:
                return json.loads(cached)
        except (RedisError, ValueError):
            pass
    payload = summarize(await run_in_threadpool(recent_attempts, db, query, 1000))
    if redis is not None and revision == app.state.revision:
        try:
            await redis.set(key, json.dumps(payload), ex=25)
        except RedisError:
            pass
    return payload


@app.websocket("/api/live")
async def live(websocket: WebSocket):
    user = session_user(websocket.cookies.get(COOKIE_NAME))
    host = websocket.headers.get("host", "")
    origin = websocket.headers.get("origin")
    if not user or user["role"] != "tutor" or user.get("invite_code") or origin not in {f"https://{host}", f"http://{host}"}:
        await websocket.close(code=1008)
        return
    await websocket.accept()
    async def wait_for_revision(revision):
        async with app.state.changed:
            await app.state.changed.wait_for(lambda: app.state.revision != revision)

    try:
        revision = app.state.revision
        await websocket.send_json({"type": "ready"})
        while time.time() < user["exp"]:
            change = asyncio.create_task(wait_for_revision(revision))
            receive = asyncio.create_task(websocket.receive())
            try:
                done, _ = await asyncio.wait({change, receive}, timeout=20, return_when=asyncio.FIRST_COMPLETED)
                if receive in done and receive.result()["type"] == "websocket.disconnect":
                    return
                if change in done:
                    revision = app.state.revision
                    await websocket.send_json({"type": "attempt"})
                elif not done:
                    await websocket.send_json({"type": "heartbeat"})
            finally:
                for task in (change, receive):
                    if not task.done():
                        task.cancel()
                await asyncio.gather(change, receive, return_exceptions=True)
        await websocket.close(code=1008)
    except (RuntimeError, OSError):
        return


if (ROOT / "dist").is_dir():
    app.mount("/", StaticFiles(directory=ROOT / "dist", html=True), name="frontend")
