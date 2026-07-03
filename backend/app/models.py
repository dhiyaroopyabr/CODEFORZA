"""
models.py — SQLAlchemy ORM models.

Tables:
  - users         : registered accounts (user | admin roles)
  - problems      : competitive programming problems
  - test_cases    : input/output pairs for each problem
  - submissions   : code submissions with verdicts
"""

import uuid
import enum

from sqlalchemy import (
    Column, String, Boolean, DateTime, Text,
    Float, Integer, ForeignKey, Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


# ── Enums ────────────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    user = "user"
    admin = "admin"


# ── Models ───────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(Text, nullable=False)
    role = Column(SAEnum(UserRole, name="userrole"), default=UserRole.user, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    submissions = relationship("Submission", back_populates="user", lazy="dynamic")


class Problem(Base):
    __tablename__ = "problems"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    title = Column(String(200), nullable=False)
    statement = Column(Text, nullable=False)
    input_format = Column(Text)
    output_format = Column(Text)
    constraints = Column(Text)
    difficulty = Column(Integer, default=800, nullable=False)   # 800–3500 (CF scale)
    time_limit = Column(Float, default=2.0, nullable=False)     # seconds
    memory_limit = Column(Integer, default=256, nullable=False) # MB
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    test_cases = relationship(
        "TestCase", back_populates="problem",
        cascade="all, delete-orphan", lazy="select",
    )
    submissions = relationship("Submission", back_populates="problem", lazy="dynamic")


class TestCase(Base):
    __tablename__ = "test_cases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    problem_id = Column(
        UUID(as_uuid=True),
        ForeignKey("problems.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    input_data = Column(Text, nullable=False)
    expected_output = Column(Text, nullable=False)
    is_sample = Column(Boolean, default=False, nullable=False)  # visible to users

    problem = relationship("Problem", back_populates="test_cases")


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    problem_id = Column(UUID(as_uuid=True), ForeignKey("problems.id", ondelete="SET NULL"), nullable=True)
    language = Column(String(20), nullable=False)  # python | cpp | c | java
    code = Column(Text, nullable=False)
    status = Column(String(50), default="Pending", nullable=False)
    # AC | WA | TLE | MLE | RE | CE | Pending | Running
    stdout = Column(Text)
    stderr = Column(Text)
    execution_time = Column(Float)  # seconds, wall-clock
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="submissions")
    problem = relationship("Problem", back_populates="submissions")
