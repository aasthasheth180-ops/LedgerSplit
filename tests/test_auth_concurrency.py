from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from time import monotonic, sleep
from uuid import uuid4

import pytest

from sqlalchemy import select, text

from app.models.user import User
from app.models.auth_session import AuthSession
from app.models.refresh_token import RefreshToken

from app.core.security import hash_refresh_token

from app.services.session_service import (
    create_auth_session,
    rotate_refresh_token,
    revoke_auth_session,
    validate_refresh_token,
    InvalidRefreshTokenError,
    RefreshTokenReuseError,
)

from tests.conftest import TestingSessionLocal, test_engine


@pytest.fixture
def committed_auth_session():

    # Ensure committed tests use only the test database.
    with test_engine.connect() as connection:
        database_name = connection.execute(
            text("SELECT current_database()")
        ).scalar_one()

    assert database_name == "ledgersplit_test_db"

    user_id = None

    try:
        with TestingSessionLocal() as db:

            user = User(
                full_name="Auth Concurrency User",
                email=f"auth_concurrency_{uuid4().hex}@example.com",
                hashed_password="test_hash",
            )

            db.add(user)
            db.flush()

            user_id = user.id

            auth_session, raw_token = create_auth_session(
                db=db,
                user_id=user_id,
                remember_me=False,
            )

            session_id = auth_session.id

        yield {
            "user_id": user_id,
            "session_id": session_id,
            "raw_token": raw_token,
        }

    finally:
        # Foreign-key cascades remove sessions and refresh tokens.
        if user_id is not None:
            with TestingSessionLocal() as db:

                user = db.get(User, user_id)

                if user is not None:
                    db.delete(user)

                db.commit()


def test_committed_session_visible_across_connections(
    committed_auth_session,
):

    with TestingSessionLocal() as db:

        auth_session = db.get(
            AuthSession,
            committed_auth_session["session_id"],
        )

        assert auth_session is not None

        assert auth_session.user_id == (
            committed_auth_session["user_id"]
        )

        assert auth_session.revoked_at is None

        refresh_token = db.scalar(
            select(RefreshToken).where(
                RefreshToken.session_id == auth_session.id
            )
        )

        assert refresh_token is not None

        assert refresh_token.token_hash == hash_refresh_token(
            committed_auth_session["raw_token"]
        )

        assert refresh_token.used_at is None


def test_simultaneous_refresh_requests(
    committed_auth_session,
):

    raw_token = committed_auth_session["raw_token"]
    session_id = committed_auth_session["session_id"]

    barrier = Barrier(2, timeout=10)

    def refresh_worker():

        with TestingSessionLocal() as db:

            db.execute(
                text("SET LOCAL lock_timeout = '10s'")
            )

            db.execute(
                text("SET LOCAL statement_timeout = '15s'")
            )

            barrier.wait()

            try:
                auth_session, new_token, user = (
                    rotate_refresh_token(
                        db=db,
                        raw_refresh_token=raw_token,
                    )
                )

                return "success", new_token

            except RefreshTokenReuseError:
                return "reuse_detected", None

            except InvalidRefreshTokenError:
                return "invalid", None

    with ThreadPoolExecutor(max_workers=2) as executor:

        futures = [
            executor.submit(refresh_worker)
            for _ in range(2)
        ]

        results = [
            future.result(timeout=20)
            for future in futures
        ]

    statuses = sorted(
        result[0] for result in results
    )

    assert statuses == [
        "reuse_detected",
        "success",
    ]

    replacement_token = next(
        token
        for result, token in results
        if result == "success"
    )

    with TestingSessionLocal() as db:

        auth_session = db.get(
            AuthSession,
            session_id,
        )

        assert auth_session is not None
        assert auth_session.revoked_at is not None

        saved_tokens = db.scalars(
            select(RefreshToken).where(
                RefreshToken.session_id == session_id
            )
        ).all()

        assert len(saved_tokens) == 2

        assert sum(
            token.used_at is not None
            for token in saved_tokens
        ) == 1

        assert sum(
            token.used_at is None
            for token in saved_tokens
        ) == 1

        original_token = next(
            token
            for token in saved_tokens
            if token.token_hash == hash_refresh_token(raw_token)
        )

        assert original_token.used_at is not None

        assert any(
            token.token_hash == hash_refresh_token(
                replacement_token
            )
            for token in saved_tokens
        )

        with pytest.raises(InvalidRefreshTokenError):

            validate_refresh_token(
                db=db,
                raw_refresh_token=replacement_token,
            )

