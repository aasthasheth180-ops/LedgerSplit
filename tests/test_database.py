import pytest

from app.db.database import get_db

from uuid import uuid4

from sqlalchemy import select

from app.models.user import User

def test_get_db_rolls_back_on_exception(monkeypatch):
    events = []

    class FakeSession:
        def rollback(self):
            events.append("rollback")

        def close(self):
            events.append("close")

    monkeypatch.setattr(
        "app.db.database.SessionLocal",
        lambda: FakeSession(),
    )

    dependency = get_db()

    # Start the dependency and obtain its session.
    session = next(dependency)

    assert isinstance(session, FakeSession)

    # Simulate an exception inside a FastAPI endpoint.
    with pytest.raises(RuntimeError, match="Simulated failure"):
        dependency.throw(RuntimeError("Simulated failure"))

    # Verify rollback happens before session cleanup.
    assert events == ["rollback", "close"]


def test_postgresql_rollback_removes_uncommitted_user(db_session):
    # 1. Create a unique test user.
    email = f"rollback_{uuid4().hex}@example.com"

    user = User(
        full_name="Rollback Test User",
        email=email,
        hashed_password="test_hash_not_real_password",
    )

    # 2. Add the user to the session.
    db_session.add(user)

    # 3. Send the INSERT to PostgreSQL without committing.
    db_session.flush()

    # 4. Verify the user exists inside the transaction.
    saved_user = db_session.scalar(
        select(User).where(User.email == email)
    )

    assert saved_user is not None

    # 5. Roll back the uncommitted INSERT.
    db_session.rollback()

    # 6. Verify the user no longer exists.
    removed_user = db_session.scalar(
        select(User).where(User.email == email)
    )

    assert removed_user is None
