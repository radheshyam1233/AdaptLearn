# scripts/benchmark.py
# Measures real response times, so the numbers on your resume are ones you measured.
# Start the API first, then in another terminal:
#     python -m scripts.benchmark                      (local API)
#     python -m scripts.benchmark https://your-api.onrender.com   (deployed API)
# Run it once with REDIS_URL empty in .env, and once with Redis on, then compare.

import statistics
import sys
import time

import httpx

API = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
RUNS = 200


def percentile(values, p):
    values = sorted(values)
    return values[min(len(values) - 1, int(round(p / 100 * (len(values) - 1))))]


def timed_get(client, url, headers) -> float:
    start = time.perf_counter()
    r = client.get(url, headers=headers)
    r.raise_for_status()
    return (time.perf_counter() - start) * 1000   # milliseconds


def main():
    with httpx.Client(base_url=API, timeout=10) as client:
        r = client.post("/auth/login", data={"username": "tutor@demo.com", "password": "demo1234"})
        r.raise_for_status()
        headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

        print(f"Redis connected: {client.get('/health').json()['redis']}")
        for url in ["/analytics/dashboard", "/analytics/concepts"]:
            timed_get(client, url, headers)                    # warm-up call
            times = [timed_get(client, url, headers) for _ in range(RUNS)]
            print(f"{url:24} p50 {statistics.median(times):6.1f} ms   "
                  f"p95 {percentile(times, 95):6.1f} ms   ({RUNS} requests)")


if __name__ == "__main__":
    main()
