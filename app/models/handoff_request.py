from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class HandoffRequest(Base):
    """一条转人工请求"""

    __tablename__ = "handoff_requests"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    # 转人工单号，对外展示
    handoff_no: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
    )
    # 会话键与业务用户
    sender_id: Mapped[str] = mapped_column(
        String(255),
        index=True,
    )
    user_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    session_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    # 转人工原因
    reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    # pending / taken / closed
    status: Mapped[str] = mapped_column(
        String(32),
        default="pending",
        index=True,
    )
    agent_name: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
    )
    taken_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )