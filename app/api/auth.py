from app.services.session_service import (
    create_auth_session,
    rotate_refresh_token,
    InvalidRefreshTokenError,
    revoke_auth_session,
)
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.cookies import (
    set_refresh_cookie,
    clear_refresh_cookie,
)
from app.db.database import get_db
from app.schemas.user import UserCreate, UserResponse
from app.services.user_service import (
    EmailAlreadyRegisteredError,
    create_user,
)
from datetime import datetime, timezone
from app.core.csrf import require_trusted_origin
from app.core.security import create_access_token
from app.schemas.user import UserLogin
from app.services.authentication_services import authenticate_user
from app.models.user import User
from app.schemas.user import GoogleLogin

from app.services.google_auth_service import (
    verify_google_credential,
    InvalidGoogleCredentialError,
    GoogleAuthUnavailableError,
)

from app.services.oauth_account_service import (
    get_or_create_google_user,
    link_google_account,
    AccountLinkRequiredError,
    InvalidLinkPasswordError,
    InactiveAccountError,
    TermsAcceptanceRequiredError,
)
from app.core.security import generate_refresh_token

from app.services.google_challenge_service import (
    create_google_challenge,
    consume_google_challenge,
    InvalidGoogleChallengeError,
    CHALLENGE_TTL_SECONDS,
)



router = APIRouter(prefix="/auth", tags=["Authentication"])


def create_login_response(
    db: Session,
    user: User,
    response: Response,
    remember_me: bool,
) -> dict[str, str]:

    auth_session, raw_refresh_token = create_auth_session(
        db=db,
        user_id=user.id,
        remember_me=remember_me,
    )

    access_token = create_access_token(
        user_id=user.id,
        session_id=auth_session.id,
    )

    max_age = (
        settings.REMEMBER_ME_EXPIRE_DAYS * 24 * 60 * 60
        if remember_me
        else None
    )

    set_refresh_cookie(
        response=response,
        refresh_token=raw_refresh_token,
        max_age=max_age,
    )

    response.headers["Cache-Control"] = "no-store"

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
):
    try:
        return create_user(db, user_data)
    except (EmailAlreadyRegisteredError, IntegrityError):
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

@router.post(
    "/login",
    dependencies=[Depends(require_trusted_origin)],
)
def login_user(
    credentials: UserLogin,
    response: Response,
    db: Session = Depends(get_db),
):
    user = authenticate_user(
        db=db,
        email=str(credentials.email),
        password=credentials.password,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return create_login_response(
        db=db,
        user=user,
        response=response,
        remember_me=credentials.remember_me,
    )

@router.post(
    "/google",
    dependencies=[Depends(require_trusted_origin)],
)
def google_login(
    credentials: GoogleLogin,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    try:
        identity = verify_google_credential(
            credentials.credential
        )
        browser_token = request.cookies.get(
            GOOGLE_BROWSER_COOKIE
        )

        if not identity.nonce or not browser_token:
            raise InvalidGoogleChallengeError()

        consume_google_challenge(
            db=db,
            nonce=identity.nonce,
            browser_token=browser_token,
        )

        if credentials.link_password is not None:
            user = link_google_account(
                db=db,
                identity=identity,
                password=credentials.link_password,
            )
        else:
            user = get_or_create_google_user(
                db=db,
                identity=identity,
                accepted_terms=credentials.accepted_terms,
            )

    except InvalidGoogleChallengeError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Google sign-in challenge is invalid, "
                "expired, or already used. Please try again."
            ),
        )

    except InvalidGoogleCredentialError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google credential",
        )

    except GoogleAuthUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google authentication is temporarily unavailable",
        )

    except InvalidLinkPasswordError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect LedgerSplit password. Account linking failed.",
        )
    except AccountLinkRequiredError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "An account with this email already exists. "
                "Please use your original sign-in method."
            ),
        )

    except InactiveAccountError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is inactive",
        )

    except TermsAcceptanceRequiredError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please accept the terms and privacy policy to create an account",
        )

    return create_login_response(
        db=db,
        user=user,
        response=response,
        remember_me=credentials.remember_me,
    )
GOOGLE_BROWSER_COOKIE = "ledgersplit_google_browser"


@router.post(
    "/google/challenge",
    dependencies=[Depends(require_trusted_origin)],
)
def issue_google_challenge(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google authentication is unavailable",
        )

    browser_token = request.cookies.get(
        GOOGLE_BROWSER_COOKIE
    )

    if not browser_token or len(browser_token) != 43:
        browser_token = generate_refresh_token()

    nonce = create_google_challenge(
        db=db,
        browser_token=browser_token,
    )

    response.set_cookie(
        key=GOOGLE_BROWSER_COOKIE,
        value=browser_token,
        httponly=True,
        secure=settings.REFRESH_COOKIE_SECURE,
        samesite="lax",
        path="/auth/google",
        max_age=CHALLENGE_TTL_SECONDS,
    )

    response.headers["Cache-Control"] = "no-store"

    return {
        "nonce": nonce,
        "expires_in": CHALLENGE_TTL_SECONDS,
    }

@router.post(
    "/refresh",
    dependencies=[Depends(require_trusted_origin)],
)
def refresh_access_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    raw_refresh_token = request.cookies.get(
        settings.REFRESH_COOKIE_NAME
    )

    if not raw_refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    try:
        auth_session, new_refresh_token, user = (
            rotate_refresh_token(
                db=db,
                raw_refresh_token=raw_refresh_token,
            )
        )

    except InvalidRefreshTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    access_token = create_access_token(
        user_id=user.id,
        session_id=auth_session.id,
)

    max_age = None

    if auth_session.remember_me:
        remaining_seconds = (
            auth_session.expires_at
            - datetime.now(timezone.utc)
        ).total_seconds()

        max_age = max(0, int(remaining_seconds))

    set_refresh_cookie(
        response=response,
        refresh_token=new_refresh_token,
        max_age=max_age,
    )

    response.headers["Cache-Control"] = "no-store"

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }

@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_trusted_origin)],
)
def logout_user(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):

    raw_refresh_token = request.cookies.get(
        settings.REFRESH_COOKIE_NAME
    )

    if raw_refresh_token:
        revoke_auth_session(
            db=db,
            raw_refresh_token=raw_refresh_token,
        )

    clear_refresh_cookie(response)

    response.headers["Cache-Control"] = "no-store"

    response.status_code = status.HTTP_204_NO_CONTENT

    return response