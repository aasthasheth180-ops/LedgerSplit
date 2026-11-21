import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    def __init__(self):
        self.APP_NAME = os.getenv("APP_NAME", "LedgerSplit API")
        self.APP_ENV = os.getenv("APP_ENV", "development")
        self.APP_VERSION = os.getenv("APP_VERSION", "0.1.0")

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


settings = Settings()