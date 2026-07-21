import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True)
    full_name = Column(String(255), nullable=True)
    phone_number = Column(String(20), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="USER")
    status = Column(String(20), nullable=False, default="ACTIVE")
    avatar_url = Column(String(500), nullable=True)

    hashed_refresh_token = Column(String(255), nullable=True)
    refresh_token_expires_at = Column(DateTime(timezone=True), nullable=True)
    failed_login_attempts = Column(Integer, nullable=False, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"
