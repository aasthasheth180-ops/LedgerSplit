from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class GoogleAuthChallenge(Base):
    __tablename__ = "google_auth_challenges"

    nonce_hash: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )

    browser_token_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )