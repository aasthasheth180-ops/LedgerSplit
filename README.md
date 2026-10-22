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
- Duplicate requests or inconsistent financial records if the backend is not designed carefully.
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

**Note:** LedgerSplit does not process Zelle transfers or independently verify external payments. Its planned reconciliation workflow allows users to report and confirm payments made outside the application.

## Technology Stack

| Component | Technology |
|---|---|
| Backend | Python, FastAPI |
| Database (planned) | PostgreSQL |
| ORM (planned) | SQLAlchemy |
| Frontend (planned) | React, TypeScript |
| Testing | Pytest, HTTPX2 |
| Containers (planned) | Docker |
| CI/CD (planned) | GitHub Actions |

## Current Implementation

**Phase 1 — Project Foundation (in progress)**

- FastAPI application initialized.
- Modular backend directory structure created.
- Environment-based configuration added.
- Home and health-check endpoints implemented.
- Automated API tests implemented.
- Dependency versions recorded.

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/LedgerSplit.git
cd LedgerSplit
```

Replace `YOUR_USERNAME` with the actual GitHub username.

### 2. Create a virtual environment

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Configure environment variables

Copy `.env.example` to `.env`:

```powershell
Copy-Item .env.example .env
```

### 5. Run the application

```powershell
python -m uvicorn app.main:app --reload
```

API documentation: http://127.0.0.1:8000/docs

Health check: http://127.0.0.1:8000/health

### 6. Run automated tests

```powershell
python -m pytest tests/ -v
```

## Development Roadmap

- [ ] Phase 1 — Project Foundation
- [ ] Phase 2 — Database and Authentication
- [ ] Phase 3 — Groups and Expense Management
- [ ] Phase 4 — Financial Ledger and Balance Transparency
- [ ] Phase 5 — External Payment Reconciliation
- [ ] Phase 6 — Reliability and Concurrency
- [ ] Phase 7 — Recurring Bills and Notifications
- [ ] Phase 8 — Smart Expense Features
- [ ] Phase 9 — Frontend and User Experience
- [ ] Phase 10 — Deployment and Production Engineering
- [ ] Phase 11 — Theory and Interview Preparation

## Project Status

**Phase 1: In progress**

The FastAPI foundation and initial automated tests are working. Financial ledger functionality, user accounts, expense splitting, and payment reconciliation have not yet been implemented.

## Project Goals

LedgerSplit is being developed to explore practical backend engineering concepts, including relational database design, financial consistency, transaction isolation, concurrency control, idempotency, and reliable API development.