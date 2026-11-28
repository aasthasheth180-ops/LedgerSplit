from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.models.user import User


def authenticate_user(
    db: Session,
    email: str,
    password: str,
) -> User | None:

    normalized_email = email.strip().lower()

    user = db.scalar(
        select(User).where(User.email == normalized_email).with_for_update().execution_options(populate_existing=True)
    )

    if user is None:
        return None

    if not user.is_active:
        return None

    if user.hashed_password is None:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user