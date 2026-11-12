from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DialogueStateRecord(Base):
    """数据库中的一条对话状态记录"""

    __tablename__ = "dialogue_states"

    # 用户唯一标识，同时作为主键
    sender_id: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
    )
    # 完整的对话状态 JSON，长对话需要 LONGTEXT
    state_json: Mapped[str] = mapped_column(
        LONGTEXT,
        nullable=False,
    )