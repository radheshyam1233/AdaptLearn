# scripts/seed.py
# Fills the database with demo accounts and questions.
#   python -m scripts.seed          -> tutor + student accounts + 30 questions
#   python -m scripts.seed --demo   -> also 12 demo students with past attempts,
#                                      so the tutor dashboard has data to show
# Safe to run more than once: it skips anything that already exists.

import random
import sys
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.database import Base, SessionLocal, engine
from app.models import Attempt, Question, User
from app.security import hash_password
from app.services.gap import update_gap

# (text, A, B, C, D, answer, concept, difficulty)
QUESTIONS = [
    # --- Limits ---
    ("lim (x -> 0) sin(x) / x equals?", "0", "1", "Infinity", "Does not exist", "B", "Limits", 1),
    ("lim (x -> infinity) (3x^2 + 2) / (x^2 - 5) equals?", "0", "3", "Infinity", "2/5", "B", "Limits", 2),
    ("lim (x -> 2) (x^2 - 4) / (x - 2) equals?", "0", "2", "4", "Undefined", "C", "Limits", 1),
    ("lim (x -> 0) (1 + x)^(1/x) equals?", "1", "e", "0", "Infinity", "B", "Limits", 2),
    ("lim (x -> 0) |x| / x equals?", "1", "-1", "0", "Does not exist", "D", "Limits", 3),
    # --- Derivatives ---
    ("d/dx (x^3) equals?", "3x^2", "x^2", "3x", "x^4 / 4", "A", "Derivatives", 1),
    ("d/dx (sin x) equals?", "-cos x", "cos x", "-sin x", "tan x", "B", "Derivatives", 1),
    ("d/dx (e^(2x)) equals?", "e^(2x)", "2e^(2x)", "2x e^(2x)", "e^(2x) / 2", "B", "Derivatives", 2),
    ("d/dx (ln x) equals?", "1/x", "ln x", "x", "e^x", "A", "Derivatives", 1),
    ("d/dx (sin(x^2)) equals?", "cos(x^2)", "2x cos(x^2)", "2x sin(x^2)", "cos(2x)", "B", "Derivatives", 3),
    # --- Integration ---
    ("Integral of 2x dx equals?", "2", "x^2", "x^2 + C", "2x^2 + C", "C", "Integration", 1),
    ("Integral of cos x dx equals?", "sin x + C", "-sin x + C", "cos x + C", "tan x + C", "A", "Integration", 1),
    ("Definite integral of x dx from 0 to 1 equals?", "1", "1/2", "2", "0", "B", "Integration", 2),
    ("Integral of (1/x) dx equals?", "ln|x| + C", "1/x^2 + C", "x + C", "-1/x^2 + C", "A", "Integration", 2),
    ("Integral of x e^x dx equals?", "x e^x + C", "(x - 1) e^x + C", "(x + 1) e^x + C", "e^x + C", "B", "Integration", 3),
    # --- Big-O ---
    ("Time complexity of binary search on a sorted array?", "O(n)", "O(log n)", "O(n log n)", "O(1)", "B", "Big-O", 1),
    ("Two nested loops, each running n times, take?", "O(n)", "O(log n)", "O(n^2)", "O(2n)", "C", "Big-O", 1),
    ("Average time to look up a key in a hash map?", "O(1)", "O(log n)", "O(n)", "O(n^2)", "A", "Big-O", 1),
    ("Worst-case time of merge sort?", "O(n^2)", "O(n log n)", "O(n)", "O(log n)", "B", "Big-O", 2),
    ("How many times does 'i = 1; while i < n: i *= 2' loop?", "O(n)", "O(sqrt n)", "O(log n)", "O(n/2)", "C", "Big-O", 2),
    # --- Recursion ---
    ("A recursive function hits RecursionError. What is it most likely missing?",
     "A return statement", "A base case", "A loop", "A global variable", "B", "Recursion", 1),
    ("Time complexity of naive recursive fib(n) = fib(n-1) + fib(n-2)?", "O(n)", "O(n log n)", "O(2^n)", "O(n^2)", "C", "Recursion", 2),
    ("f(n) = 1 if n == 0 else n * f(n-1). What is f(4)?", "10", "24", "12", "4", "B", "Recursion", 1),
    ("Which structure manages active function calls during recursion?", "Queue", "Heap", "Call stack", "Hash table", "C", "Recursion", 1),
    ("Space complexity of the recursive factorial f(n)?", "O(1)", "O(log n)", "O(n)", "O(n^2)", "C", "Recursion", 3),
    # --- SQL Joins ---
    ("Which join returns only rows that match in both tables?", "LEFT JOIN", "INNER JOIN", "FULL OUTER JOIN", "CROSS JOIN", "B", "SQL Joins", 1),
    ("What does a LEFT JOIN return?", "Only matching rows",
     "All left-table rows, plus matching right-table rows", "All right-table rows", "Every combination of rows", "B", "SQL Joins", 1),
    ("Table A has 3 rows and table B has 4. How many rows does A CROSS JOIN B return?", "7", "12", "3", "4", "B", "SQL Joins", 2),
    ("How do you find customers who have placed no orders?", "INNER JOIN orders",
     "LEFT JOIN orders ... WHERE orders.id IS NULL", "RIGHT JOIN customers", "CROSS JOIN orders", "B", "SQL Joins", 2),
    ("Which clause filters groups after GROUP BY?", "WHERE", "HAVING", "ORDER BY", "LIMIT", "B", "SQL Joins", 2),
]

