from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

from sqlalchemy import select, func, delete

from app.models.user import User
from app.models.oauth_identity import OAuthIdentity

from app.services.google_auth_service import GoogleIdentity
from app.services.oauth_account_service import (
    get_or_create_google_user,
    AccountLinkRequiredError,
)
from tests.conftest import TestingSessionLocal

def test_concurrent_google_registration():
    unique_id = uuid4().hex

    identity = GoogleIdentity(
        subject=f"google-{unique_id}",
        email=f"{unique_id}@example.com",
        full_name="Concurrent Google User",
    )

    barrier = Barrier(2)

    def register():
        with TestingSessionLocal() as db:
            barrier.wait(timeout=10)

            user = get_or_create_google_user(
                db=db,
                identity=identity,
                accepted_terms=True,
            )

            return user.id

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(register)
            second = executor.submit(register)

            first_id = first.result(timeout=30)
            second_id = second.result(timeout=30)

        assert first_id == second_id

        with TestingSessionLocal() as db:
            user_count = db.scalar(
                select(func.count(User.id)).where(
                    User.email == identity.email
                )
            )

            identity_count = db.scalar(
                select(func.count(OAuthIdentity.id)).where(
                    OAuthIdentity.provider == "google",
                    OAuthIdentity.provider_subject
                    == identity.subject,
                )
            )

            assert user_count == 1
            assert identity_count == 1

    finally:
        with TestingSessionLocal() as db:
            db.execute(
                delete(User).where(
                    User.email == identity.email
                )
            )
            db.commit()


def test_concurrent_different_google_subjects_same_email():
    unique_id = uuid4().hex
    email = f"{unique_id}@example.com"

    identities = [
        GoogleIdentity(
            subject=f"google-first-{unique_id}",
            email=email,
            full_name="First Google User",
        ),
        GoogleIdentity(
            subject=f"google-second-{unique_id}",
            email=email,
            full_name="Second Google User",
        ),
    ]

    barrier = Barrier(2)

    def register(identity):
        with TestingSessionLocal() as db:
            barrier.wait(timeout=10)

            try:
                user = get_or_create_google_user(
                    db=db,
                    identity=identity,
                    accepted_terms=True,
                )

                return ("created", user.id)

            except AccountLinkRequiredError:
                return ("collision", None)

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(
                register, identities[0]
            )

            second = executor.submit(
                register, identities[1]
            )

            results = [
                first.result(timeout=30),
                second.result(timeout=30),
            ]

        statuses = sorted(
            result[0] for result in results
        )

        assert statuses == ["collision", "created"]

        with TestingSessionLocal() as db:
            users = db.scalars(
                select(User).where(User.email == email)
            ).all()

            assert len(users) == 1

            identity_count = db.scalar(
                select(func.count(OAuthIdentity.id)).where(
                    OAuthIdentity.user_id == users[0].id
                )
            )

            assert identity_count == 1

    finally:
        with TestingSessionLocal() as db:
            db.execute(
                delete(User).where(User.email == email)
            )
            db.commit()