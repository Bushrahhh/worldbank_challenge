"""
Database models for UNMAPPED Skills Signal Engine.

SQLAlchemy 2.0 async models. SQLite for demo; swap DATABASE_URL for Postgres in production.
Migrate with: python -m backend.models.db  (creates tables)
"""

import json
import os
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

_DB_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./unmapped.db")

engine = create_async_engine(_DB_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[Optional[str]] = mapped_column(String(64), unique=True, index=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(128))
    country_iso: Mapped[str] = mapped_column(String(3), default="GHA")
    education_level: Mapped[Optional[str]] = mapped_column(String(32))
    languages: Mapped[str] = mapped_column(String(256), default="en")  # JSON list
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    sessions: Mapped[list["InterviewSession"]] = relationship(back_populates="user")
    passports: Mapped[list["SkillsPassport"]] = relationship(back_populates="user")


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(32), default="active")
    # status: active | complete | abandoned
    messages: Mapped[str] = mapped_column(Text, default="[]")  # JSON list of {role, content}
    stage: Mapped[str] = mapped_column(String(32), default="greeting")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship(back_populates="sessions")

    def get_messages(self) -> list[dict]:
        return json.loads(self.messages or "[]")

    def add_message(self, role: str, content: str) -> None:
        msgs = self.get_messages()
        msgs.append({"role": role, "content": content})
        self.messages = json.dumps(msgs)


class SkillReceipt(Base):
    __tablename__ = "skill_receipts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    passport_id: Mapped[int] = mapped_column(ForeignKey("skills_passports.id"))
    skill_label: Mapped[str] = mapped_column(String(256))
    esco_code: Mapped[Optional[str]] = mapped_column(String(256))
    isco_code: Mapped[Optional[str]] = mapped_column(String(8))
    evidence_type: Mapped[str] = mapped_column(String(32), default="self_report")
    # self_report | peer_vouched | employer_verified | assessed
    verified_by: Mapped[Optional[str]] = mapped_column(String(256))
    confidence: Mapped[float] = mapped_column(Float, default=0.7)
    is_heritage_skill: Mapped[bool] = mapped_column(Boolean, default=False)
    heritage_skill_id: Mapped[Optional[str]] = mapped_column(String(64))
    evidence_text: Mapped[Optional[str]] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    passport: Mapped["SkillsPassport"] = relationship(back_populates="receipts")
    vouches: Mapped[list["PeerVouch"]] = relationship(back_populates="receipt")


class SkillsPassport(Base):
    __tablename__ = "skills_passports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    passport_uuid: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    schema_version: Mapped[str] = mapped_column(String(16), default="1.0")
    country_iso: Mapped[str] = mapped_column(String(3))
    holder_public_key: Mapped[Optional[str]] = mapped_column(Text)
    signature: Mapped[Optional[str]] = mapped_column(Text)
    context_json: Mapped[str] = mapped_column(Text, default="{}")
    issued_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="passports")
    receipts: Mapped[list["SkillReceipt"]] = relationship(
        back_populates="passport", cascade="all, delete-orphan"
    )


class PeerVouch(Base):
    __tablename__ = "peer_vouches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    receipt_id: Mapped[int] = mapped_column(ForeignKey("skill_receipts.id"))
    voucher_token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    voucher_phone_hash: Mapped[Optional[str]] = mapped_column(String(128))
    service_description: Mapped[Optional[str]] = mapped_column(String(256))
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    receipt: Mapped["SkillReceipt"] = relationship(back_populates="vouches")


async def init_db() -> None:
    """Create all tables. Called at app startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """FastAPI dependency — yields an async DB session."""
    async with AsyncSessionLocal() as session:
        yield session


if __name__ == "__main__":
    import asyncio
    asyncio.run(init_db())
    print("Database tables created at", _DB_URL)
