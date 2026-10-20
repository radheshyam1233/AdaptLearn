# backend/Dockerfile
# Builds an image that runs the API anywhere Docker runs.

# Small official Python image
FROM python:3.12-slim

# Don't write .pyc files; print logs immediately
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

WORKDIR /app

# Copy requirements first: Docker caches this layer, so packages are only
# re-installed when requirements.txt changes, not on every code change
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Now copy the code
COPY . .

# Hosting platforms tell the app which port to use through $PORT.
# If SEED_DEMO=true, load the demo accounts, questions and activity first
# (safe to repeat: the seed script skips anything that already exists).
CMD ["sh", "-c", "if [ \"$SEED_DEMO\" = \"true\" ]; then python -m scripts.seed --demo; fi; uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
