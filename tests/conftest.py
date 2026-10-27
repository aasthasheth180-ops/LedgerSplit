import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.db.database import Base, get_db
from app.main import app

# Import models so SQLAlchemy knows which tables to create.
from app.models.user import User  # noqa: F401


def validate_test_database():
    if not settings.DATABASE_URL:
        raise RuntimeError("DATABASE_URL is missing")

    if not settings.TEST_DATABASE_URL:
        raise RuntimeError("TEST_DATABASE_URL is missing")

    main_url = make_url(settings.DATABASE_URL)
    test_url = make_url(settings.TEST_DATABASE_URL)

    if test_url.database != "ledgersplit_test_db":
        raise RuntimeError("Refusing to use a non-test database")

    if main_url == test_url:
        raise RuntimeError("Test and development databases are identical")


validate_test_database()

test_engine = create_engine(
    settings.TEST_DATABASE_URL,
    poolclass=NullPool,
)

TestingSessionLocal = sessionmaker(
    bind=test_engine,
    autoflush=False,
    expire_on_commit=False,
)


@pytest.fixture
def db_session():
    # Use a transaction so test data can be rolled back.
    connection = test_engine.connect()
    transaction = connection.begin()

    session = TestingSessionLocal(
        bind=connection,
        join_transaction_mode="create_savepoint",
    )

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)