def test_concurrent_refresh_and_logout(
    committed_auth_session,
):

    raw_token = committed_auth_session["raw_token"]
    session_id = committed_auth_session["session_id"]

    barrier = Barrier(2, timeout=10)

    def refresh_worker():

        with TestingSessionLocal() as db:

            db.execute(
                text("SET LOCAL lock_timeout = '10s'")
            )

            db.execute(
                text("SET LOCAL statement_timeout = '15s'")
            )

            barrier.wait()

            try:
                auth_session, new_token, user = (
                    rotate_refresh_token(
                        db=db,
                        raw_refresh_token=raw_token,
                    )
                )

                return "success", new_token

            except InvalidRefreshTokenError:
                return "invalid", None

    def logout_worker():

        with TestingSessionLocal() as db:

            db.execute(
                text("SET LOCAL lock_timeout = '10s'")
            )

            db.execute(
                text("SET LOCAL statement_timeout = '15s'")
            )

            barrier.wait()

            return revoke_auth_session(
                db=db,
                raw_refresh_token=raw_token,
            )

    with ThreadPoolExecutor(max_workers=2) as executor:

        refresh_future = executor.submit(
            refresh_worker
        )

        logout_future = executor.submit(
            logout_worker
        )

        refresh_status, replacement_token = (
            refresh_future.result(timeout=20)
        )

        logout_result = logout_future.result(
            timeout=20
        )

    assert logout_result is True

    assert refresh_status in (
        "success",
        "invalid",
    )

    with TestingSessionLocal() as db:

        auth_session = db.get(
            AuthSession,
            session_id,
        )

        assert auth_session is not None
        assert auth_session.revoked_at is not None

        saved_tokens = db.scalars(
            select(RefreshToken).where(
                RefreshToken.session_id == session_id
            )
        ).all()

        if refresh_status == "success":

            assert replacement_token is not None
            assert len(saved_tokens) == 2

            assert sum(
                token.used_at is not None
                for token in saved_tokens
            ) == 1

            assert any(
                token.token_hash == hash_refresh_token(
                    replacement_token
                )
                and token.used_at is None
                for token in saved_tokens
            )

            with pytest.raises(InvalidRefreshTokenError):

                validate_refresh_token(
                    db=db,
                    raw_refresh_token=replacement_token,
                )

        else:

            assert replacement_token is None
            assert len(saved_tokens) == 1
            assert saved_tokens[0].used_at is None

        with pytest.raises(InvalidRefreshTokenError):

            validate_refresh_token(
                db=db,
                raw_refresh_token=raw_token,
            )

