from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.oauth_identity import OAuthIdentity
from app.models.user import User
from app.services.google_auth_service import GoogleIdentity


class AccountLinkRequiredError(Exception):
    pass


class InactiveAccountError(Exception):
    pass


class TermsAcceptanceRequiredError(Exception):
    pass


def find_google_user(
    db: Session,
    subject: str,
) -> User | None:

    return db.scalar(
        select(User)
        .join(
            OAuthIdentity,
            OAuthIdentity.user_id == User.id,
        )
        .where(
            OAuthIdentity.provider == "google",
            OAuthIdentity.provider_subject == subject,
        )
    )


def get_or_create_google_user(
    db: Session,
    identity: GoogleIdentity,
    accepted_terms: bool = False,
) -> User:

    existing_user = find_google_user(
        db,
        identity.subject,
    )

    if existing_user is not None:
        if not existing_user.is_active:
            raise InactiveAccountError()

        return existing_user

    email_owner = db.scalar(
        select(User).where(
            User.email == identity.email
        )
    )

    if email_owner is not None:
        raise AccountLinkRequiredError()

    if not accepted_terms:
        raise TermsAcceptanceRequiredError()

    user = User(
        full_name=identity.full_name,
        email=identity.email,
        hashed_password=None,
        is_active=True,
    )

    try:
        db.add(user)
        db.flush()

        oauth_identity = OAuthIdentity(
            user_id=user.id,
            provider="google",
            provider_subject=identity.subject,
        )

        db.add(oauth_identity)
        db.commit()

    except IntegrityError:
        db.rollback()

        existing_user = find_google_user(
            db,
            identity.subject,
        )

        if existing_user is not None:
            if not existing_user.is_active:
                raise InactiveAccountError()

            return existing_user

        email_owner = db.scalar(
            select(User).where(
                User.email == identity.email
            )
        )

        if email_owner is not None:
            raise AccountLinkRequiredError()

        raise

    db.refresh(user)

    return user