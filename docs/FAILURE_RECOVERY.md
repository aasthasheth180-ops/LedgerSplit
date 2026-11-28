# LedgerSplit — Failure Recovery

## Objective

Validate application behavior during database unavailability, automatic database reconnection, and persistence of existing records.

## Test Environment

- Docker Compose
- FastAPI and SQLAlchemy
- PostgreSQL
- Isolated testing environment on localhost:8081
- Synthetic user and financial records
- Separate persistent database volume

## Scenario 1 — Database Disconnection

PostgreSQL was deliberately stopped while the backend remained running.

```powershell
docker compose -p ledgersplit-load --env-file .env.docker -f compose.yaml -f compose.load.yaml stop db
```

Observed behavior:

- Liveness endpoint returned HTTP 200.
- Readiness endpoint returned HTTP 503.
- Backend remained responsive.
- Readiness response reported database unavailability.

## Scenario 2 — Automatic Reconnection

PostgreSQL was restarted without restarting the backend.

```powershell
docker compose -p ledgersplit-load --env-file .env.docker -f compose.yaml -f compose.load.yaml start db
```

After a 10-second waiting period, both health endpoints returned HTTP 200.

SQLAlchemy connection pre-ping helps detect stale database connections and replace them when connectivity becomes available.

## Scenario 3 — Data Persistence

| Entity | Before Failure | After Recovery |
|---|---:|---:|
| Users | 332 | 332 |
| Groups | 222 | 222 |
| Expenses | 398 | 398 |
| Expense splits | 398 | 398 |
| Payments | 0 | 0 |

All inspected record counts remained unchanged.

## Financial Reliability Safeguards

LedgerSplit implements:

- Transaction rollback on failed database operations.
- Idempotency protection for financial submissions.
- Database locking for concurrent financial operations.
- Payment confirmation and rejection state validation.
- Protection against duplicate financial records.
- Persistent PostgreSQL storage.
- Database backup and restoration procedures.

Financial concurrency and transaction correctness are evaluated separately through automated regression tests.

## Recovery Procedure

1. Inspect container status and structured application logs.
2. Check backend liveness and database readiness.
3. Identify and resolve the database connectivity issue.
4. Restart PostgreSQL when necessary.
5. Verify that readiness returns HTTP 200.
6. Verify persisted records and financial consistency.
7. Investigate failed requests before retrying financial operations.

## Limitations

- This experiment simulated a controlled database shutdown, not an unexpected hardware failure.
- Matching record counts do not independently verify every stored field.
- The isolated database contained no payment records. Payment restoration was verified separately during backup recovery testing.
- Exact automatic reconnection time was not measured.
- In-flight financial writes during database failure were not tested in this experiment.
- Production failover, replication and automated incident alerting remain future improvements.

## Conclusion

The local application detected database unavailability, remained live during the outage, recovered database connectivity without a backend restart, and preserved the inspected database record counts.