def test_simultaneous_logout_requests(
    committed_auth_session,
):

    raw_token = committed_auth_session["raw_token"]
    session_id = committed_auth_session["session_id"]

    barrier = Barrier(2, timeout=10)

    def logout_worker():

        with TestingSessionLocal() as db:

            db.execute(
                text("SET LOCAL lock_timeout = '10s'")
            )

            db.execute(
                text("SET LOCAL statement_timeout = '15s'")
            )

            barrier.wait()

            result = revoke_auth_session(
                db=db,
                raw_refresh_token=raw_token,
            )

            auth_session = db.get(
                AuthSession,
                session_id,
                populate_existing=True,
            )

            assert auth_session is not None

            return result, auth_session.revoked_at

    with ThreadPoolExecutor(max_workers=2) as executor:

        futures = [
            executor.submit(logout_worker)
            for _ in range(2)
        ]

        results = [
            future.result(timeout=20)
            for future in futures
        ]

    # Both logout requests must succeed.
    assert all(
        result is True
        for result, revoked_at in results
    )

    first_revoked_at = results[0][1]
    second_revoked_at = results[1][1]

    assert first_revoked_at is not None
    assert second_revoked_at is not None

    # Repeated logout must preserve the revocation timestamp.
    assert first_revoked_at == second_revoked_at

    with TestingSessionLocal() as db:

        auth_session = db.get(
            AuthSession,
            session_id,
        )

        assert auth_session is not None
        assert auth_session.revoked_at == first_revoked_at

        saved_tokens = db.scalars(
            select(RefreshToken).where(
                RefreshToken.session_id == session_id
            )
        ).all()

        # Logout must not create additional refresh tokens.
        assert len(saved_tokens) == 1

        assert saved_tokens[0].used_at is None

        assert saved_tokens[0].token_hash == (
            hash_refresh_token(raw_token)
        )

        with pytest.raises(InvalidRefreshTokenError):

            validate_refresh_token(
                db=db,
                raw_refresh_token=raw_token,
            )

def test_concurrent_refresh_reuse_preserves_other_session(
    committed_auth_session,
):

    user_id = committed_auth_session["user_id"]
    first_session_id = committed_auth_session["session_id"]
    first_token = committed_auth_session["raw_token"]

    # Create another session for the same user.
    with TestingSessionLocal() as db:

        second_session, second_token = create_auth_session(
            db=db,
            user_id=user_id,
            remember_me=True,
        )

        second_session_id = second_session.id
        second_expires_at = second_session.expires_at

    assert first_session_id != second_session_id

    barrier = Barrier(2, timeout=10)

    def refresh_worker():

        with TestingSessionLocal() as db:

            db.execute(
                text("SET LOCAL lock_timeout = '10s'")
            )

            db.execute(
                text("SET LOCAL statement_timeout = '15s'")
            )

            barrier.wait()

            try:
                rotate_refresh_token(
                    db=db,
                    raw_refresh_token=first_token,
                )

                return "success"

            except RefreshTokenReuseError:
                return "reuse_detected"

            except InvalidRefreshTokenError:
                return "invalid"

    with ThreadPoolExecutor(max_workers=2) as executor:

        futures = [
            executor.submit(refresh_worker)
            for _ in range(2)
        ]

        results = [
            future.result(timeout=20)
            for future in futures
        ]

    assert sorted(results) == [
        "reuse_detected",
        "success",
    ]

    with TestingSessionLocal() as db:

        first_session = db.get(
            AuthSession,
            first_session_id,
        )

        second_session = db.get(
            AuthSession,
            second_session_id,
        )

        assert first_session is not None
        assert second_session is not None

        # Only the compromised session should be revoked.
        assert first_session.revoked_at is not None
        assert second_session.revoked_at is None

        assert second_session.expires_at == second_expires_at

        # Verify the unaffected session remains valid.
        valid_session, refresh_token, user = (
            validate_refresh_token(
                db=db,
                raw_refresh_token=second_token,
            )
        )

        assert valid_session.id == second_session_id
        assert user.id == user_id
        assert refresh_token.used_at is None

        # Verify the unaffected session can still rotate.
        rotated_session, new_token, user = (
            rotate_refresh_token(
                db=db,
                raw_refresh_token=second_token,
            )
        )

        assert rotated_session.id == second_session_id
        assert new_token != second_token

    # Verify the final committed database state.
    with TestingSessionLocal() as db:

        first_session = db.get(
            AuthSession,
            first_session_id,
        )

        second_session = db.get(
            AuthSession,
            second_session_id,
        )

        assert first_session.revoked_at is not None
        assert second_session.revoked_at is None

        second_tokens = db.scalars(
            select(RefreshToken).where(
                RefreshToken.session_id == second_session_id
            )
        ).all()

        assert len(second_tokens) == 2

        assert sum(
            token.used_at is None
            for token in second_tokens
        ) == 1

        assert sum(
            token.used_at is not None
            for token in second_tokens
        ) == 1

        valid_session, _, _ = validate_refresh_token(
            db=db,
            raw_refresh_token=new_token,
        )

        assert valid_session.id == second_session_id

