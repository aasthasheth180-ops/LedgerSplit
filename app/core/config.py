import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    APP_NAME = os.getenv("APP_NAME", "LedgerSplit API")
    APP_ENV = os.getenv("APP_ENV", "development")
    APP_VERSION = os.getenv("APP_VERSION", "0.1.0")

    DATABASE_URL = os.getenv("DATABASE_URL")
    JWT_SECRET_KEY: str | None = os.getenv("JWT_SECRET_KEY")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    )
    TEST_DATABASE_URL: str | None = os.getenv("TEST_DATABASE_URL")


settings = Settings()