"""
SQLAlchemy ORM models — full Postgres schema.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


# ── Users ────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tg_user_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    locale = Column(String(10), default="ru")
    timezone = Column(String(64), default="Asia/Dubai")
    status = Column(String(20), default="active")   # active | blocked
    role = Column(String(20), default="user")        # user | admin
    first_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Personalization
    custom_system_prompt = Column(Text, nullable=True)
    custom_user_template = Column(Text, nullable=True)
    summary_instructions = Column(Text, nullable=True)  # User instructions for weekly summary
    notification_time = Column(String(5), default="21:00") # "HH:MM" in user's timezone

    # Financial & Partnership
    balance = Column(Numeric(10, 2), server_default="0")
    referrer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    weekly_summary_enabled = Column(Boolean, default=False)
    limit_overrides = Column(JSONB, nullable=True) # { "entries_count": 100, ... }

    entries = relationship("JournalEntry", back_populates="user", lazy="dynamic")
    subscriptions = relationship("Subscription", back_populates="user", lazy="dynamic")
    events = relationship("Event", back_populates="user", lazy="dynamic")
    referrals = relationship("User", backref="referrer", remote_side=[id])
    affiliate_records = relationship("AffiliateRecord", back_populates="user", foreign_keys="[AffiliateRecord.user_id]")


# ── Telegram update dedup ────────────────────────────────────

class TelegramUpdate(Base):
    __tablename__ = "telegram_updates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    update_id = Column(BigInteger, unique=True, nullable=False)
    tg_user_id = Column(BigInteger, nullable=True)
    received_at = Column(DateTime(timezone=True), server_default=func.now())
    raw_update_json = Column(JSONB, nullable=True)


# ── Journal entries ──────────────────────────────────────────

class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    source_message_id = Column(BigInteger, nullable=True)
    input_type = Column(String(20), nullable=False)  # voice | audio | text
    entry_date = Column(Date, nullable=True)
    entry_time = Column(String(5), nullable=True)     # "HH:MM" or null
    raw_input_text = Column(Text, nullable=True)       # original text or null for voice
    transcript_text = Column(Text, nullable=True)      # STT result
    final_diary_text = Column(Text, nullable=True)     # formatted diary entry
    status = Column(String(20), default="processing")  # processing | ok | needs_date | error
    is_admin_entry = Column(Boolean, default=False)
    
    # Cost tracking
    usage_tokens_in = Column(Integer, default=0)
    usage_tokens_out = Column(Integer, default=0)
    usage_audio_duration = Column(Integer, default=0)  # in seconds for STT
    bot_message_id = Column(BigInteger, nullable=True) # ID of the message sent by the bot to the user
    mood = Column(String(50), nullable=True)          # mood detected by AI (happy, sad, etc.)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="entries")

    __table_args__ = (
        Index("idx_entries_user_date", "user_id", "entry_date"),
    )


# ── Provider jobs (STT/LLM observability) ────────────────────

class ProviderJob(Base):
    __tablename__ = "provider_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(UUID(as_uuid=True), unique=True, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    kind = Column(String(20), nullable=False)         # stt | llm | repair
    provider = Column(String(30), nullable=False)     # assemblyai | gemini | openai
    model = Column(String(100), nullable=True)
    provider_job_id = Column(String(255), nullable=True)
    tokens_in = Column(Integer, default=0)
    tokens_out = Column(Integer, default=0)
    duration_seconds = Column(Numeric, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), default="pending")    # pending | ok | error
    error_message = Column(Text, nullable=True)


# ── Event log ────────────────────────────────────────────────

class Event(Base):
    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    event_name = Column(String(100), nullable=False, index=True)
    payload = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="events")


# ── Plans ────────────────────────────────────────────────────

class Plan(Base):
    __tablename__ = "plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, nullable=False)  # trial, basic, pro
    name = Column(String(100), nullable=False)
    price = Column(Numeric(10, 2), default=0)
    currency = Column(String(10), default="USD")
    limits_json = Column(JSONB, default={})  # entries_per_day, stt_seconds_per_day, etc.
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ── Subscriptions ────────────────────────────────────────────

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("plans.id"), nullable=False)
    status = Column(String(20), default="trial")  # trial | active | past_due | canceled
    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="subscriptions")
    plan = relationship("Plan")


# ── Payments ─────────────────────────────────────────────────

class Payment(Base):
    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    provider = Column(String(30), nullable=False)     # telegram_stars | stripe
    provider_payment_id = Column(String(255), nullable=True)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(10), default="USD")
    status = Column(String(20), default="pending")    # pending | succeeded | failed | refunded
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ── Usage tracking ───────────────────────────────────────────

class UsageDaily(Base):
    __tablename__ = "usage_daily"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)
    entries_count = Column(Integer, default=0)
    stt_seconds = Column(Integer, default=0)
    tokens_in = Column(Integer, default=0)
    tokens_out = Column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_usage_user_date"),
    )


# ── Settings (admin-managed, encrypted secrets) ─────────────

class BotSettings(Base):
    __tablename__ = "bot_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=True)            # plain text for non-secret
    encrypted_value = Column(Text, nullable=True)  # Fernet-encrypted for secrets
    is_secret = Column(Boolean, default=False)
    version = Column(Integer, default=1)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by = Column(UUID(as_uuid=True), nullable=True)


# ── Affiliate Program ───────────────────────────────────────

class AffiliateRecord(Base):
    __tablename__ = "affiliate_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True) # The partner
    referral_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)        # The person who joined
    amount = Column(Numeric(10, 2), default=0)
    event_type = Column(String(50), nullable=False) # registration | payment
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", foreign_keys=[user_id], back_populates="affiliate_records")
    referral = relationship("User", foreign_keys=[referral_id])

