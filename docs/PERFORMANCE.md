# LedgerSplit — Performance Testing

## Objective

Evaluate API performance, concurrent request handling, database connection management, and application stability under increasing user load.

## Testing Environment

- FastAPI, SQLAlchemy and PostgreSQL
- Docker Compose
- Locust 2.47.0
- Isolated testing environment on localhost:8081
- Separate PostgreSQL database volume
- Synthetic user accounts

## Benchmark Results

| Users | Requests | Failures | Error Rate | Mean Latency | P95 | Requests/sec |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 16 | 0 | 0% | 249 ms | 2700 ms | 0.57 |
| 10 | 303 | 0 | 0% | 128 ms | 210 ms | 5.13 |
| 50 | 1355 | 0 | 0% | 265 ms | 1500 ms | 22.75 |
| 100 — Initial | 162 | 22 | 13.58% | 20038 ms | 35000 ms | 3.63 |
| 100 — Diagnostic | 132 | 32 | 24.24% | 15033 ms | 36000 ms | 3.04 |
| 100 — Optimized | 1401 | 0 | 0% | 2397 ms | 8400 ms | 23.52 |

## Bottleneck Investigation

The initial 100-user benchmark produced HTTP 500 errors and response times exceeding 30 seconds.

Structured exception logging revealed repeated TimeoutError exceptions. SQLAlchemy connection pool exhaustion was identified as the leading hypothesis based on the timeout duration and default connection limits.

## Optimization

| Configuration | Before | After |
|---|---:|---:|
| Pool size | 5 | 20 |
| Maximum overflow | 10 | 10 |
| Maximum connections per engine | 15 | 30 |
| Pool timeout | 30 seconds | 30 seconds |

PostgreSQL's configured maximum connection count was 100.

Password hashing, authorization, financial transaction handling and idempotency safeguards remained unchanged.

## Results

The optimized 100-user benchmark achieved:

- 1,401 successful requests
- Zero observed request failures
- Approximately 88% lower aggregate mean latency
- Approximately 76% lower P95 latency
- 100 successful registrations, logins and group creations
- 170 successful expense creation requests
- No exception errors observed in the backend logs
- 11 passing targeted database and concurrency regression tests

## Reproducing the Benchmark

```powershell
python -m pip install -r requirements-load.txt

docker compose -p ledgersplit-load --env-file .env.docker -f compose.yaml -f compose.load.yaml up -d --build

python -m locust -f scripts/locustfile.py --headless --host http://localhost:8081 -u 100 -r 10 -t 60s --html performance/results/load_100_optimized.html
```

Verify application readiness before running the benchmark. If Nginx returns HTTP 502 after backend recreation, verify backend health and restart the isolated frontend container.

## Limitations

- Results represent short-duration local benchmarks, not production capacity guarantees.
- Registration and login operations remain relatively expensive under heavy load.
- The workload includes account registration and group creation, rather than exclusively steady-state traffic.
- The failed and successful runs have different completed request distributions.
- Locust-reported throughput may use different request observation intervals.
- The exact source of the timeout exceptions was not independently established.
- Shared-group financial contention is evaluated separately through concurrency tests.
- Connection pool limits must be reconsidered when increasing backend workers or deployment replicas.
- Longer-duration testing and production infrastructure benchmarking remain future work.