from fastapi import HTTPException, Request, status

from app.core.config import settings


def require_trusted_origin(request: Request) -> None:

    origin = request.headers.get("origin")

    if origin not in settings.TRUSTED_ORIGINS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Untrusted request origin",
        )