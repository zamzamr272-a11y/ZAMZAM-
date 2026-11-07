from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Literal, Optional
from zoneinfo import ZoneInfo

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from fastapi import Depends, FastAPI, Header, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import (JSON, Boolean, Date, DateTime, Float, ForeignKey, Index, Integer,
                        Numeric, String, Text, UniqueConstraint, create_engine, func, select)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

APP_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = APP_ROOT / "frontend"
DATA_DIR = Path(os.getenv("NEXORA_DATA_DIR", APP_ROOT / "backend" / "data"))
UPLOAD_DIR = DATA_DIR / "private-uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
try:
    UPLOAD_DIR.chmod(0o700)
except OSError:
    pass
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./nexora.db")
JWT_SECRET = os.getenv("JWT_SECRET", "development-only-change-this-secret-before-deploy")
ACCESS_TTL_MINUTES = int(os.getenv("ACCESS_TTL_MINUTES", "20"))
REFRESH_TTL_DAYS = int(os.getenv("REFRESH_TTL_DAYS", "30"))
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(8 * 1024 * 1024)))
APP_TIMEZONE = ZoneInfo(os.getenv("APP_TIMEZONE", "Asia/Makassar"))
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").strip().lower()
if ENVIRONMENT == "production":
    if JWT_SECRET == "development-only-change-this-secret-before-deploy" or len(JWT_SECRET) < 64:
        raise RuntimeError("Production requires a unique JWT_SECRET of at least 64 characters.")
    if origins := [x.strip() for x in os.getenv("CORS_ORIGINS", "*").split(",") if x.strip()]:
        if "*" in origins:
            raise RuntimeError("Production CORS_ORIGINS must list explicit trusted origins; wildcard is forbidden.")

