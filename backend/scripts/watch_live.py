# scripts/watch_live.py
# Watch the tutor live feed from the terminal (handy before the frontend exists).
#     python -m scripts.watch_live
# Then submit answers as a student in /docs and watch events appear here.

import asyncio
import json
import sys

import httpx
import websockets   # installed with uvicorn[standard]

API = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"


async def main():
    r = httpx.post(f"{API}/auth/login", data={"username": "tutor@demo.com", "password": "demo1234"})
    r.raise_for_status()
    token = r.json()["access_token"]
    url = API.replace("http", "ws", 1) + f"/ws/dashboard?token={token}"
    async with websockets.connect(url) as ws:
        print("Connected. Waiting for student answers... (Ctrl+C to stop)")
        while True:
            event = json.loads(await ws.recv())
            mark = "right" if event["is_correct"] else "WRONG"
            print(f"{event['student']:15} {event['concept']:12} {mark:6} gap={event['gap_score']}")


if __name__ == "__main__":
    asyncio.run(main())
