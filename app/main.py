from fastapi import FastAPI

from app.core.config import settings
from app.api import auth, users, groups, expenses
from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.groups import router as groups_router
from app.api.balances import router as balances_router
from app.api.settlements import router as settlements_router
from app.api.payments import router as payments_router
from fastapi.middleware.cors import CORSMiddleware
from app.api.payment_requests import router as payment_requests_router

app = FastAPI(
    title=settings.APP_NAME,
    description="Shared Expense and Payment Reconciliation Platform",
    version=settings.APP_VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.TRUSTED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register authentication endpoints
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(groups_router)
app.include_router(expenses.router)
app.include_router(balances_router)
app.include_router(settlements_router)
app.include_router(payments_router)
app.include_router(payment_requests_router)
from app.api.notifications import router as notifications_router
app.include_router(notifications_router)

@app.get("/")
def root():
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "ledgersplit-api",
    }