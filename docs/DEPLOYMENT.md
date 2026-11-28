# LedgerSplit — Deployment Guide

## 1. Deployment Architecture

LedgerSplit uses a containerized full-stack architecture.

| Service | Responsibility |
|---|---|
| Frontend | React, TypeScript, Vite and Nginx |
| Backend | FastAPI REST API |
| Database | PostgreSQL 18 |
| Migrate | Alembic database migrations |
| Worker | Background payment reminders |

Nginx serves the frontend and proxies requests under `/api/` to the backend. PostgreSQL data is stored in the persistent `ledger_data` Docker volume.

## 2. Prerequisites

- Git
- Docker Desktop
- Docker Compose
- Available local port 8080

## 3. Clone the Repository

```powershell
git clone https://github.com/aasthasheth180-ops/LedgerSplit.git
cd LedgerSplit
```

## 4. Environment Configuration

Create a private `.env.docker` file containing the variables referenced by `docker-compose.yml`.

Configure the following application settings through the Compose environment:

| Variable | Purpose |
|---|---|
| APP_ENV | Application environment |
| DATABASE_URL | PostgreSQL connection string |
| POSTGRES_PASSWORD | Database password |
| JWT_SECRET_KEY | JWT signing secret |
| JWT_ALGORITHM | JWT signing algorithm; HS256 |
| ACCESS_TOKEN_EXPIRE_MINUTES | Access-token lifetime |
| TRUSTED_ORIGINS | Approved browser origins |
| GOOGLE_CLIENT_ID | Optional Google authentication client ID |

Generate a secure JWT secret using:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Keep all database credentials and JWT secrets outside version control.

The Google OAuth client ID is public configuration. Backend credentials must never be included in frontend build variables.

## 5. Start the Application

```powershell
docker compose --env-file .env.docker config --quiet
docker compose --env-file .env.docker up --build -d
```

Check service status:

```powershell
docker compose --env-file .env.docker ps
```

Open the application at:

http://localhost:8080

## 6. Database Migrations

The migration service automatically executes:

```bash
alembic upgrade head
```

PostgreSQL must become healthy before migrations execute. The backend starts after successful migration completion.

Check migration logs:

```powershell
docker compose --env-file .env.docker logs migrate
```

Inspect the current database revision:

```powershell
docker compose --env-file .env.docker exec backend alembic current
```

## 7. Deployment Verification

```powershell
curl.exe -i http://localhost:8080/api/health/live
curl.exe -i http://localhost:8080/api/health/ready
curl.exe -i http://localhost:8080/api/metrics
```

Expected results:

- Liveness: HTTP 200.
- Readiness: HTTP 200 when PostgreSQL is reachable.
- Metrics: HTTP 200 with request counts, latency and error rate.

## 8. Stop or Restart Services

Stop containers while preserving database storage:

```powershell
docker compose --env-file .env.docker down
```

Restart the application:

```powershell
docker compose --env-file .env.docker up -d
```

Do not use `docker compose down -v` unless permanent deletion of the local database is intended.

## 9. Production Deployment Requirements

Before public deployment:

- Configure APP_ENV as production.
- Use strong, securely managed credentials.
- Configure a production PostgreSQL instance.
- Enable HTTPS.
- Configure approved HTTPS origins.
- Verify secure authentication cookies.
- Restrict access to internal monitoring endpoints.
- Configure automated backups and recovery procedures.
- Configure external monitoring and alerts.
- Execute production smoke tests.

## 10. Current Deployment Status

Local containerized deployment has been implemented and verified.

Public hosting, production PostgreSQL infrastructure and public HTTPS verification remain pending.