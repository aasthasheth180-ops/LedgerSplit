from datetime import datetime, timedelta, timezone

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.security import (
    generate_refresh_token,
    hash_refresh_token,
)
from app.models.google_auth_challenge import GoogleAuthChallenge


CHALLENGE_TTL_SECONDS = 300


class InvalidGoogleChallengeError(Exception):
    pass


def create_google_challenge(
    db: Session,
    browser_token: str,
) -> str:

    now = datetime.now(timezone.utc)

    db.execute(
        delete(GoogleAuthChallenge).where(
            GoogleAuthChallenge.expires_at <= now
        )
    )

    nonce = generate_refresh_token()

    challenge = GoogleAuthChallenge(
        nonce_hash=hash_refresh_token(nonce),
        browser_token_hash=hash_refresh_token(browser_token),
        expires_at=now + timedelta(
            seconds=CHALLENGE_TTL_SECONDS
        ),
    )

    db.add(challenge)
    db.commit()

    return nonce


def consume_google_challenge(
    db: Session,
    nonce: str,
    browser_token: str,
) -> None:

    statement = (
        delete(GoogleAuthChallenge)
        .where(
            GoogleAuthChallenge.nonce_hash
            == hash_refresh_token(nonce),

            GoogleAuthChallenge.browser_token_hash
            == hash_refresh_token(browser_token),

            GoogleAuthChallenge.expires_at
            > datetime.now(timezone.utc),
        )
        .returning(GoogleAuthChallenge.nonce_hash)
    )

    consumed_nonce = db.execute(
        statement
    ).scalar_one_or_none()

    if consumed_nonce is None:
        db.rollback()
        raise InvalidGoogleChallengeError()

    db.commit()