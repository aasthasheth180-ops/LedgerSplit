from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import UserCreate


class EmailAlreadyRegisteredError(Exception):
    pass


def create_user(db: Session, user_data: UserCreate) -> User:
    normalized_email = str(user_data.email).strip().lower()

    existing_user = db.scalar(
        select(User).where(User.email == normalized_email)
    )

    if existing_user is not None:
        raise EmailAlreadyRegisteredError()

    new_user = User(
        full_name=user_data.full_name.strip(),
        email=normalized_email,
        hashed_password=hash_password(user_data.password),
    )

    db.add(new_user)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(new_user)

    return new_user