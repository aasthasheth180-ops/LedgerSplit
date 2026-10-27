# LedgerSplit

**A Shared Expense and Payment Reconciliation Platform**

LedgerSplit is a backend-focused software engineering project designed to address common problems in shared expense management, including forgotten payment confirmations, confusing balances, repetitive expense entry, and transaction reliability.

The platform is designed for students, roommates, and groups who want a simple way to track shared expenses and reconcile payments made through external services such as Zelle.

## Problem Statement

Existing expense-sharing workflows often rely on users manually recording expenses and marking payments as settled.

This can lead to:

- Outstanding balances even after someone has paid.
- Forgotten recurring expenses and reimbursements.
- Confusion about how much each participant owes.
- Duplicate requests or inconsistent financial records.
- Frustration with usage limits and advertisements.

## Proposed Solution

LedgerSplit aims to provide:

- Free, ad-free shared expense tracking.
- Flexible expense splitting for groups.
- Payment reporting and two-sided settlement confirmation.
- Recurring bill tracking and reminders.
- Transparent balance explanations.
- An auditable financial ledger.
- Idempotent, concurrency-safe transaction processing.

**Important:** LedgerSplit does not process Zelle transfers or independently verify external payments. Its planned reconciliation workflow allows users to report and confirm payments made outside the application.

## Technology Stack

| Component | Technology |
|---|---|
| Backend | Python, FastAPI |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Database migrations | Alembic |
| Data validation | Pydantic |
| Authentication | JWT, OAuth2 bearer tokens |
| Password security | Argon2 |
| Testing | Pytest, HTTPX2 |
| Frontend (planned) | React, TypeScript |
| Containers (planned) | Docker |
| CI/CD (planned) | GitHub Actions |

## Current Implementation

### Phase 1 — Project Foundation (Completed)

- Initialized FastAPI application.
- Created modular backend directory structure.
- Implemented environment-based configuration.
- Implemented home and health-check endpoints.
- Added automated API tests.
- Established dependency management and Git version control.

### Phase 2 — Database and Authentication (Completed)

**Database integration**

- Installed and configured PostgreSQL.
- Created a dedicated application database and database role.
- Integrated SQLAlchemy with PostgreSQL using Psycopg.
- Implemented database sessions and dependency injection.
- Created a persistent user model.
- Configured Alembic migrations.
- Created and applied the initial users table migration.

**Authentication and security**

- Implemented user registration.
- Added email validation and duplicate-account handling.
- Implemented Argon2 password hashing.
- Implemented password verification.
- Implemented user login and JWT access-token generation.
- Configured token expiration.
- Implemented authenticated user dependencies.
- Added a protected user profile endpoint.
- Added handling for missing, invalid, and expired authentication tokens.

**Automated testing**

- Configured a separate PostgreSQL test database.
- Added isolated database fixtures.
- Added registration, login, and protected-route tests.
- Verified invalid authentication scenarios.
- Confirmed all 10 automated tests pass.

## API Endpoints

| Method | Endpoint | Description | Authentication |
|---|---|---|---|
| GET | `/` | Application welcome message | No |
| GET | `/health` | Application health check | No |
| POST | `/auth/register` | Register a new user | No |
| POST | `/auth/login` | Authenticate and obtain an access token | No |
| GET | `/users/me` | Retrieve the authenticated user's profile | JWT required |

Interactive API documentation is available through FastAPI Swagger UI.

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/aasthasheth180-ops/LedgerSplit.git
cd LedgerSplit
```

### 2. Create a virtual environment

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Configure PostgreSQL

Install PostgreSQL and create a development database and an application role with the necessary database permissions.

The application requires a valid PostgreSQL connection string.

### 5. Configure environment variables

Create a `.env` file using `.env.example` as a template, if available:

```powershell
Copy-Item .env.example .env
```

Configure the following values:

```dotenv
DATABASE_URL=postgresql+psycopg://USERNAME:PASSWORD@localhost:5432/ledgersplit_db
JWT_SECRET_KEY=replace-with-a-long-random-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

Replace the placeholders with your own local configuration. URL-encode reserved characters in database credentials.

Never commit `.env`, passwords, or JWT secrets to version control.

### 6. Apply database migrations

```powershell
python -m alembic upgrade head
```

### 7. Run the application

```powershell
python -m uvicorn app.main:app --reload
```

API documentation: http://127.0.0.1:8000/docs

Health check: http://127.0.0.1:8000/health

### 8. Run automated tests

Automated authentication tests use an isolated PostgreSQL test database. Configure the test database connection before running the suite.

```powershell
python -m pytest tests/ -v
```

e next development phase will introduce group creation, group membership, shared expense records, and expense splitting. Financial ledger and settlement reconciliation functionality will be implemented in subsequent phases.
