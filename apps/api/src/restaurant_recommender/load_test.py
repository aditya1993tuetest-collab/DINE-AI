"""Dependency-free bounded load smoke test; never runs without an explicit target."""

import argparse
import json
import statistics
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--requests", type=int, default=50)
    parser.add_argument("--concurrency", type=int, default=5)
    args = parser.parse_args()
    if args.requests > 10_000 or args.concurrency > 100:
        parser.error("safety ceiling exceeded")
    payload = json.dumps(
        {"location": {"city": "Bangalore"}, "cuisines": [], "resultCount": 5}
    ).encode()

    def call() -> tuple[float, int]:
        started = time.perf_counter()
        request = urllib.request.Request(
            args.url.rstrip("/") + "/api/v1/recommendations",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                return time.perf_counter() - started, response.status
        except Exception:
            return time.perf_counter() - started, 0

    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = [pool.submit(call) for _ in range(args.requests)]
        results = [future.result() for future in as_completed(futures)]
    latencies = sorted(value * 1000 for value, _ in results)

    def percentile(value: float) -> float:
        return latencies[min(int(len(latencies) * value), len(latencies) - 1)]

    report = {
        "requests": len(results),
        "successes": sum(status == 200 for _, status in results),
        "p50Ms": percentile(0.5),
        "p95Ms": percentile(0.95),
        "p99Ms": percentile(0.99),
        "meanMs": statistics.mean(latencies),
    }
    print(json.dumps(report))


if __name__ == "__main__":
    main()
