from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


if not settings.DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not configured")


engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass



def get_db():
    db = SessionLocal()

    try:
        yield db

    except Exception:
        # Undo any uncommitted database changes if the request fails.
        db.rollback()
        raise

    finally:
        # Always release the database session and connection.
        db.close()