DEMO_NAMES = ["Aarav Sharma", "Priya Mehta", "Rohan Gupta", "Sneha Iyer", "Ishaan Verma", "Ananya Rao",
              "Kabir Singh", "Meera Nair", "Arjun Patel", "Diya Joshi", "Vivaan Reddy", "Riya Das"]


def get_or_create_user(db, name, email, password, role):
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(name=name, email=email, password_hash=hash_password(password), role=role)
        db.add(user)
        db.flush()   # sends the INSERT now so user.id is available
    return user


def seed_basics(db):
    get_or_create_user(db, "Demo Tutor", "tutor@demo.com", "demo1234", "tutor")
    get_or_create_user(db, "Demo Student", "student@demo.com", "demo1234", "student")
    if db.scalar(select(func.count(Question.id))) == 0:
        for text, a, b, c, d, ans, concept, diff in QUESTIONS:
            db.add(Question(text=text, option_a=a, option_b=b, option_c=c, option_d=d,
                            answer=ans, concept=concept, difficulty=diff))
    db.commit()
    print(f"Accounts ready, {db.scalar(select(func.count(Question.id)))} questions in the database")


def seed_demo_activity(db):
    """12 students with different skill levels answer questions over the last 20 hours."""
    rng = random.Random(42)   # fixed seed: the same demo data every time
    questions = db.scalars(select(Question)).all()
    concepts = sorted({q.concept for q in questions})
    now = datetime.now(timezone.utc)
    created = 0
    for i, name in enumerate(DEMO_NAMES):
        email = f"demo{i + 1}@demo.com"
        if db.scalar(select(User).where(User.email == email)):
            continue   # already seeded
        user = get_or_create_user(db, name, email, "demo1234", "student")
        for concept in concepts:
            skill = rng.uniform(0.45, 0.97)   # chance this student answers correctly
            pool = [q for q in questions if q.concept == concept]
            for _ in range(rng.randint(3, 8)):
                q = rng.choice(pool)
                ok = rng.random() < skill
                wrong = rng.choice([x for x in "ABCD" if x != q.answer])
                db.add(Attempt(user_id=user.id, question_id=q.id,
                               selected=q.answer if ok else wrong, is_correct=ok,
                               created_at=now - timedelta(minutes=rng.randint(5, 20 * 60))))
                update_gap(db, user.id, concept, ok)
                db.flush()   # make the new gap row visible to the next update_gap call
                created += 1
        db.commit()
    print(f"Demo activity: {created} attempts added")


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_basics(db)
        if "--demo" in sys.argv:
            seed_demo_activity(db)