engine_kwargs: dict[str, Any] = {"pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    profile_code: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    theme: Mapped[str] = mapped_column(String(12), default="dark")

class UserSession(Base):
    __tablename__ = "user_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    refresh_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class RecoveryCode(Base):
    __tablename__ = "recovery_codes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    code_hash: Mapped[str] = mapped_column(String(64))
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

class WebSocketTicket(Base):
    __tablename__ = "websocket_tickets"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    group_id: Mapped[str] = mapped_column(ForeignKey("community_groups.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class FinancialAccount(Base):
    __tablename__ = "financial_accounts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(60))
    kind: Mapped[str] = mapped_column(String(24), default="cash")
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    currency: Mapped[str] = mapped_column(String(3), default="IDR")
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Category(Base):
    __tablename__ = "categories"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(48))
    kind: Mapped[str] = mapped_column(String(12))
    color: Mapped[str] = mapped_column(String(7), default="#42D6C5")
    icon: Mapped[str] = mapped_column(String(12), default="◈")

class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (Index("ix_transactions_user_occurred", "user_id", "occurred_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(12))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(3), default="IDR")
    source_account_id: Mapped[Optional[str]] = mapped_column(ForeignKey("financial_accounts.id"), nullable=True)
    target_account_id: Mapped[Optional[str]] = mapped_column(ForeignKey("financial_accounts.id"), nullable=True)
    category_id: Mapped[Optional[str]] = mapped_column(ForeignKey("categories.id"), nullable=True)
    description: Mapped[str] = mapped_column(String(140))
    notes: Mapped[str] = mapped_column(Text, default="")
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(16), default="confirmed")
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class Budget(Base):
    __tablename__ = "budgets"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    category_id: Mapped[str] = mapped_column(ForeignKey("categories.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    starts_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[date] = mapped_column(Date)
    threshold_percent: Mapped[int] = mapped_column(Integer, default=80)

class Goal(Base):
    __tablename__ = "goals"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    target_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    current_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    target_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    note: Mapped[str] = mapped_column(String(500), default="")
    status: Mapped[str] = mapped_column(String(16), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class RecurringRule(Base):
    __tablename__ = "recurring_rules"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(12))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(3), default="IDR")
    source_account_id: Mapped[Optional[str]] = mapped_column(ForeignKey("financial_accounts.id"), nullable=True)
    target_account_id: Mapped[Optional[str]] = mapped_column(ForeignKey("financial_accounts.id"), nullable=True)
    category_id: Mapped[Optional[str]] = mapped_column(ForeignKey("categories.id"), nullable=True)
    description: Mapped[str] = mapped_column(String(140))
    notes: Mapped[str] = mapped_column(Text, default="")
    frequency: Mapped[str] = mapped_column(String(12))
    next_run_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class RecurringExecution(Base):
    __tablename__ = "recurring_executions"
    __table_args__ = (UniqueConstraint("rule_id", "scheduled_on", name="uq_recurring_rule_date"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rule_id: Mapped[str] = mapped_column(ForeignKey("recurring_rules.id", ondelete="CASCADE"), index=True)
    scheduled_on: Mapped[date] = mapped_column(Date)
    transaction_id: Mapped[str] = mapped_column(ForeignKey("transactions.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Receipt(Base):
    __tablename__ = "receipts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    original_name: Mapped[str] = mapped_column(String(160))
    stored_path: Mapped[str] = mapped_column(String(500))
    mime_type: Mapped[str] = mapped_column(String(80))
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(24), default="uploaded")
    ocr_text: Mapped[str] = mapped_column(Text, default="")
    ocr_fields: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    ocr_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    confirmed_transaction_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

class CommunityGroup(Base):
    __tablename__ = "community_groups"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(String(320), default="")
    rules: Mapped[str] = mapped_column(Text, default="Saling menghormati dan berdiskusi dengan data.")
    invite_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class GroupMember(Base):
    __tablename__ = "group_members"
    __table_args__ = (Index("ix_group_member_group_user", "group_id", "user_id", unique=True),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    group_id: Mapped[str] = mapped_column(ForeignKey("community_groups.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(12), default="member")
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class JoinRequest(Base):
    __tablename__ = "join_requests"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    group_id: Mapped[str] = mapped_column(ForeignKey("community_groups.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(12), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (Index("ix_messages_group_created", "group_id", "created_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    group_id: Mapped[str] = mapped_column(ForeignKey("community_groups.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    body: Mapped[str] = mapped_column(String(2000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    edited_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

class MessageReaction(Base):
    __tablename__ = "message_reactions"
    __table_args__ = (UniqueConstraint("message_id", "user_id", "emoji", name="uq_message_reaction"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    message_id: Mapped[str] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    emoji: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class ContentReport(Base):
    __tablename__ = "content_reports"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    reporter_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    group_id: Mapped[str] = mapped_column(ForeignKey("community_groups.id", ondelete="CASCADE"), index=True)
    message_id: Mapped[Optional[str]] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"), nullable=True)
    reason: Mapped[str] = mapped_column(String(40))
    details: Mapped[str] = mapped_column(String(1000), default="")
    status: Mapped[str] = mapped_column(String(16), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class UserBlock(Base):
    __tablename__ = "user_blocks"
    __table_args__ = (UniqueConstraint("blocker_id", "blocked_id", name="uq_user_block"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    blocker_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    blocked_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class WatchlistItem(Base):
    __tablename__ = "watchlist_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    symbol: Mapped[str] = mapped_column(String(24))
    asset_name: Mapped[str] = mapped_column(String(80), default="")
    note: Mapped[str] = mapped_column(String(240), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class InvestmentThesis(Base):
    __tablename__ = "investment_theses"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    symbol: Mapped[str] = mapped_column(String(24))
    horizon: Mapped[str] = mapped_column(String(24))
    risk_profile: Mapped[str] = mapped_column(String(24))
    thesis: Mapped[str] = mapped_column(Text)
    risks: Mapped[str] = mapped_column(Text, default="")
    invalidation: Mapped[str] = mapped_column(Text, default="")
    optimistic_case: Mapped[str] = mapped_column(Text, default="")
    base_case: Mapped[str] = mapped_column(Text, default="")
    pessimistic_case: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class SupportTicket(Base):
    __tablename__ = "support_tickets"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    ticket_code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(24), default="baru")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

if os.getenv("AUTO_CREATE_SCHEMA", "true").lower() == "true":
    Base.metadata.create_all(bind=engine)

pwd_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

def hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")

def issue_access_token(user_id: str, session_id: str) -> str:
    header = b64url(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = b64url(json.dumps({"sub": user_id, "sid": session_id,
                                 "exp": int((now_utc() + timedelta(minutes=ACCESS_TTL_MINUTES)).timestamp())},
                                separators=(",", ":")).encode())
    body = f"{header}.{payload}"
    signature = b64url(hmac.new(JWT_SECRET.encode(), body.encode(), hashlib.sha256).digest())
    return f"{body}.{signature}"

def decode_access_token(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid token")
    body = f"{parts[0]}.{parts[1]}"
    expected = b64url(hmac.new(JWT_SECRET.encode(), body.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(expected, parts[2]):
        raise ValueError("Invalid signature")
    padding = "=" * (-len(parts[1]) % 4)
    payload = json.loads(base64.urlsafe_b64decode(parts[1] + padding))
    if int(payload.get("exp", 0)) < int(now_utc().timestamp()):
        raise ValueError("Expired token")
    return payload

def new_session(db: Session, user_id: str) -> tuple[str, str]:
    refresh = secrets.token_urlsafe(48)
    session_row = UserSession(user_id=user_id, refresh_hash=hash_secret(refresh),
                              expires_at=now_utc() + timedelta(days=REFRESH_TTL_DAYS))
    db.add(session_row)
    db.flush()
    return issue_access_token(user_id, session_row.id), refresh

def get_current_user(authorization: str = Header(default=""), db: Session = Depends(get_db)) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Silakan masuk untuk melanjutkan.")
    try:
        payload = decode_access_token(authorization[7:])
    except Exception:
        raise HTTPException(401, "Sesi tidak valid atau telah kedaluwarsa.")
    session_row = db.get(UserSession, payload.get("sid"))
    user = db.get(User, payload.get("sub"))
    if not user or not session_row or session_row.user_id != user.id or session_row.revoked_at:
        raise HTTPException(401, "Sesi telah dicabut.")
    exp = session_row.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp < now_utc():
        raise HTTPException(401, "Sesi telah kedaluwarsa.")
    return user

def serialize_account(row: FinancialAccount) -> dict[str, Any]:
    return {"id": row.id, "name": row.name, "kind": row.kind, "opening_balance": str(row.opening_balance),
            "currency": row.currency, "archived": row.archived}

def serialize_category(row: Category) -> dict[str, Any]:
    return {"id": row.id, "name": row.name, "kind": row.kind, "color": row.color, "icon": row.icon}

def serialize_transaction(row: Transaction) -> dict[str, Any]:
    return {"id": row.id, "kind": row.kind, "amount": str(row.amount), "currency": row.currency,
            "source_account_id": row.source_account_id, "target_account_id": row.target_account_id,
            "category_id": row.category_id, "description": row.description, "notes": row.notes,
            "tags": row.tags or [], "status": row.status,
            "occurred_at": row.occurred_at.isoformat(), "created_at": row.created_at.isoformat()}

def serialize_group(row: CommunityGroup, role: str | None = None) -> dict[str, Any]:
    return {"id": row.id, "name": row.name, "description": row.description, "rules": row.rules, "role": role}

def group_member(db: Session, group_id: str, user_id: str) -> Optional[GroupMember]:
    return db.scalar(select(GroupMember).where(GroupMember.group_id == group_id, GroupMember.user_id == user_id))

def require_group_member(db: Session, group_id: str, user_id: str) -> GroupMember:
    member = group_member(db, group_id, user_id)
    if not member:
        raise HTTPException(404, "Grup tidak ditemukan atau kamu belum menjadi anggota.")
    return member

def require_group_admin(db: Session, group_id: str, user_id: str) -> GroupMember:
    member = require_group_member(db, group_id, user_id)
    if member.role not in ("owner", "admin"):
        raise HTTPException(403, "Hanya owner/admin yang dapat melakukan tindakan ini.")
    return member

def parse_dt(value: datetime | str) -> datetime:
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)

def local_day_start_utc(day: date) -> datetime:
    return datetime.combine(day, datetime.min.time()).replace(tzinfo=APP_TIMEZONE).astimezone(timezone.utc)

def transaction_local_date(value: datetime) -> date:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(APP_TIMEZONE).date()

class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=10, max_length=128)
    @field_validator("username")
    @classmethod
    def normalize_username(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.fullmatch(r"[a-z0-9_]{3,32}", v):
            raise ValueError("Username hanya boleh berisi huruf kecil, angka, dan garis bawah (3–32 karakter).")
        return v

class LoginIn(BaseModel):
    username: str
    password: str

class RefreshIn(BaseModel):
    refresh_token: str

class RecoveryIn(BaseModel):
    username: str
    recovery_code: str
    new_password: str = Field(min_length=10, max_length=128)

class DeleteAccountIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    confirmation: Literal["HAPUS AKUN"]

class AccountIn(BaseModel):
    name: str = Field(min_length=2, max_length=60)
    kind: Literal["cash", "bank", "ewallet", "card", "investment"] = "cash"
    opening_balance: Decimal = Decimal("0")
    currency: str = Field(default="IDR", min_length=3, max_length=3)

class CategoryIn(BaseModel):
    name: str = Field(min_length=2, max_length=48)
    kind: Literal["income", "expense"]
    color: str = Field(default="#42D6C5", pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: str = Field(default="◈", max_length=12)

class TransactionIn(BaseModel):
    kind: Literal["income", "expense", "transfer"]
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    currency: str = Field(default="IDR", min_length=3, max_length=3)
    source_account_id: Optional[str] = None
    target_account_id: Optional[str] = None
    category_id: Optional[str] = None
    description: str = Field(min_length=1, max_length=140)
    notes: str = Field(default="", max_length=2000)
    tags: list[str] = Field(default_factory=list, max_length=12)
    occurred_at: datetime

class BudgetIn(BaseModel):
    category_id: str
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    starts_on: date
    ends_on: date
    threshold_percent: int = Field(default=80, ge=1, le=100)

class GoalIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    target_amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    current_amount: Decimal = Field(default=Decimal("0"), ge=0, max_digits=18, decimal_places=2)
    target_date: Optional[date] = None
    note: str = Field(default="", max_length=500)

class RecurringIn(BaseModel):
    kind: Literal["income", "expense", "transfer"]
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    currency: str = Field(default="IDR", min_length=3, max_length=3)
    source_account_id: Optional[str] = None
    target_account_id: Optional[str] = None
    category_id: Optional[str] = None
    description: str = Field(min_length=1, max_length=140)
    notes: str = Field(default="", max_length=2000)
    frequency: Literal["daily", "weekly", "monthly", "yearly"]
    next_run_on: date
    ends_on: Optional[date] = None

class GroupPatchIn(BaseModel):
    name: str = Field(min_length=3, max_length=80)
    description: str = Field(default="", max_length=320)
    rules: str = Field(default="", max_length=2000)

class MessagePatchIn(BaseModel):
    body: str = Field(min_length=1, max_length=2000)

class ReactionIn(BaseModel):
    emoji: Literal["👍", "❤️", "😂", "👏", "🙏", "🔥", "💡"]

class ContentReportIn(BaseModel):
    reason: Literal["spam", "harassment", "scam", "misinformation", "other"]
    details: str = Field(default="", max_length=1000)

class ContentReportPatchIn(BaseModel):
    status: Literal["reviewing", "resolved", "dismissed"]
    moderator_note: str = Field(default="", max_length=1000)

class RoleIn(BaseModel):
    role: Literal["admin", "member"]

class GroupIn(BaseModel):
    name: str = Field(min_length=3, max_length=80)
    description: str = Field(default="", max_length=320)
    rules: str = Field(default="Saling menghormati dan berdiskusi dengan data.", max_length=2000)

class JoinRequestIn(BaseModel):
    invite_code: str = Field(min_length=8, max_length=80)

class MessageIn(BaseModel):
    body: str = Field(min_length=1, max_length=2000)

class WatchlistIn(BaseModel):
    symbol: str = Field(min_length=1, max_length=24)
    asset_name: str = Field(default="", max_length=80)
    note: str = Field(default="", max_length=240)

class ThesisIn(BaseModel):
    symbol: str = Field(min_length=1, max_length=24)
    horizon: str = Field(min_length=2, max_length=24)
    risk_profile: str = Field(min_length=2, max_length=24)
    thesis: str = Field(min_length=10, max_length=4000)
    risks: str = Field(default="", max_length=3000)
    invalidation: str = Field(default="", max_length=2000)
    optimistic_case: str = Field(default="", max_length=1200)
    base_case: str = Field(default="", max_length=1200)
    pessimistic_case: str = Field(default="", max_length=1200)

class SupportIn(BaseModel):
    category: str = Field(min_length=2, max_length=32)
    title: str = Field(min_length=4, max_length=120)
    description: str = Field(min_length=10, max_length=4000)

class ReceiptUploadIn(BaseModel):
    filename: str = Field(min_length=1, max_length=160)
    mime_type: str = Field(min_length=3, max_length=80)
    content_base64: str

class ReceiptConfirmIn(BaseModel):
    kind: Literal["income", "expense"]
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    occurred_at: datetime
    account_id: str
    category_id: str
    description: str = Field(min_length=1, max_length=140)

app = FastAPI(title="NEXORA API", version="0.1.0", description="API MVP NEXORA — finance, reporting, groups, investment journal and support")
origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "*").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False,
                   allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
                   allow_headers=["Authorization", "Content-Type", "Idempotency-Key"])

_auth_attempts: dict[str, list[datetime]] = {}
@app.middleware("http")
async def auth_rate_guard(request, call_next):
    if request.url.path in ("/api/v1/auth/login", "/api/v1/auth/register", "/api/v1/auth/recovery/redeem"):
        ip = request.client.host if request.client else "unknown"
        now = now_utc()
        attempts = [t for t in _auth_attempts.get(ip, []) if (now - t).total_seconds() < 60]
        if len(attempts) >= int(os.getenv("AUTH_RATE_LIMIT_PER_MINUTE", "12")):
            return JSONResponse(status_code=429, content={"detail": "Terlalu banyak percobaan. Coba lagi setelah satu menit."})
        attempts.append(now); _auth_attempts[ip] = attempts
    return await call_next(request)

@app.get("/health")
def health():
    return {"status": "ok", "service": "nexora-api", "time": now_utc().isoformat()}

@app.post("/api/v1/auth/register", status_code=201)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.username == data.username)):
        raise HTTPException(409, "Username sudah digunakan.")
    recovery_code = f"NX-{secrets.token_hex(3).upper()}-{secrets.token_hex(3).upper()}-{secrets.token_hex(3).upper()}"
    user = User(username=data.username, password_hash=pwd_hasher.hash(data.password),
                profile_code=f"NX-{secrets.token_hex(5).upper()}")
    db.add(user)
    db.flush()
    db.add(RecoveryCode(user_id=user.id, code_hash=hash_secret(recovery_code)))
    db.add(FinancialAccount(user_id=user.id, name="Tunai", kind="cash", opening_balance=Decimal("0")))
    db.add(FinancialAccount(user_id=user.id, name="Rekening utama", kind="bank", opening_balance=Decimal("0")))
    for name, kind, color, icon in [
        ("Gaji", "income", "#39C98A", "↗"), ("Usaha", "income", "#42D6C5", "◈"),
        ("Freelance", "income", "#63B7E8", "✦"), ("Lainnya", "income", "#A78BFA", "＋"),
        ("Makanan", "expense", "#F2B35E", "◒"), ("Transportasi", "expense", "#63B7E8", "↗"),
        ("Tagihan", "expense", "#F16D72", "▤"), ("Belanja", "expense", "#A78BFA", "◇"),
        ("Hiburan", "expense", "#E28BC4", "♫"), ("Lainnya", "expense", "#98A8B4", "•••")]:
        db.add(Category(user_id=user.id, name=name, kind=kind, color=color, icon=icon))
    access, refresh = new_session(db, user.id)
    db.commit()
    return {"user": {"id": user.id, "username": user.username, "profile_code": user.profile_code},
            "access_token": access, "refresh_token": refresh, "token_type": "bearer",
            "recovery_code": recovery_code,
            "recovery_warning": "Simpan recovery code ini sekarang. Kode hanya ditampilkan sekali; tanpa password dan kode ini akun mungkin tidak dapat dipulihkan."}

@app.post("/api/v1/auth/login")
def login(data: LoginIn, db: Session = Depends(get_db)):
    username = data.username.strip().lower()
    user = db.scalar(select(User).where(User.username == username))
    if not user:
        raise HTTPException(401, "Username atau password salah.")
    try:
        pwd_hasher.verify(user.password_hash, data.password)
    except (VerifyMismatchError, VerificationError):
        raise HTTPException(401, "Username atau password salah.")
    if pwd_hasher.check_needs_rehash(user.password_hash):
        user.password_hash = pwd_hasher.hash(data.password)
    access, refresh = new_session(db, user.id)
    db.commit()
    return {"user": {"id": user.id, "username": user.username, "profile_code": user.profile_code},
            "access_token": access, "refresh_token": refresh, "token_type": "bearer"}

@app.post("/api/v1/auth/refresh")
def refresh_session(data: RefreshIn, db: Session = Depends(get_db)):
    row = db.scalar(select(UserSession).where(UserSession.refresh_hash == hash_secret(data.refresh_token)))
    if not row or row.revoked_at:
        raise HTTPException(401, "Refresh token tidak valid atau telah dipakai.")
    expiry = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=timezone.utc)
    if expiry < now_utc():
        row.revoked_at = now_utc(); db.commit()
        raise HTTPException(401, "Sesi telah kedaluwarsa.")
    user_id, session_id = row.user_id, row.id
    new_refresh = secrets.token_urlsafe(48)
    row.refresh_hash = hash_secret(new_refresh)
    row.expires_at = now_utc() + timedelta(days=REFRESH_TTL_DAYS)
    db.commit()
    return {"access_token": issue_access_token(user_id, session_id), "refresh_token": new_refresh, "token_type": "bearer"}

@app.post("/api/v1/auth/logout")
def logout(user: User = Depends(get_current_user), authorization: str = Header(default=""), db: Session = Depends(get_db)):
    try:
        payload = decode_access_token(authorization[7:])
        row = db.get(UserSession, payload["sid"])
        if row and row.user_id == user.id:
            row.revoked_at = now_utc(); db.commit()
    except Exception:
        pass
    return {"ok": True}

@app.post("/api/v1/auth/recovery/redeem")
def redeem_recovery(data: RecoveryIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == data.username.strip().lower()))
    if not user:
        raise HTTPException(400, "Recovery code tidak valid.")
    row = db.scalar(select(RecoveryCode).where(RecoveryCode.user_id == user.id))
    if not row or row.used_at or not hmac.compare_digest(row.code_hash, hash_secret(data.recovery_code.strip().upper())):
        raise HTTPException(400, "Recovery code tidak valid atau telah digunakan.")
    new_code = f"NX-{secrets.token_hex(3).upper()}-{secrets.token_hex(3).upper()}-{secrets.token_hex(3).upper()}"
    user.password_hash = pwd_hasher.hash(data.new_password)
    row.code_hash = hash_secret(new_code); row.used_at = None
    for sess in db.scalars(select(UserSession).where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))):
        sess.revoked_at = now_utc()
    db.commit()
    return {"ok": True, "new_recovery_code": new_code,
            "warning": "Simpan kode pemulihan baru. Semua sesi lama telah dicabut."}

@app.get("/api/v1/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "username": user.username, "profile_code": user.profile_code,
            "theme": user.theme, "created_at": user.created_at.isoformat()}

@app.patch("/api/v1/me")
def update_me(data: dict[str, Any], user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if "theme" in data:
        if data["theme"] not in ("dark", "light"):
            raise HTTPException(422, "Tema tidak valid.")
        user.theme = data["theme"]
    db.commit()
    return me(user)

@app.get("/api/v1/accounts")
def list_accounts(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(FinancialAccount).where(FinancialAccount.user_id == user.id).order_by(FinancialAccount.created_at)).all()
    result = []
    for row in rows:
        balance = Decimal(row.opening_balance or 0)
        for tx in db.scalars(select(Transaction).where(Transaction.user_id == user.id, Transaction.status == "confirmed")):
            if tx.kind == "transfer":
                if tx.source_account_id == row.id: balance -= tx.amount
                if tx.target_account_id == row.id: balance += tx.amount
            elif tx.source_account_id == row.id:
                balance += tx.amount if tx.kind == "income" else -tx.amount
        result.append({**serialize_account(row), "balance": str(balance)})
    return result

@app.post("/api/v1/accounts", status_code=201)
def create_account(data: AccountIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = FinancialAccount(user_id=user.id, name=data.name.strip(), kind=data.kind,
                           opening_balance=data.opening_balance, currency=data.currency.upper())
    db.add(row); db.commit(); db.refresh(row)
    return serialize_account(row)

@app.get("/api/v1/categories")
def list_categories(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [serialize_category(x) for x in db.scalars(select(Category).where(Category.user_id == user.id).order_by(Category.kind, Category.name)).all()]

@app.post("/api/v1/categories", status_code=201)
def create_category(data: CategoryIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = Category(user_id=user.id, name=data.name.strip(), kind=data.kind, color=data.color, icon=data.icon)
    db.add(row); db.commit(); db.refresh(row)
    return serialize_category(row)

def validate_transaction_links(data: TransactionIn, user: User, db: Session):
    if data.kind in ("income", "expense"):
        account = db.get(FinancialAccount, data.source_account_id) if data.source_account_id else None
        if not account or account.user_id != user.id or account.archived:
            raise HTTPException(422, "Pilih akun aktif yang valid.")
        category = db.get(Category, data.category_id) if data.category_id else None
        if not category or category.user_id != user.id or category.kind != data.kind:
            raise HTTPException(422, "Pilih kategori sesuai jenis transaksi.")
        if data.target_account_id:
            raise HTTPException(422, "Transaksi pemasukan/pengeluaran tidak boleh memiliki akun tujuan.")
    else:
        source = db.get(FinancialAccount, data.source_account_id) if data.source_account_id else None
        target = db.get(FinancialAccount, data.target_account_id) if data.target_account_id else None
        if (not source or not target or source.user_id != user.id or target.user_id != user.id
                or source.archived or target.archived or source.id == target.id):
            raise HTTPException(422, "Akun asal dan tujuan transfer harus aktif, berbeda, dan milikmu.")
        if data.category_id:
            raise HTTPException(422, "Transfer internal tidak memakai kategori income/expense.")

def make_transaction(data: TransactionIn, user: User, db: Session) -> Transaction:
    validate_transaction_links(data, user, db)
    row = Transaction(user_id=user.id, kind=data.kind, amount=data.amount, currency=data.currency.upper(),
                      source_account_id=data.source_account_id, target_account_id=data.target_account_id,
                      category_id=data.category_id, description=data.description.strip(), notes=data.notes,
                      tags=[str(t)[:32] for t in data.tags[:12]], status="confirmed", occurred_at=parse_dt(data.occurred_at))
    db.add(row); db.flush()
    return row

@app.get("/api/v1/transactions")
def list_transactions(start: Optional[date] = None, end: Optional[date] = None,
                      kind: Optional[str] = None, q: Optional[str] = None, limit: int = Query(100, ge=1, le=300),
                      offset: int = Query(0, ge=0), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = select(Transaction).where(Transaction.user_id == user.id, Transaction.status == "confirmed")
    if start: stmt = stmt.where(Transaction.occurred_at >= local_day_start_utc(start))
    if end: stmt = stmt.where(Transaction.occurred_at < local_day_start_utc(end + timedelta(days=1)))
    if kind in ("income", "expense", "transfer"): stmt = stmt.where(Transaction.kind == kind)
    if q: stmt = stmt.where(Transaction.description.ilike(f"%{q[:80]}%"))
    stmt = stmt.order_by(Transaction.occurred_at.desc()).limit(limit).offset(offset)
    return [serialize_transaction(x) for x in db.scalars(stmt).all()]

@app.post("/api/v1/transactions", status_code=201)
def create_transaction(data: TransactionIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = make_transaction(data, user, db); db.commit(); db.refresh(row)
    return serialize_transaction(row)

@app.get("/api/v1/transactions/{transaction_id}")
def get_transaction(transaction_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(Transaction, transaction_id)
    if not row or row.user_id != user.id: raise HTTPException(404, "Transaksi tidak ditemukan.")
    return serialize_transaction(row)

@app.patch("/api/v1/transactions/{transaction_id}")
def patch_transaction(transaction_id: str, data: TransactionIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(Transaction, transaction_id)
    if not row or row.user_id != user.id: raise HTTPException(404, "Transaksi tidak ditemukan.")
    validate_transaction_links(data, user, db)
    row.kind, row.amount, row.currency = data.kind, data.amount, data.currency.upper()
    row.source_account_id, row.target_account_id, row.category_id = data.source_account_id, data.target_account_id, data.category_id
    row.description, row.notes, row.tags, row.occurred_at = data.description.strip(), data.notes, data.tags[:12], parse_dt(data.occurred_at)
    db.commit(); db.refresh(row)
    return serialize_transaction(row)

@app.delete("/api/v1/transactions/{transaction_id}")
def delete_transaction(transaction_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(Transaction, transaction_id)
    if not row or row.user_id != user.id: raise HTTPException(404, "Transaksi tidak ditemukan.")
    row.status = "void"; db.commit()
    return {"ok": True}

@app.get("/api/v1/reports/summary")
def report_summary(start: Optional[date] = None, end: Optional[date] = None,
                   user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = select(Transaction).where(Transaction.user_id == user.id, Transaction.status == "confirmed")
    if start: stmt = stmt.where(Transaction.occurred_at >= local_day_start_utc(start))
    if end: stmt = stmt.where(Transaction.occurred_at < local_day_start_utc(end + timedelta(days=1)))
    txs = db.scalars(stmt.order_by(Transaction.occurred_at.desc())).all()
    income = sum((x.amount for x in txs if x.kind == "income"), Decimal("0"))
    expense = sum((x.amount for x in txs if x.kind == "expense"), Decimal("0"))
    top: dict[str, Decimal] = {}
    for tx in txs:
        if tx.kind == "expense" and tx.category_id:
            cat = db.get(Category, tx.category_id)
            key = cat.name if cat else "Lainnya"
            top[key] = top.get(key, Decimal("0")) + tx.amount
    top_category = max(top.items(), key=lambda x: x[1]) if top else ("Belum ada", Decimal("0"))
    accounts = db.scalars(select(FinancialAccount).where(FinancialAccount.user_id == user.id, FinancialAccount.archived.is_(False))).all()
    balance = Decimal("0")
    for a in accounts:
        balance += Decimal(a.opening_balance or 0)
    for tx in db.scalars(select(Transaction).where(Transaction.user_id == user.id, Transaction.status == "confirmed")):
        if tx.kind == "income":
            for a in accounts:
                if a.id == tx.source_account_id: balance += tx.amount
        elif tx.kind == "expense":
            for a in accounts:
                if a.id == tx.source_account_id: balance -= tx.amount
        else:
            for a in accounts:
                if a.id == tx.source_account_id: balance -= tx.amount
                if a.id == tx.target_account_id: balance += tx.amount
    budget_stmt = select(Budget).where(Budget.user_id == user.id)
    if start: budget_stmt = budget_stmt.where(Budget.ends_on >= start)
    if end: budget_stmt = budget_stmt.where(Budget.starts_on <= end)
    budgets = db.scalars(budget_stmt).all()
    budget_total = sum((b.amount for b in budgets), Decimal("0"))
    spent = Decimal("0")
    for tx in txs:
        if tx.kind == "expense" and tx.category_id:
            for b in budgets:
                if b.category_id == tx.category_id and (not start or transaction_local_date(tx.occurred_at) >= b.starts_on) and (not end or transaction_local_date(tx.occurred_at) <= b.ends_on):
                    spent += tx.amount
    return {"income": str(income), "expense": str(expense), "net_cashflow": str(income - expense),
            "recorded_balance": str(balance), "budget_remaining": str(budget_total - spent),
            "top_category": {"name": top_category[0], "amount": str(top_category[1])},
            "transaction_count": len(txs), "period": {"start": start.isoformat() if start else None, "end": end.isoformat() if end else None}}

@app.get("/api/v1/reports/categories")
def report_categories(start: Optional[date] = None, end: Optional[date] = None,
                      user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    txs = db.scalars(select(Transaction).where(Transaction.user_id == user.id, Transaction.kind == "expense", Transaction.status == "confirmed")).all()
    buckets: dict[str, Decimal] = {}
    for tx in txs:
        local_day = transaction_local_date(tx.occurred_at)
        if start and local_day < start: continue
        if end and local_day > end: continue
        cat = db.get(Category, tx.category_id) if tx.category_id else None
        name = cat.name if cat else "Lainnya"
        buckets[name] = buckets.get(name, Decimal("0")) + tx.amount
    total = sum(buckets.values(), Decimal("0"))
    return [{"name": k, "amount": str(v), "percent": round(float(v / total * 100), 2) if total else 0} for k, v in sorted(buckets.items(), key=lambda x: x[1], reverse=True)]

@app.get("/api/v1/reports/cashflow")
def report_cashflow(start: Optional[date] = None, end: Optional[date] = None,
                    bucket: Literal["day", "week", "month", "year"] = "day",
                    user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    txs = db.scalars(select(Transaction).where(Transaction.user_id == user.id, Transaction.status == "confirmed")).all()
    buckets: dict[str, dict[str, Decimal]] = {}
    for tx in txs:
        d = transaction_local_date(tx.occurred_at)
        if start and d < start: continue
        if end and d > end: continue
        if bucket == "year": key = d.strftime("%Y")
        elif bucket == "month": key = d.strftime("%Y-%m")
        elif bucket == "week": key = f"{d.isocalendar().year}-W{d.isocalendar().week:02d}"
        else: key = d.isoformat()
        buckets.setdefault(key, {"income": Decimal("0"), "expense": Decimal("0")})
        if tx.kind == "income": buckets[key]["income"] += tx.amount
        elif tx.kind == "expense": buckets[key]["expense"] += tx.amount
    return [{"period": k, "income": str(v["income"]), "expense": str(v["expense"]), "net": str(v["income"] - v["expense"])}
            for k, v in sorted(buckets.items())]

@app.get("/api/v1/budgets")
def list_budgets(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Budget).where(Budget.user_id == user.id).order_by(Budget.starts_on.desc())).all()
    out = []
    for b in rows:
        c = db.get(Category, b.category_id)
        txs = db.scalars(select(Transaction).where(
            Transaction.user_id == user.id, Transaction.kind == "expense",
            Transaction.category_id == b.category_id, Transaction.status == "confirmed"
        )).all()
        spent = sum((tx.amount for tx in txs if b.starts_on <= transaction_local_date(tx.occurred_at) <= b.ends_on), Decimal("0"))
        amount = Decimal(b.amount)
        percent = (spent / amount * 100) if amount else Decimal("0")
        out.append({"id": b.id, "category_id": b.category_id, "category": c.name if c else "Lainnya",
                    "amount": str(amount), "spent": str(spent), "remaining": str(amount-spent),
                    "percent": round(float(percent), 2), "threshold_percent": b.threshold_percent,
                    "threshold_reached": percent >= b.threshold_percent, "over_budget": spent > amount,
                    "starts_on": b.starts_on.isoformat(), "ends_on": b.ends_on.isoformat()})
    return out

@app.post("/api/v1/budgets", status_code=201)
def create_budget(data: BudgetIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cat = db.get(Category, data.category_id)
    if not cat or cat.user_id != user.id or cat.kind != "expense": raise HTTPException(422, "Kategori anggaran harus kategori pengeluaran milikmu.")
    if data.ends_on < data.starts_on: raise HTTPException(422, "Tanggal akhir harus setelah tanggal awal.")
    row = Budget(user_id=user.id, category_id=data.category_id, amount=data.amount, starts_on=data.starts_on,
                 ends_on=data.ends_on, threshold_percent=data.threshold_percent)
    db.add(row); db.commit(); db.refresh(row)
    return {"id": row.id, "amount": str(row.amount), "category_id": row.category_id}

@app.post("/api/v1/receipts", status_code=201)
def upload_receipt(data: ReceiptUploadIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    filename = Path(data.filename).name
    ext = Path(filename).suffix.lower()
    allowed = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".pdf": "application/pdf"}
    if ext not in allowed or data.mime_type.lower() != allowed[ext]: raise HTTPException(415, "Hanya JPG, PNG, atau PDF yang didukung.")
    try: raw = base64.b64decode(data.content_base64, validate=True)
    except Exception: raise HTTPException(422, "Data berkas tidak valid.")
    if not raw or len(raw) > MAX_UPLOAD_BYTES: raise HTTPException(413, "Ukuran berkas maksimal 8 MB.")
    magic_ok = (ext in (".jpg", ".jpeg") and raw.startswith(b"\xff\xd8\xff")) or (ext == ".png" and raw.startswith(b"\x89PNG\r\n\x1a\n")) or (ext == ".pdf" and raw.startswith(b"%PDF-"))
    if not magic_ok: raise HTTPException(415, "Isi file tidak cocok dengan tipe yang dipilih.")
    digest = hashlib.sha256(raw).hexdigest()
    duplicate = db.scalar(select(Receipt).where(Receipt.user_id == user.id, Receipt.sha256 == digest))
    if duplicate: raise HTTPException(409, "Berkas ini sudah pernah diunggah.")
    path = UPLOAD_DIR / user.id
    path.mkdir(parents=True, exist_ok=True)
    stored = path / f"{uuid.uuid4().hex}{ext}"
    stored.write_bytes(raw)
    try:
        stored.chmod(0o600)
    except OSError:
        stored.unlink(missing_ok=True)
        raise HTTPException(500, "Gagal mengamankan dokumen yang diunggah.")
    row = Receipt(user_id=user.id, original_name=filename, stored_path=str(stored), mime_type=allowed[ext], sha256=digest, status="uploaded")
    db.add(row); db.commit(); db.refresh(row)
    return {"id": row.id, "filename": row.original_name, "status": row.status,
            "message": "Berkas tersimpan privat. Jalankan ekstraksi OCR untuk membuat saran draft, lalu tinjau sebelum konfirmasi.",
            "extract_url": f"/receipts/{row.id}/extract"}

@app.get("/api/v1/receipts/{receipt_id}")
def get_receipt(receipt_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(Receipt, receipt_id)
    if not row or row.user_id != user.id: raise HTTPException(404, "Dokumen tidak ditemukan.")
    return {"id": row.id, "filename": row.original_name, "status": row.status,
            "fields": row.ocr_fields or {}, "confidence": row.ocr_confidence,
            "created_at": row.created_at.isoformat()}

@app.post("/api/v1/receipts/{receipt_id}/confirm")
def confirm_receipt(receipt_id: str, data: ReceiptConfirmIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Serialize confirmations on databases that support row-level locks. The
    # already-confirmed check makes retries idempotent after network timeouts.
    row = db.scalar(select(Receipt).where(Receipt.id == receipt_id).with_for_update())
    if not row or row.user_id != user.id: raise HTTPException(404, "Dokumen tidak ditemukan.")
    if row.confirmed_transaction_id: return {"ok": True, "transaction_id": row.confirmed_transaction_id, "already_confirmed": True}
    tx_in = TransactionIn(kind=data.kind, amount=data.amount, currency="IDR", source_account_id=data.account_id,
                          category_id=data.category_id, description=data.description, occurred_at=data.occurred_at)
    tx = make_transaction(tx_in, user, db)
    row.status = "confirmed"; row.confirmed_transaction_id = tx.id
    db.commit(); db.refresh(tx)
    return {"ok": True, "transaction": serialize_transaction(tx)}

@app.delete("/api/v1/receipts/{receipt_id}")
def delete_receipt(receipt_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(Receipt, receipt_id)
    if not row or row.user_id != user.id: raise HTTPException(404, "Dokumen tidak ditemukan.")
    try: Path(row.stored_path).unlink(missing_ok=True)
    except OSError: pass
    db.delete(row); db.commit()
    return {"ok": True}

@app.post("/api/v1/groups", status_code=201)
def create_group(data: GroupIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    code = f"NXG-{secrets.token_urlsafe(8).upper()}"
    row = CommunityGroup(owner_id=user.id, name=data.name.strip(), description=data.description,
                         rules=data.rules, invite_hash=hash_secret(code))
    db.add(row); db.flush()
    db.add(GroupMember(group_id=row.id, user_id=user.id, role="owner"))
    db.commit(); db.refresh(row)
    return {**serialize_group(row, "owner"), "invite_code": code}

@app.get("/api/v1/groups")
def list_groups(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    members = db.scalars(select(GroupMember).where(GroupMember.user_id == user.id)).all()
    out = []
    for m in members:
        group = db.get(CommunityGroup, m.group_id)
        if group: out.append(serialize_group(group, m.role))
    return out

@app.get("/api/v1/groups/preview/{invite_code}")
def preview_group(invite_code: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    group = db.scalar(select(CommunityGroup).where(CommunityGroup.invite_hash == hash_secret(invite_code.strip())))
    if not group: raise HTTPException(404, "Kode grup tidak valid atau telah dicabut.")
    owner = db.get(User, group.owner_id)
    return {"id": group.id, "name": group.name, "description": group.description,
            "rules": group.rules, "owner_username": owner.username if owner else "Owner"}

@app.post("/api/v1/groups/join-requests", status_code=201)
def request_group_join(data: JoinRequestIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    group = db.scalar(select(CommunityGroup).where(CommunityGroup.invite_hash == hash_secret(data.invite_code.strip())))
    if not group: raise HTTPException(404, "Kode grup tidak valid.")
    if group_member(db, group.id, user.id): raise HTTPException(409, "Kamu sudah menjadi anggota grup ini.")
    old = db.scalar(select(JoinRequest).where(JoinRequest.group_id == group.id, JoinRequest.user_id == user.id, JoinRequest.status == "pending"))
    if old: return {"id": old.id, "status": old.status, "message": "Permintaanmu masih menunggu persetujuan."}
    row = JoinRequest(group_id=group.id, user_id=user.id, status="pending")
    db.add(row); db.commit(); db.refresh(row)
    return {"id": row.id, "status": row.status, "message": "Permintaan bergabung terkirim."}

@app.get("/api/v1/groups/{group_id}/requests")
def list_join_requests(group_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_group_admin(db, group_id, user.id)
    rows = db.scalars(select(JoinRequest).where(JoinRequest.group_id == group_id, JoinRequest.status == "pending")).all()
    return [{"id": r.id, "username": (db.get(User, r.user_id).username if db.get(User, r.user_id) else "Pengguna"), "created_at": r.created_at.isoformat()} for r in rows]

@app.post("/api/v1/groups/{group_id}/requests/{request_id}/approve")
def approve_join(group_id: str, request_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_group_admin(db, group_id, user.id)
    row = db.get(JoinRequest, request_id)
    if not row or row.group_id != group_id or row.status != "pending": raise HTTPException(404, "Permintaan tidak ditemukan.")
    if not group_member(db, group_id, row.user_id): db.add(GroupMember(group_id=group_id, user_id=row.user_id, role="member"))
    row.status = "approved"; db.commit()
    return {"ok": True, "status": row.status}

@app.post("/api/v1/groups/{group_id}/requests/{request_id}/reject")
def reject_join(group_id: str, request_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_group_admin(db, group_id, user.id)
    row = db.get(JoinRequest, request_id)
    if not row or row.group_id != group_id or row.status != "pending": raise HTTPException(404, "Permintaan tidak ditemukan.")
    row.status = "rejected"; db.commit()
    return {"ok": True, "status": row.status}

@app.get("/api/v1/groups/{group_id}/messages")
def list_messages(group_id: str, limit: int = Query(80, ge=1, le=200), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_group_member(db, group_id, user.id)
    rows = db.scalars(select(Message).where(Message.group_id == group_id).order_by(Message.created_at.desc()).limit(limit)).all()
    rows.reverse()
    blocked_ids = set(db.scalars(select(UserBlock.blocked_id).where(UserBlock.blocker_id == user.id)).all())
    output = []
    for r in rows:
        if r.user_id in blocked_ids:
            continue
        author = db.get(User, r.user_id)
        reactions = db.execute(select(MessageReaction.emoji, func.count(MessageReaction.id)).where(
            MessageReaction.message_id == r.id).group_by(MessageReaction.emoji)).all()
        output.append({"id": r.id, "user_id": r.user_id, "username": author.username if author else "Pengguna",
             "body": "Pesan telah dihapus" if r.deleted_at else r.body, "deleted": bool(r.deleted_at),
             "created_at": r.created_at.isoformat(), "edited": bool(r.edited_at),
             "reactions": [{"emoji": emoji, "count": count} for emoji, count in reactions]})
    return output

@app.post("/api/v1/groups/{group_id}/ws-ticket")
def create_group_ws_ticket(group_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_group_member(db, group_id, user.id)
    ticket = secrets.token_urlsafe(32)
    row = WebSocketTicket(user_id=user.id, group_id=group_id, token_hash=hash_secret(ticket),
                          expires_at=now_utc() + timedelta(seconds=60))
    db.add(row); db.commit()
    return {"ticket": ticket, "expires_in": 60, "single_use": True}


class ConnectionHub:
    def __init__(self): self.connections: dict[str, set[WebSocket]] = {}
    async def connect(self, group_id: str, websocket: WebSocket):
        await websocket.accept(); self.connections.setdefault(group_id, set()).add(websocket)
    def disconnect(self, group_id: str, websocket: WebSocket):
        self.connections.get(group_id, set()).discard(websocket)
    async def broadcast(self, group_id: str, payload: dict[str, Any]):
        dead = []
        for ws in list(self.connections.get(group_id, set())):
            try: await ws.send_json(payload)
            except Exception: dead.append(ws)
        for ws in dead: self.disconnect(group_id, ws)
hub = ConnectionHub()

@app.post("/api/v1/groups/{group_id}/messages", status_code=201)
async def create_message(group_id: str, data: MessageIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_group_member(db, group_id, user.id)
    body = data.body.strip()
    if not body:
        raise HTTPException(422, "Pesan tidak boleh hanya berisi spasi.")
    row = Message(group_id=group_id, user_id=user.id, body=body)
    db.add(row); db.commit(); db.refresh(row)
    result = {"id": row.id, "user_id": user.id, "username": user.username, "body": row.body,
              "created_at": row.created_at.isoformat(), "edited": False}
    await hub.broadcast(group_id, {"event": "message.created", "message": result})
    return result

@app.websocket("/api/v1/groups/{group_id}/ws")
async def group_socket(websocket: WebSocket, group_id: str, ticket: str = Query(...)):
    db = SessionLocal()
    try:
        ticket_row = db.scalar(select(WebSocketTicket).where(
            WebSocketTicket.token_hash == hash_secret(ticket),
            WebSocketTicket.group_id == group_id,
            WebSocketTicket.consumed_at.is_(None)
        ).with_for_update())
        if not ticket_row:
            await websocket.close(code=4403); return
        expiry = ticket_row.expires_at if ticket_row.expires_at.tzinfo else ticket_row.expires_at.replace(tzinfo=timezone.utc)
        if expiry <= now_utc():
            ticket_row.consumed_at = now_utc(); db.commit()
            await websocket.close(code=4403); return
        ticket_row.consumed_at = now_utc()
        db.commit()
        user = db.get(User, ticket_row.user_id)
        if not user or not group_member(db, group_id, user.id):
            await websocket.close(code=4403); return
        await hub.connect(group_id, websocket)
        await websocket.send_json({"event": "connected", "username": user.username})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        hub.disconnect(group_id, websocket)
    except Exception:
        try: await websocket.close(code=4401)
        except Exception: pass
    finally:
        db.close()

@app.get("/api/v1/watchlist")
def list_watchlist(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(WatchlistItem).where(WatchlistItem.user_id == user.id).order_by(WatchlistItem.created_at.desc())).all()
    return [{"id": x.id, "symbol": x.symbol, "asset_name": x.asset_name, "note": x.note,
             "market_data_status": "unavailable", "source": None, "as_of": None} for x in rows]

@app.post("/api/v1/watchlist", status_code=201)
def add_watchlist(data: WatchlistIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = WatchlistItem(user_id=user.id, symbol=data.symbol.strip().upper(), asset_name=data.asset_name.strip(), note=data.note)
    db.add(row); db.commit(); db.refresh(row)
    return {"id": row.id, "symbol": row.symbol, "asset_name": row.asset_name, "note": row.note, "market_data_status": "unavailable"}

@app.delete("/api/v1/watchlist/{item_id}")
def delete_watchlist(item_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(WatchlistItem, item_id)
    if not row or row.user_id != user.id: raise HTTPException(404, "Watchlist item tidak ditemukan.")
    db.delete(row); db.commit(); return {"ok": True}

@app.get("/api/v1/investment/theses")
def list_theses(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(InvestmentThesis).where(InvestmentThesis.user_id == user.id).order_by(InvestmentThesis.created_at.desc())).all()
    return [{"id": r.id, "symbol": r.symbol, "horizon": r.horizon, "risk_profile": r.risk_profile,
             "thesis": r.thesis, "risks": r.risks, "invalidation": r.invalidation,
             "optimistic_case": r.optimistic_case, "base_case": r.base_case,
             "pessimistic_case": r.pessimistic_case, "created_at": r.created_at.isoformat(),
             "market_data_status": "unavailable"} for r in rows]

@app.post("/api/v1/investment/theses", status_code=201)
def create_thesis(data: ThesisIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = InvestmentThesis(user_id=user.id, **data.model_dump())
    row.symbol = row.symbol.upper()
    db.add(row); db.commit(); db.refresh(row)
    return {"id": row.id, "symbol": row.symbol, "created_at": row.created_at.isoformat(), "market_data_status": "unavailable"}

@app.post("/api/v1/support/tickets", status_code=201)
def create_support_ticket(data: SupportIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    code = f"NX-{now_utc().strftime('%y%m%d')}-{secrets.token_hex(2).upper()}"
    row = SupportTicket(user_id=user.id, ticket_code=code, category=data.category,
                        title=data.title.strip(), description=data.description.strip(), status="baru")
    db.add(row); db.commit(); db.refresh(row)
    return {"id": row.id, "ticket_code": row.ticket_code, "status": row.status, "created_at": row.created_at.isoformat()}

@app.get("/api/v1/support/tickets")
def list_support_tickets(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(SupportTicket).where(SupportTicket.user_id == user.id).order_by(SupportTicket.created_at.desc())).all()
    return [{"id": r.id, "ticket_code": r.ticket_code, "category": r.category, "title": r.title,
             "status": r.status, "created_at": r.created_at.isoformat()} for r in rows]

@app.get("/api/v1/export/transactions.csv")
def export_transactions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    import csv, io
    from fastapi.responses import StreamingResponse
    output = io.StringIO(); writer = csv.writer(output)
    writer.writerow(["tanggal", "jenis", "deskripsi", "nominal", "mata_uang", "akun_asal", "kategori", "catatan"])
    rows = db.scalars(select(Transaction).where(Transaction.user_id == user.id, Transaction.status == "confirmed").order_by(Transaction.occurred_at)).all()
    for r in rows:
        account = db.get(FinancialAccount, r.source_account_id) if r.source_account_id else None
        category = db.get(Category, r.category_id) if r.category_id else None
        writer.writerow([r.occurred_at.isoformat(), r.kind, r.description, str(r.amount), r.currency,
                         account.name if account else "", category.name if category else "", r.notes])
    output.seek(0)
    return StreamingResponse(iter(["\ufeff" + output.getvalue()]), media_type="text/csv; charset=utf-8",
                             headers={"Content-Disposition": "attachment; filename=nexora-transactions.csv"})

@app.get("/api/v1/export/data.json")
def export_all_user_data(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Portable JSON export of the authenticated user's own NEXORA records."""
    groups = db.scalars(select(CommunityGroup).join(GroupMember, GroupMember.group_id == CommunityGroup.id)
                        .where(GroupMember.user_id == user.id)).all()
    group_ids = [g.id for g in groups]
    receipts = db.scalars(select(Receipt).where(Receipt.user_id == user.id)).all()
    payload = {
        "schema_version": 1,
        "exported_at": now_utc().isoformat(),
        "timezone": str(APP_TIMEZONE),
        "user": {"username": user.username, "profile_code": user.profile_code,
                 "created_at": user.created_at.isoformat(), "theme": user.theme},
        "accounts": [serialize_account(x) for x in db.scalars(select(FinancialAccount).where(FinancialAccount.user_id == user.id)).all()],
        "categories": [serialize_category(x) for x in db.scalars(select(Category).where(Category.user_id == user.id)).all()],
        "transactions": [serialize_transaction(x) for x in db.scalars(select(Transaction).where(Transaction.user_id == user.id).order_by(Transaction.occurred_at)).all()],
        "budgets": [{"category_id": x.category_id, "amount": str(x.amount), "starts_on": x.starts_on.isoformat(),
                     "ends_on": x.ends_on.isoformat(), "threshold_percent": x.threshold_percent}
                    for x in db.scalars(select(Budget).where(Budget.user_id == user.id)).all()],
        "goals": [serialize_goal(x) for x in db.scalars(select(Goal).where(Goal.user_id == user.id)).all()],
        "recurring_rules": [serialize_recurring(x) for x in db.scalars(select(RecurringRule).where(RecurringRule.user_id == user.id)).all()],
        "receipts": [{"filename": x.original_name, "mime_type": x.mime_type, "sha256": x.sha256,
                      "status": x.status, "ocr_fields": x.ocr_fields or {}, "ocr_confidence": x.ocr_confidence,
                      "created_at": x.created_at.isoformat()} for x in receipts],
        "watchlist": [{"symbol": x.symbol, "asset_name": x.asset_name, "note": x.note}
                      for x in db.scalars(select(WatchlistItem).where(WatchlistItem.user_id == user.id)).all()],
        "investment_theses": [{"symbol": x.symbol, "horizon": x.horizon, "risk_profile": x.risk_profile,
                                "thesis": x.thesis, "risks": x.risks, "invalidation": x.invalidation,
                                "optimistic_case": x.optimistic_case, "base_case": x.base_case,
                                "pessimistic_case": x.pessimistic_case, "created_at": x.created_at.isoformat()}
                               for x in db.scalars(select(InvestmentThesis).where(InvestmentThesis.user_id == user.id)).all()],
        "support_tickets": [{"ticket_code": x.ticket_code, "category": x.category, "title": x.title,
                             "description": x.description, "status": x.status, "created_at": x.created_at.isoformat()}
                            for x in db.scalars(select(SupportTicket).where(SupportTicket.user_id == user.id)).all()],
        "groups": [{"id": g.id, "name": g.name, "description": g.description, "rules": g.rules,
                    "membership_role": group_member(db, g.id, user.id).role if group_member(db, g.id, user.id) else "member"}
                   for g in groups],
        "group_messages": [{"group_id": x.group_id, "username": db.get(User, x.user_id).username if db.get(User, x.user_id) else "Pengguna",
                            "body": x.body, "created_at": x.created_at.isoformat(), "edited_at": x.edited_at.isoformat() if x.edited_at else None,
                            "deleted": bool(x.deleted_at)}
                           for x in db.scalars(select(Message).where(Message.group_id.in_(group_ids))).all()] if group_ids else [],
    }
    return JSONResponse(content=payload, headers={"Content-Disposition": 'attachment; filename="nexora-data-export.json"'})


@app.post("/api/v1/auth/delete-account")
def delete_account(data: DeleteAccountIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Irreversibly delete the authenticated user's account and owned content."""
    try:
        pwd_hasher.verify(user.password_hash, data.current_password)
    except (VerifyMismatchError, VerificationError):
        raise HTTPException(403, "Password saat ini tidak cocok.")

    owned_groups = db.scalars(select(CommunityGroup).where(CommunityGroup.owner_id == user.id)).all()
    owned_group_ids = [g.id for g in owned_groups]
    authored_messages = db.scalars(select(Message).where(Message.user_id == user.id)).all()
    authored_message_ids = [m.id for m in authored_messages]
    affected_group_ids = set(owned_group_ids)
    affected_group_ids.update(m.group_id for m in authored_messages)

    # Remove group-scoped children first for PostgreSQL FK compatibility.
    reports = db.scalars(select(ContentReport).where(ContentReport.reporter_id == user.id)).all()
    for report in reports:
        db.delete(report)
    if owned_group_ids:
        db.query(ContentReport).filter(ContentReport.group_id.in_(owned_group_ids)).delete(synchronize_session=False)
    if authored_message_ids:
        db.query(ContentReport).filter(ContentReport.message_id.in_(authored_message_ids)).delete(synchronize_session=False)
        db.query(MessageReaction).filter(MessageReaction.message_id.in_(authored_message_ids)).delete(synchronize_session=False)
    db.query(MessageReaction).filter(MessageReaction.user_id == user.id).delete(synchronize_session=False)
    if owned_group_ids:
        db.query(MessageReaction).filter(MessageReaction.message_id.in_(select(Message.id).where(Message.group_id.in_(owned_group_ids)))).delete(synchronize_session=False)
        db.query(Message).filter(Message.group_id.in_(owned_group_ids)).delete(synchronize_session=False)
        db.query(JoinRequest).filter(JoinRequest.group_id.in_(owned_group_ids)).delete(synchronize_session=False)
        db.query(GroupMember).filter(GroupMember.group_id.in_(owned_group_ids)).delete(synchronize_session=False)
        db.query(WebSocketTicket).filter(WebSocketTicket.group_id.in_(owned_group_ids)).delete(synchronize_session=False)
    if authored_message_ids:
        db.query(Message).filter(Message.id.in_(authored_message_ids)).delete(synchronize_session=False)
    db.query(GroupMember).filter(GroupMember.user_id == user.id).delete(synchronize_session=False)
    db.query(JoinRequest).filter(JoinRequest.user_id == user.id).delete(synchronize_session=False)
    if owned_group_ids:
        db.query(CommunityGroup).filter(CommunityGroup.id.in_(owned_group_ids)).delete(synchronize_session=False)

    db.query(UserBlock).filter((UserBlock.blocker_id == user.id) | (UserBlock.blocked_id == user.id)).delete(synchronize_session=False)
    db.query(WebSocketTicket).filter(WebSocketTicket.user_id == user.id).delete(synchronize_session=False)
    db.query(UserSession).filter(UserSession.user_id == user.id).delete(synchronize_session=False)
    db.query(RecoveryCode).filter(RecoveryCode.user_id == user.id).delete(synchronize_session=False)

    # Remove private documents from local encrypted-volume storage before deleting metadata.
    user_receipts = db.scalars(select(Receipt).where(Receipt.user_id == user.id)).all()
    for receipt in user_receipts:
        try:
            Path(receipt.stored_path).unlink(missing_ok=True)
        except OSError:
            pass
        db.delete(receipt)
    db.query(RecurringExecution).filter(RecurringExecution.rule_id.in_(
        select(RecurringRule.id).where(RecurringRule.user_id == user.id))).delete(synchronize_session=False)
    db.query(RecurringRule).filter(RecurringRule.user_id == user.id).delete(synchronize_session=False)
    for model in (Transaction, Budget, Goal, WatchlistItem, InvestmentThesis, SupportTicket, Category, FinancialAccount):
        db.query(model).filter(model.user_id == user.id).delete(synchronize_session=False)
    db.delete(user)
    db.commit()
    return {"ok": True, "message": "Akun dan data NEXORA milikmu telah dihapus."}


@app.get("/")
def app_home():
    return FileResponse(FRONTEND_DIR / "index.html")

@app.get("/manifest.webmanifest")
def manifest():
    return FileResponse(FRONTEND_DIR / "manifest.webmanifest", media_type="application/manifest+json")

@app.get("/sw.js")
def service_worker():
    return FileResponse(FRONTEND_DIR / "sw.js", media_type="application/javascript")

if (FRONTEND_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")


# ---------------------------------------------------------------------------
# NEXORA completion pack: goals, recurring transactions, OCR, group management,
# message moderation, account controls, and session management.
# ---------------------------------------------------------------------------

from calendar import monthrange


def serialize_goal(row: Goal) -> dict[str, Any]:
    target = Decimal(row.target_amount)
    current = Decimal(row.current_amount)
    pct = (current / target * 100) if target else Decimal("0")
    return {"id": row.id, "name": row.name, "target_amount": str(target),
            "current_amount": str(current), "remaining": str(max(target-current, Decimal("0"))),
            "progress_percent": min(round(float(pct), 2), 100),
            "target_date": row.target_date.isoformat() if row.target_date else None,
            "note": row.note, "status": row.status,
            "created_at": row.created_at.isoformat()}


def serialize_recurring(row: RecurringRule) -> dict[str, Any]:
    return {"id": row.id, "kind": row.kind, "amount": str(row.amount), "currency": row.currency,
            "source_account_id": row.source_account_id, "target_account_id": row.target_account_id,
            "category_id": row.category_id, "description": row.description, "notes": row.notes,
            "frequency": row.frequency, "next_run_on": row.next_run_on.isoformat(),
            "ends_on": row.ends_on.isoformat() if row.ends_on else None, "active": row.active}


def next_recurring_date(value: date, frequency: str) -> date:
    if frequency == "daily": return value + timedelta(days=1)
    if frequency == "weekly": return value + timedelta(days=7)
    if frequency == "monthly":
        month = value.month + 1
        year = value.year + (1 if month > 12 else 0)
        month = 1 if month > 12 else month
        return date(year, month, min(value.day, monthrange(year, month)[1]))
    if frequency == "yearly":
        try: return value.replace(year=value.year + 1)
        except ValueError: return value.replace(year=value.year + 1, day=28)
    raise ValueError("Frekuensi tidak didukung.")


def recurring_transaction_input(rule: RecurringRule, scheduled_on: date) -> TransactionIn:
    scheduled_at = datetime.combine(scheduled_on, datetime.min.time()).replace(hour=12, tzinfo=APP_TIMEZONE)
    return TransactionIn(kind=rule.kind, amount=rule.amount, currency=rule.currency,
                         source_account_id=rule.source_account_id, target_account_id=rule.target_account_id,
                         category_id=rule.category_id, description=rule.description, notes=rule.notes,
                         occurred_at=scheduled_at)


def execute_recurring_rule(db: Session, rule: RecurringRule, scheduled_on: date) -> Optional[Transaction]:
    # Unique(rule_id, scheduled_on) is the final idempotency guard if two workers overlap.
    if db.scalar(select(RecurringExecution).where(
        RecurringExecution.rule_id == rule.id, RecurringExecution.scheduled_on == scheduled_on
    )):
        return None
    user = db.get(User, rule.user_id)
    if not user:
        return None
    try:
        # A savepoint prevents one duplicate schedule from rolling back other rules
        # already processed in this worker pass.
        with db.begin_nested():
            data = recurring_transaction_input(rule, scheduled_on)
            tx = make_transaction(data, user, db)
            db.flush()
            db.add(RecurringExecution(rule_id=rule.id, scheduled_on=scheduled_on, transaction_id=tx.id))
            db.flush()
        return tx
    except IntegrityError:
        return None


def process_due_recurring(db: Session, today_local: Optional[date] = None) -> int:
    today_local = today_local or now_utc().astimezone(APP_TIMEZONE).date()
    rules = db.scalars(select(RecurringRule).where(RecurringRule.active.is_(True)).with_for_update()).all()
    created = 0
    for rule in rules:
        while rule.next_run_on <= today_local and (rule.ends_on is None or rule.next_run_on <= rule.ends_on):
            scheduled = rule.next_run_on
            try:
                tx = execute_recurring_rule(db, rule, scheduled)
                if tx: created += 1
            except HTTPException:
                # Pause invalid rules rather than retrying a broken template forever.
                rule.active = False
                break
            rule.next_run_on = next_recurring_date(rule.next_run_on, rule.frequency)
        if rule.ends_on and rule.next_run_on > rule.ends_on:
            rule.active = False
    db.commit()
    return created


@app.get("/api/v1/goals")
def list_goals(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Goal).where(Goal.user_id == user.id).order_by(Goal.created_at.desc())).all()
    return [serialize_goal(row) for row in rows]


@app.post("/api/v1/goals", status_code=201)
def create_goal(data: GoalIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if data.target_date and data.target_date < now_utc().astimezone(APP_TIMEZONE).date():
        raise HTTPException(422, "Tanggal target tidak boleh berada di masa lalu.")
    if data.current_amount > data.target_amount:
        raise HTTPException(422, "Jumlah terkumpul tidak boleh melebihi target.")
    row = Goal(user_id=user.id, **data.model_dump())
    if row.current_amount >= row.target_amount: row.status = "completed"
    db.add(row); db.commit(); db.refresh(row)
    return serialize_goal(row)


@app.patch("/api/v1/goals/{goal_id}")
def update_goal(goal_id: str, data: GoalIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(Goal, goal_id)
    if not row or row.user_id != user.id: raise HTTPException(404, "Tujuan tidak ditemukan.")
    if data.current_amount > data.target_amount: raise HTTPException(422, "Jumlah terkumpul tidak boleh melebihi target.")
    for key, value in data.model_dump().items(): setattr(row, key, value)
    row.status = "completed" if row.current_amount >= row.target_amount else "active"
    db.commit(); db.refresh(row)
    return serialize_goal(row)


@app.delete("/api/v1/goals/{goal_id}")
def delete_goal(goal_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(Goal, goal_id)
    if not row or row.user_id != user.id: raise HTTPException(404, "Tujuan tidak ditemukan.")
    db.delete(row); db.commit(); return {"ok": True}


@app.get("/api/v1/recurring")
def list_recurring(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(RecurringRule).where(RecurringRule.user_id == user.id).order_by(RecurringRule.next_run_on)).all()
    return [serialize_recurring(row) for row in rows]


@app.post("/api/v1/recurring", status_code=201)
def create_recurring(data: RecurringIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if data.ends_on and data.ends_on < data.next_run_on: raise HTTPException(422, "Tanggal akhir harus sama atau setelah jadwal pertama.")
    tx_input = TransactionIn(kind=data.kind, amount=data.amount, currency=data.currency,
        source_account_id=data.source_account_id, target_account_id=data.target_account_id,
        category_id=data.category_id, description=data.description, notes=data.notes,
        occurred_at=datetime.combine(data.next_run_on, datetime.min.time()).replace(tzinfo=APP_TIMEZONE))
    validate_transaction_links(tx_input, user, db)
    row = RecurringRule(user_id=user.id, **data.model_dump())
    row.currency = row.currency.upper(); row.description = row.description.strip()
    db.add(row); db.commit(); db.refresh(row)
    return serialize_recurring(row)


@app.patch("/api/v1/recurring/{rule_id}")
def update_recurring(rule_id: str, data: dict[str, Any], user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(RecurringRule, rule_id)
    if not row or row.user_id != user.id: raise HTTPException(404, "Aturan berulang tidak ditemukan.")
    if set(data) - {"active", "next_run_on", "ends_on"}: raise HTTPException(422, "Hanya status aktif dan tanggal jadwal yang dapat diubah di sini.")
    if "active" in data:
        if not isinstance(data["active"], bool): raise HTTPException(422, "Status aktif harus berupa boolean.")
        row.active = data["active"]
    for field in ("next_run_on", "ends_on"):
        if field in data:
            try: setattr(row, field, date.fromisoformat(data[field]) if data[field] else None)
            except (TypeError, ValueError): raise HTTPException(422, f"{field} harus berupa tanggal ISO.")
    if row.ends_on and row.ends_on < row.next_run_on: raise HTTPException(422, "Tanggal akhir harus sama atau setelah jadwal berikutnya.")
    db.commit(); db.refresh(row); return serialize_recurring(row)


@app.delete("/api/v1/recurring/{rule_id}")
def delete_recurring(rule_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(RecurringRule, rule_id)
    if not row or row.user_id != user.id: raise HTTPException(404, "Aturan berulang tidak ditemukan.")
    db.delete(row); db.commit(); return {"ok": True}


@app.post("/api/v1/recurring/{rule_id}/run-now", status_code=201)
def run_recurring_now(rule_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(RecurringRule, rule_id)
    if not row or row.user_id != user.id: raise HTTPException(404, "Aturan berulang tidak ditemukan.")
    if not row.active: raise HTTPException(409, "Aturan berulang sedang dijeda.")
    today_local = now_utc().astimezone(APP_TIMEZONE).date()
    scheduled = min(row.next_run_on, today_local)
    tx = execute_recurring_rule(db, row, scheduled)
    if not tx: raise HTTPException(409, "Jadwal ini sudah pernah dibuat menjadi transaksi.")
    db.commit(); db.refresh(tx)
    if scheduled >= row.next_run_on:
        row.next_run_on = next_recurring_date(row.next_run_on, row.frequency)
        db.commit()
    return {"transaction": serialize_transaction(tx), "next_run_on": row.next_run_on.isoformat()}


@app.get("/api/v1/receipts/{receipt_id}/download")
def download_receipt(receipt_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(Receipt, receipt_id)
    if not row or row.user_id != user.id: raise HTTPException(404, "Dokumen tidak ditemukan.")
    path = Path(row.stored_path).resolve()
    if not path.exists() or UPLOAD_DIR.resolve() not in path.parents: raise HTTPException(404, "Berkas tidak ditemukan.")
    return FileResponse(path, media_type=row.mime_type, filename=row.original_name)


def extract_ocr_fields(text_value: str) -> dict[str, Any]:
    text_lines = [line.strip() for line in text_value.splitlines() if line.strip()]
    date_candidates: list[str] = []
    for line in text_lines:
        for match in re.findall(r"(?<!\d)(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})(?!\d)", line):
            normalized = match.replace("/", "-")
            try:
                parts = normalized.split("-")
                if len(parts[0]) == 4: parsed = date(int(parts[0]), int(parts[1]), int(parts[2]))
                else:
                    year = int(parts[2]); year = year + 2000 if year < 100 else year
                    parsed = date(year, int(parts[1]), int(parts[0]))
                date_candidates.append(parsed.isoformat())
            except ValueError: pass
    date_candidates = list(dict.fromkeys(date_candidates))

    candidates: list[dict[str, str]] = []
    amount_pattern = re.compile(r"(?<!\d)(?:Rp\s*|IDR\s*)?((?:\d{1,3}(?:[., ]\d{3})+)|\d{4,})(?:[.,]\d{2})?(?!\d)", re.I)
    for line in text_lines:
        if re.search(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})\b", line):
            line = re.sub(r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})\b", " ", line)
        for raw in amount_pattern.findall(line):
            digits = re.sub(r"[^0-9]", "", raw)
            if len(digits) < 4 or len(digits) > 15: continue
            try: amount = int(digits)
            except ValueError: continue
            if amount == 0: continue
            candidates.append({"raw": raw.strip(), "amount": str(amount), "line": line[:180]})
    # Prefer a unique amount on a line containing total/amount keywords; do not choose
    # between several plausible totals, subtotals, taxes, and balances automatically.
    total_candidates = [x for x in candidates if re.search(r"total|jumlah|amount|grand|tagihan|debit|kredit", x["line"], re.I)]
    pool = total_candidates or candidates
    unique: dict[str, dict[str, str]] = {x["amount"]: x for x in pool}
    amount_suggestion = next(iter(unique.values())) if len(unique) == 1 else None
    kind = None
    joined = " ".join(text_lines).lower()
    if re.search(r"kredit|credit|setoran|penerimaan|uang masuk", joined): kind = "income"
    if re.search(r"debit|debet|pembayaran|pembelian|uang keluar", joined):
        kind = "expense" if kind is None or not re.search(r"kredit|credit|setoran|penerimaan|uang masuk", joined) else None
    descriptions = [line for line in text_lines if not amount_pattern.search(line) and not re.search(r"rekening|statement|mutasi|tanggal|date|saldo|balance|total|bank|transfer|receipt", line, re.I)]
    return {"date": date_candidates[0] if len(date_candidates) == 1 else None,
            "date_candidates": date_candidates,
            "amount": amount_suggestion["amount"] if amount_suggestion else None,
            "amount_candidates": list(unique.values())[:8],
            "kind": kind,
            "description": descriptions[0][:140] if descriptions else None}


@app.post("/api/v1/receipts/{receipt_id}/extract")
def extract_receipt(receipt_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(Receipt, receipt_id)
    if not row or row.user_id != user.id: raise HTTPException(404, "Dokumen tidak ditemukan.")
    if row.confirmed_transaction_id: raise HTTPException(409, "Dokumen sudah dikonfirmasi menjadi transaksi.")
    try:
        import pytesseract
        from PIL import Image
        if row.mime_type == "application/pdf":
            from pdf2image import convert_from_path
            pages = convert_from_path(row.stored_path, dpi=220, first_page=1, last_page=2)
        else:
            pages = [Image.open(row.stored_path).convert("RGB")]
        texts: list[str] = []
        confidences: list[float] = []
        for image in pages:
            image.thumbnail((2600, 2600))
            texts.append(pytesseract.image_to_string(image, lang=os.getenv("OCR_LANG", "ind+eng"), config="--psm 6"))
            data = pytesseract.image_to_data(image, lang=os.getenv("OCR_LANG", "ind+eng"), config="--psm 6", output_type=pytesseract.Output.DICT)
            for conf in data.get("conf", []):
                try:
                    value = float(conf)
                    if value >= 0: confidences.append(value)
                except (TypeError, ValueError): pass
        extracted_text = "\n".join(texts).strip()
        if not extracted_text: raise HTTPException(422, "Teks tidak terbaca. Coba foto lebih jelas atau isi secara manual.")
        fields = extract_ocr_fields(extracted_text)
        confidence = round(sum(confidences) / len(confidences), 2) if confidences else None
        row.ocr_text = extracted_text[:30000]
        row.ocr_fields = fields
        row.ocr_confidence = confidence
        row.status = "ocr_review"
        db.commit()
        return {"id": row.id, "filename": row.original_name, "status": row.status,
                "ocr_text": row.ocr_text, "fields": fields, "confidence": confidence,
                "confidence_label": "Perkiraan kualitas pembacaan, bukan jaminan kebenaran transaksi.",
                "message": "OCR menghasilkan saran draft. Periksa semua nilai dan konfirmasi sendiri; belum ada transaksi yang disimpan."}
    except HTTPException:
        raise
    except ImportError:
        raise HTTPException(503, "Mesin OCR tidak terpasang pada server ini. Gunakan input manual atau deploy image Docker resmi NEXORA.")
    except Exception as exc:
        raise HTTPException(422, f"OCR gagal membaca dokumen ({type(exc).__name__}). Silakan isi transaksi secara manual.")


@app.get("/api/v1/sessions")
def list_sessions(user: User = Depends(get_current_user), authorization: str = Header(default=""), db: Session = Depends(get_db)):
    payload = decode_access_token(authorization[7:])
    rows = db.scalars(select(UserSession).where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None)).order_by(UserSession.created_at.desc())).all()
    return [{"id": row.id, "current": row.id == payload.get("sid"), "created_at": row.created_at.isoformat(),
             "expires_at": row.expires_at.isoformat()} for row in rows]


@app.post("/api/v1/auth/logout-all")
def logout_all_sessions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(UserSession).where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))).all()
    for row in rows: row.revoked_at = now_utc()
    db.commit()
    return {"ok": True, "revoked_sessions": len(rows)}


@app.get("/api/v1/profiles/{profile_code}")
def lookup_profile(profile_code: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.scalar(select(User).where(User.profile_code == profile_code.strip().upper()))
    if not row: raise HTTPException(404, "Kode profil tidak ditemukan.")
    return {"username": row.username, "profile_code": row.profile_code, "same_user": row.id == user.id}


@app.patch("/api/v1/accounts/{account_id}")
def update_account(account_id: str, data: dict[str, Any], user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(FinancialAccount, account_id)
    if not row or row.user_id != user.id: raise HTTPException(404, "Akun tidak ditemukan.")
    if set(data) - {"name", "archived"}: raise HTTPException(422, "Field akun tidak dikenali.")
    if "name" in data:
        if not isinstance(data["name"], str) or not 2 <= len(data["name"].strip()) <= 60: raise HTTPException(422, "Nama akun harus 2–60 karakter.")
        row.name = data["name"].strip()
    if "archived" in data:
        if not isinstance(data["archived"], bool): raise HTTPException(422, "archived harus berupa boolean.")
        row.archived = data["archived"]
        if row.archived:
            dependent_rules = db.scalars(select(RecurringRule).where(
                RecurringRule.user_id == user.id, RecurringRule.active.is_(True),
                (RecurringRule.source_account_id == row.id) | (RecurringRule.target_account_id == row.id)
            )).all()
            for rule in dependent_rules:
                rule.active = False
    db.commit(); db.refresh(row); return serialize_account(row)


@app.patch("/api/v1/categories/{category_id}")
def update_category(category_id: str, data: CategoryIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(Category, category_id)
    if not row or row.user_id != user.id: raise HTTPException(404, "Kategori tidak ditemukan.")
    if row.kind != data.kind:
        # A category's semantic type determines report aggregation. Changing it
        # after use would silently reclassify historical transactions/budgets.
        used_tx = db.scalar(select(Transaction.id).where(
            Transaction.user_id == user.id, Transaction.category_id == category_id
        ).limit(1))
        used_budget = db.scalar(select(Budget.id).where(
            Budget.user_id == user.id, Budget.category_id == category_id
        ).limit(1))
        used_rule = db.scalar(select(RecurringRule.id).where(
            RecurringRule.user_id == user.id, RecurringRule.category_id == category_id
        ).limit(1))
        if used_tx or used_budget or used_rule:
            raise HTTPException(409, "Jenis kategori tidak dapat diubah karena sudah dipakai transaksi, anggaran, atau transaksi berulang. Buat kategori baru untuk jenis yang berbeda.")
    row.name = data.name.strip(); row.kind = data.kind; row.color = data.color; row.icon = data.icon
    db.commit(); db.refresh(row); return serialize_category(row)


@app.delete("/api/v1/categories/{category_id}")
def delete_category(category_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(Category, category_id)
    if not row or row.user_id != user.id: raise HTTPException(404, "Kategori tidak ditemukan.")
    used_tx = db.scalar(select(Transaction.id).where(Transaction.category_id == category_id).limit(1))
    used_budget = db.scalar(select(Budget.id).where(Budget.category_id == category_id).limit(1))
    used_rule = db.scalar(select(RecurringRule.id).where(RecurringRule.category_id == category_id).limit(1))
    if used_tx or used_budget or used_rule: raise HTTPException(409, "Kategori masih dipakai transaksi, anggaran, atau transaksi berulang.")
    db.delete(row); db.commit(); return {"ok": True}


@app.patch("/api/v1/budgets/{budget_id}")
def update_budget(budget_id: str, data: BudgetIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(Budget, budget_id)
    if not row or row.user_id != user.id: raise HTTPException(404, "Anggaran tidak ditemukan.")
    cat = db.get(Category, data.category_id)
    if not cat or cat.user_id != user.id or cat.kind != "expense": raise HTTPException(422, "Pilih kategori pengeluaran milikmu.")
    if data.ends_on < data.starts_on: raise HTTPException(422, "Tanggal akhir harus setelah tanggal awal.")
    for key, value in data.model_dump().items(): setattr(row, key, value)
    db.commit(); db.refresh(row); return {"id": row.id, "ok": True}


@app.delete("/api/v1/budgets/{budget_id}")
def delete_budget(budget_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(Budget, budget_id)
    if not row or row.user_id != user.id: raise HTTPException(404, "Anggaran tidak ditemukan.")
    db.delete(row); db.commit(); return {"ok": True}


@app.get("/api/v1/groups/{group_id}/members")
def list_group_members(group_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_group_member(db, group_id, user.id)
    rows = db.scalars(select(GroupMember).where(GroupMember.group_id == group_id).order_by(GroupMember.joined_at)).all()
    return [{"user_id": row.user_id, "username": db.get(User, row.user_id).username if db.get(User, row.user_id) else "Pengguna",
             "role": row.role, "joined_at": row.joined_at.isoformat()} for row in rows]


@app.patch("/api/v1/groups/{group_id}")
def update_group(group_id: str, data: GroupPatchIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    group = db.get(CommunityGroup, group_id)
    if not group or group.owner_id != user.id: raise HTTPException(404, "Grup tidak ditemukan atau kamu bukan owner.")
    group.name = data.name.strip(); group.description = data.description.strip(); group.rules = data.rules.strip()
    db.commit(); db.refresh(group); return serialize_group(group, "owner")


@app.post("/api/v1/groups/{group_id}/invite/rotate")
def rotate_group_invite(group_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    member = require_group_admin(db, group_id, user.id)
    if member.role != "owner": raise HTTPException(403, "Hanya owner yang dapat mengganti kode undangan.")
    group = db.get(CommunityGroup, group_id)
    code = f"NXG-{secrets.token_urlsafe(12).upper()}"
    group.invite_hash = hash_secret(code)
    db.commit()
    return {"invite_code": code, "rotated": True, "message": "Kode lama langsung tidak berlaku."}


@app.patch("/api/v1/groups/{group_id}/members/{member_user_id}")
def update_group_member_role(group_id: str, member_user_id: str, data: RoleIn,
    user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    acting = require_group_admin(db, group_id, user.id)
    if acting.role != "owner": raise HTTPException(403, "Hanya owner yang dapat mengubah role admin.")
    target = group_member(db, group_id, member_user_id)
    if not target or target.role == "owner": raise HTTPException(404, "Anggota tidak ditemukan atau role owner tidak dapat diubah.")
    target.role = data.role; db.commit()
    return {"user_id": member_user_id, "role": target.role}


@app.delete("/api/v1/groups/{group_id}/members/{member_user_id}")
def remove_group_member(group_id: str, member_user_id: str,
    user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    acting = require_group_admin(db, group_id, user.id)
    target = group_member(db, group_id, member_user_id)
    if not target or target.role == "owner": raise HTTPException(404, "Anggota tidak ditemukan atau owner tidak dapat dikeluarkan.")
    if acting.role != "owner" and (target.role == "admin" or member_user_id == user.id):
        raise HTTPException(403, "Admin hanya dapat mengeluarkan member biasa.")
    db.delete(target); db.commit()
    return {"ok": True}


@app.patch("/api/v1/groups/{group_id}/messages/{message_id}")
async def edit_group_message(group_id: str, message_id: str, data: MessagePatchIn,
    user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_group_member(db, group_id, user.id)
    row = db.get(Message, message_id)
    if not row or row.group_id != group_id or row.user_id != user.id or row.deleted_at:
        raise HTTPException(404, "Pesan tidak ditemukan atau bukan milikmu.")
    created = row.created_at if row.created_at.tzinfo else row.created_at.replace(tzinfo=timezone.utc)
    if (now_utc() - created).total_seconds() > 15 * 60: raise HTTPException(409, "Pesan hanya dapat diedit selama 15 menit.")
    row.body = data.body.strip(); row.edited_at = now_utc(); db.commit()
    payload = {"id": row.id, "user_id": row.user_id, "username": user.username, "body": row.body,
               "created_at": row.created_at.isoformat(), "edited": True, "deleted": False}
    await hub.broadcast(group_id, {"event": "message.updated", "message": payload})
    return payload


@app.delete("/api/v1/groups/{group_id}/messages/{message_id}")
async def delete_group_message(group_id: str, message_id: str,
    user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    member = require_group_member(db, group_id, user.id)
    row = db.get(Message, message_id)
    if not row or row.group_id != group_id or row.deleted_at: raise HTTPException(404, "Pesan tidak ditemukan.")
    if row.user_id != user.id and member.role not in ("owner", "admin"):
        raise HTTPException(403, "Kamu hanya dapat menghapus pesan sendiri.")
    row.deleted_at = now_utc(); db.commit()
    payload = {"id": row.id, "user_id": row.user_id, "body": "Pesan telah dihapus", "deleted": True, "edited": False}
    await hub.broadcast(group_id, {"event": "message.deleted", "message_id": row.id, "message": payload})
    return {"ok": True}


@app.post("/api/v1/groups/{group_id}/messages/{message_id}/reactions", status_code=201)
def add_message_reaction(group_id: str, message_id: str, data: ReactionIn,
    user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_group_member(db, group_id, user.id)
    message = db.get(Message, message_id)
    if not message or message.group_id != group_id or message.deleted_at: raise HTTPException(404, "Pesan tidak ditemukan.")
    existing = db.scalar(select(MessageReaction).where(MessageReaction.message_id == message_id,
        MessageReaction.user_id == user.id, MessageReaction.emoji == data.emoji))
    if not existing: db.add(MessageReaction(message_id=message_id, user_id=user.id, emoji=data.emoji)); db.commit()
    counts = db.execute(select(MessageReaction.emoji, func.count(MessageReaction.id)).where(
        MessageReaction.message_id == message_id).group_by(MessageReaction.emoji)).all()
    return {"message_id": message_id, "reactions": [{"emoji": emoji, "count": count} for emoji, count in counts]}


@app.post("/api/v1/groups/{group_id}/messages/{message_id}/report", status_code=201)
def report_group_message(group_id: str, message_id: str, data: ContentReportIn,
    user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_group_member(db, group_id, user.id)
    message = db.get(Message, message_id)
    if not message or message.group_id != group_id: raise HTTPException(404, "Pesan tidak ditemukan.")
    exists = db.scalar(select(ContentReport.id).where(ContentReport.reporter_id == user.id,
        ContentReport.message_id == message_id, ContentReport.status == "open"))
    if exists: raise HTTPException(409, "Pesan ini sudah kamu laporkan.")
    report = ContentReport(reporter_id=user.id, group_id=group_id, message_id=message_id,
                           reason=data.reason, details=data.details.strip())
    db.add(report); db.commit(); db.refresh(report)
    return {"id": report.id, "status": report.status, "message": "Laporan diterima untuk ditinjau oleh moderator grup."}


@app.get("/api/v1/groups/{group_id}/reports")
def list_group_reports(group_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_group_admin(db, group_id, user.id)
    rows = db.scalars(select(ContentReport).where(ContentReport.group_id == group_id).order_by(ContentReport.created_at.desc())).all()
    return [{"id": row.id, "reporter": db.get(User, row.reporter_id).username if db.get(User, row.reporter_id) else "Pengguna",
             "message_id": row.message_id, "reason": row.reason, "details": row.details,
             "status": row.status, "created_at": row.created_at.isoformat()} for row in rows]


@app.patch("/api/v1/groups/{group_id}/reports/{report_id}")
def resolve_group_report(group_id: str, report_id: str, data: ContentReportPatchIn,
    user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_group_admin(db, group_id, user.id)
    report = db.get(ContentReport, report_id)
    if not report or report.group_id != group_id:
        raise HTTPException(404, "Laporan tidak ditemukan.")
    report.status = data.status
    db.commit()
    return {"id": report.id, "status": report.status, "moderator_note": data.moderator_note,
            "message": "Status laporan diperbarui."}


@app.post("/api/v1/users/{blocked_user_id}/block", status_code=201)
def block_user(blocked_user_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    target = db.get(User, blocked_user_id)
    if not target or target.id == user.id: raise HTTPException(404, "Pengguna tidak ditemukan.")
    existing = db.scalar(select(UserBlock).where(UserBlock.blocker_id == user.id, UserBlock.blocked_id == target.id))
    if not existing: db.add(UserBlock(blocker_id=user.id, blocked_id=target.id)); db.commit()
    return {"ok": True}


@app.get("/api/v1/users/blocks")
def list_blocked_users(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(UserBlock).where(UserBlock.blocker_id == user.id)).all()
    return [{"user_id": row.blocked_id, "username": db.get(User, row.blocked_id).username if db.get(User, row.blocked_id) else "Pengguna"} for row in rows]


@app.delete("/api/v1/users/{blocked_user_id}/block")
def unblock_user(blocked_user_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.scalar(select(UserBlock).where(UserBlock.blocker_id == user.id, UserBlock.blocked_id == blocked_user_id))
    if not row: raise HTTPException(404, "Blokir tidak ditemukan.")
    db.delete(row); db.commit(); return {"ok": True}
