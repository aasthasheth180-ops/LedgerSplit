from fastapi import FastAPI

from app.core.config import settings
from app.api.auth import router as auth_router
from app.api.users import router as users_router

app = FastAPI(
    title=settings.APP_NAME,
    description="Shared Expense and Payment Reconciliation Platform",
    version=settings.APP_VERSION,
)

# Register authentication endpoints
app.include_router(auth_router)
app.include_router(users_router)

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