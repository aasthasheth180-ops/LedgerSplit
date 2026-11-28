import os
from urllib.parse import urlsplit

from dotenv import load_dotenv

load_dotenv()


class Settings:
    def __init__(self):
        self.APP_NAME = os.getenv("APP_NAME", "LedgerSplit API")
        self.APP_ENV = os.getenv("APP_ENV", "development")
        self.APP_VERSION = os.getenv("APP_VERSION", "0.1.0")
        self.GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()

        self.DATABASE_URL = os.getenv("DATABASE_URL")
        self.TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

        self.JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
        self.JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
        if self.JWT_SECRET_KEY is not None:
            if len(self.JWT_SECRET_KEY) < 32:
                raise ValueError(
                    "JWT_SECRET_KEY must contain at least 32 characters"
                )

        self.ACCESS_TOKEN_EXPIRE_MINUTES = int(
            os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
        )

        if self.ACCESS_TOKEN_EXPIRE_MINUTES <= 0:
            raise ValueError(
                "ACCESS_TOKEN_EXPIRE_MINUTES must be greater than zero"
            )

        if self.JWT_ALGORITHM != "HS256":
            raise ValueError("JWT_ALGORITHM must be HS256")
        if self.APP_ENV.lower() == "production":
            secret = self.JWT_SECRET_KEY or ""
            if len(secret) < 32 or len(set(secret)) < 12 or secret == "replace-with-a-long-random-secret":
                raise ValueError("Production requires a strong JWT secret")
            if not 1 <= self.ACCESS_TOKEN_EXPIRE_MINUTES <= 60:
                raise ValueError("Production access tokens must expire within 60 minutes")
            if not self.DATABASE_URL:
                raise ValueError("Production requires DATABASE_URL")

        if self.JWT_ALGORITHM != "HS256":
            raise ValueError("JWT_ALGORITHM must be HS256")
        if self.APP_ENV.lower() == "production":
            secret = self.JWT_SECRET_KEY or ""
            if len(secret) < 32 or len(set(secret)) < 12 or secret == "replace-with-a-long-random-secret":
                raise ValueError("Production requires a strong JWT secret")
            if not 1 <= self.ACCESS_TOKEN_EXPIRE_MINUTES <= 60:
                raise ValueError("Production access tokens must expire within 60 minutes")
            if not self.DATABASE_URL:
                raise ValueError("Production requires DATABASE_URL")

        # Refresh-token session configuration
        self.REFRESH_COOKIE_NAME = "ledgersplit_refresh"

        self.REFRESH_COOKIE_SECURE = self.APP_ENV.lower() != "development"

        self.REFRESH_COOKIE_SAMESITE = "lax"

        self.REFRESH_COOKIE_PATH = "/auth"

        self.SESSION_EXPIRE_DAYS = int(
            os.getenv("SESSION_EXPIRE_DAYS", "7")
        )

        self.REMEMBER_ME_EXPIRE_DAYS = int(
            os.getenv("REMEMBER_ME_EXPIRE_DAYS", "30")
        )

        if self.SESSION_EXPIRE_DAYS <= 0:
            raise ValueError(
                "SESSION_EXPIRE_DAYS must be greater than zero"
            )

        if self.REMEMBER_ME_EXPIRE_DAYS < self.SESSION_EXPIRE_DAYS:
            raise ValueError(
                "REMEMBER_ME_EXPIRE_DAYS must be at least SESSION_EXPIRE_DAYS"
            )

        # Trusted frontend origins
        self.TRUSTED_ORIGINS = [
            origin.strip()
            for origin in os.getenv(
                "TRUSTED_ORIGINS",
                "http://localhost:5173",
            ).split(",")
            if origin.strip()
        ]

        if not self.TRUSTED_ORIGINS:
            raise ValueError("TRUSTED_ORIGINS must not be empty")

        if "*" in self.TRUSTED_ORIGINS:
            raise ValueError("Wildcard trusted origins are not allowed")

        for origin in self.TRUSTED_ORIGINS:
            parsed = urlsplit(origin)

            if (
                parsed.scheme not in ("http", "https")
                or not parsed.hostname
                or parsed.username is not None
                or parsed.password is not None
                or parsed.path
                or parsed.query
                or parsed.fragment
                or origin != f"{parsed.scheme}://{parsed.netloc}"
                or any(char.isspace() for char in origin)
                or "*" in origin
            ):
                raise ValueError(
                    "TRUSTED_ORIGINS must contain valid HTTP or HTTPS origins"
                )

            _ = parsed.port
            if self.APP_ENV.lower() == "production" and parsed.scheme != "https":
                raise ValueError("Production trusted origins must use HTTPS")
            if self.APP_ENV.lower() == "production" and parsed.scheme != "https":
                raise ValueError("Production trusted origins must use HTTPS")



settings = Settings()