@pytest.mark.parametrize(
    "first_operation",
    ["refresh", "logout"],
)
def test_auth_session_row_lock_contention(
    committed_auth_session,
    first_operation,
):

    session_id = committed_auth_session["session_id"]
    raw_token = committed_auth_session["raw_token"]

    worker_started = Event()
    worker_pid = {}

    def second_worker():

        with TestingSessionLocal() as db:

            db.execute(
                text("SET LOCAL lock_timeout = '10s'")
            )

            db.execute(
                text("SET LOCAL statement_timeout = '15s'")
            )

            worker_pid["pid"] = db.scalar(
                text("SELECT pg_backend_pid()")
            )

            worker_started.set()

            try:
                rotate_refresh_token(
                    db=db,
                    raw_refresh_token=raw_token,
                )

                return "success"

            except RefreshTokenReuseError:
                return "reuse_detected"

            except InvalidRefreshTokenError:
                return "invalid"

    with ThreadPoolExecutor(max_workers=1) as executor:

        with TestingSessionLocal() as db:

            db.execute(
                text("SET LOCAL lock_timeout = '10s'")
            )

            db.execute(
                text("SET LOCAL statement_timeout = '15s'")
            )

            first_pid = db.scalar(
                text("SELECT pg_backend_pid()")
            )

            # Acquire the session row lock.
            db.execute(
                select(AuthSession)
                .where(AuthSession.id == session_id)
                .with_for_update()
            ).scalar_one()

            future = executor.submit(second_worker)

            try:
                assert worker_started.wait(timeout=5)

                # Verify actual PostgreSQL lock contention.
                blocked = False
                deadline = monotonic() + 5

                with test_engine.connect() as connection:

                    while monotonic() < deadline:

                        blocking_pids = connection.execute(
                            text(
                                "SELECT pg_blocking_pids(:pid)"
                            ),
                            {"pid": worker_pid["pid"]},
                        ).scalar_one()

                        if first_pid in blocking_pids:
                            blocked = True
                            break

                        if future.done():
                            break

                        sleep(0.05)

                assert blocked, (
                    "Refresh request did not wait "
                    "for the authentication session lock"
                )

                if first_operation == "refresh":

                    _, replacement_token, _ = (
                        rotate_refresh_token(
                            db=db,
                            raw_refresh_token=raw_token,
                        )
                    )

                    expected_result = "reuse_detected"

                else:

                    assert revoke_auth_session(
                        db=db,
                        raw_refresh_token=raw_token,
                    ) is True

                    replacement_token = None
                    expected_result = "invalid"

            finally:
                db.rollback()

        result = future.result(timeout=20)

    assert result == expected_result

    # Verify the final committed database state.
    with TestingSessionLocal() as db:

        auth_session = db.get(
            AuthSession,
            session_id,
        )

        assert auth_session is not None
        assert auth_session.revoked_at is not None

        saved_tokens = db.scalars(
            select(RefreshToken).where(
                RefreshToken.session_id == session_id
            )
        ).all()

        expected_count = (
            2 if first_operation == "refresh" else 1
        )

        assert len(saved_tokens) == expected_count

        assert sum(
            token.used_at is not None
            for token in saved_tokens
        ) == (
            1 if first_operation == "refresh" else 0
        )

        with pytest.raises(InvalidRefreshTokenError):

            validate_refresh_token(
                db=db,
                raw_refresh_token=raw_token,
            )

        if replacement_token is not None:

            with pytest.raises(InvalidRefreshTokenError):

                validate_refresh_token(
                    db=db,
                    raw_refresh_token=replacement_token,
                )