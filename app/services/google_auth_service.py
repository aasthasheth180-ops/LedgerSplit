from dataclasses import dataclass

from google.auth import exceptions
from google.auth.transport import requests
from google.oauth2 import id_token
from pydantic import EmailStr, TypeAdapter, ValidationError

from app.core.config import settings


class InvalidGoogleCredentialError(Exception):
    pass


class GoogleAuthUnavailableError(Exception):
    pass

@dataclass(frozen=True)
class GoogleIdentity:
    subject: str
    email: str
    full_name: str
    nonce: str | None = None


def verify_google_credential(
    credential: str,
) -> GoogleIdentity:

    if not settings.GOOGLE_CLIENT_ID:
        raise GoogleAuthUnavailableError()

    try:
        claims = id_token.verify_oauth2_token(
            credential,
            requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )

    except exceptions.TransportError as exc:
        raise GoogleAuthUnavailableError() from exc

    except (ValueError, exceptions.GoogleAuthError) as exc:
        raise InvalidGoogleCredentialError() from exc

    subject = claims.get("sub")
    email = claims.get("email")
    full_name = claims.get("name")
    nonce = claims.get("nonce")

    if nonce is not None and (
        not isinstance(nonce, str)
        or not nonce
        or len(nonce) > 255
    ):
        raise InvalidGoogleCredentialError()

    if (
        not isinstance(subject, str)
        or not subject.strip()
        or len(subject) > 255
        or not isinstance(email, str)
        or claims.get("email_verified") is not True
    ):
        raise InvalidGoogleCredentialError()

    try:
        email = str(
            TypeAdapter(EmailStr).validate_python(email)
        ).strip().lower()

    except ValidationError as exc:
        raise InvalidGoogleCredentialError() from exc

    if len(email) > 255:
        raise InvalidGoogleCredentialError()

    if not isinstance(full_name, str) or not full_name.strip():
        full_name = email.split("@")[0]

    return GoogleIdentity(
        subject=subject,
        email=email,
        full_name=full_name.strip()[:100],
        nonce=nonce,
)