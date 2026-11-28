# LedgerSplit — Monitoring and Troubleshooting

## 1. Monitoring Overview

LedgerSplit implements:

- Structured backend request logging.
- Unique request identifiers.
- Liveness and readiness endpoints.
- API request counters.
- Mean request latency.
- Server error counts and error rates.
- Generic responses for unexpected server errors.

## 2. Health Endpoints

| Endpoint | Purpose |
|---|---|
| `/api/health/live` | Verify application availability |
| `/api/health/ready` | Verify database connectivity |
| `/api/metrics` | Inspect application request metrics |

```powershell
curl.exe -i http://localhost:8080/api/health/live
curl.exe -i http://localhost:8080/api/health/ready
curl.exe -i http://localhost:8080/api/metrics
```

A readiness failure indicates that the application cannot successfully complete its database connectivity check.

## 3. Structured Logging

Inspect recent backend logs:

```powershell
docker compose --env-file .env.docker logs --tail=50 backend
```

Example structured log:

```json
{
  "request_id": "c0a014e6140b4713a9a95dbff81fd467",
  "method": "GET",
  "status": 401,
  "duration_ms": 416.23
}
```

The `X-Request-ID` response header can be matched against backend logs to investigate individual requests.

Application request logs intentionally exclude request bodies, authentication tokens and passwords.

Avoid sharing unredacted infrastructure logs or environment configuration.

## 4. Verified Local Monitoring Results

Observed on November 28, 2026:

| Metric | Observed value |
|---|---:|
| Total requests | 46 |
| Server errors | 0 |
| Mean latency | 8.48 ms |
| Error rate | 0.0% |

These values represent a local runtime observation, not a controlled performance benchmark.

## 5. Common Failures

### Backend Unavailable

```powershell
docker compose --env-file .env.docker ps
docker compose --env-file .env.docker logs --tail=50 backend
```

Check backend startup, configuration and database availability.

### Database Connection Failure

```powershell
docker compose --env-file .env.docker logs --tail=50 db
docker compose --env-file .env.docker exec db pg_isready -U ledger -d ledger
```

Verify database credentials, connection configuration and container health.

### Migration Failure

```powershell
docker compose --env-file .env.docker logs migrate
```

Investigate the migration error before restarting the application. Back up existing data before attempting destructive schema changes.

### Authentication Failure

HTTP 401 indicates missing, invalid, expired or otherwise rejected authentication credentials.

Check the session state and attempt authentication again.

HTTP 403 indicates that access was forbidden. Verify group membership, ownership, permissions and trusted-origin configuration.

### Google Sign-In Unavailable

Verify:

- Google client ID configuration.
- Authorized JavaScript origins.
- Matching frontend and backend client IDs.

Rebuild the frontend after changing build-time Google configuration.

### Frontend or API Routing Failure

```powershell
docker compose --env-file .env.docker logs --tail=50 frontend
```

Check Nginx configuration, backend health and `/api/` routing.

### Reminder Worker Failure

```powershell
docker compose --env-file .env.docker logs --tail=50 worker
docker compose --env-file .env.docker restart worker
```

Verify database availability and worker status. A running worker alone does not prove successful reminder delivery.

### Duplicate or Conflicting Financial Requests

HTTP 409 may indicate an idempotency conflict, incompatible financial state or another business-rule conflict.

Refresh the current ledger state before submitting another operation. Do not blindly retry financial requests with new idempotency keys.

## 6. Proposed Monitoring Alerts

The following are initial operational thresholds for future external monitoring:

| Condition | Proposed alert |
|---|---|
| Readiness failure | Three consecutive failed checks |
| Server error rate | Above 5% over five minutes |
| API latency | Mean above 500 ms over five minutes |
| Worker unavailable | Worker process stops unexpectedly |

These thresholds are proposed, not currently automated or validated through load testing.

## 7. Monitoring Limitations

- Metrics are stored in process memory.
- Metrics reset when the backend restarts.
- Metrics are not aggregated across multiple backend processes.
- Health-check traffic contributes to request metrics.
- Readiness verifies database connectivity, not complete schema correctness.
- External monitoring dashboards and automated alerts are not yet configured.

## 8. Incident Investigation

1. Identify the failing operation.
2. Capture the HTTP status and request ID.
3. Inspect the corresponding backend logs.
4. Verify container and database health.
5. Investigate the underlying failure.
6. Apply the appropriate correction.
7. Repeat health checks and verify the affected workflow.

Preserve financial records and database volumes during troubleshooting.