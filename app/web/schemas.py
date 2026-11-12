from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ChatObject(BaseModel):
    """消息中携带的业务对象，例如订单、酒店。"""

    type: str
    id: str
    title: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class ChatRequest(BaseModel):
    """POST /api/chat 的请求体。"""

    sender_id: str
    # 业务用户标识，缺省时由服务层回退到配置中的演示用户
    user_id: int | None = None
    message_id: str | None = None
    text: str | None = None
    object: ChatObject | None = None


class ChatBotMessage(BaseModel):
    """机器人本轮返回的一条消息。"""

    text: str | None = None
    object: ChatObject | None = None


class ChatResponse(BaseModel):
    """POST /api/chat 的响应体。"""

    sender_id: str
    message_id: str
    messages: list[ChatBotMessage]
    # 是否处于人工模式，前端据此切换为轮询
    human_mode: bool = False


class HistoryMessage(BaseModel):
    """历史记录中的一条消息。"""

    role: str
    text: str | None = None
    object: ChatObject | None = None


class HistoryResponse(BaseModel):
    """GET /api/chat/history 的响应体。"""

    sender_id: str
    messages: list[HistoryMessage]
    human_mode: bool = False


class SessionRequest(BaseModel):
    """POST /api/chat/sessions 的请求体。"""

    sender_id: str
    user_id: int | None = None


class SessionResponse(BaseModel):
    """POST /api/chat/sessions 的响应体。"""

    sender_id: str
    session_id: str
    started_at: float


class TaskStateView(BaseModel):
    """当前任务的可视化信息。"""

    task_id: str
    flow_id: str
    step_id: str | None = None
    slots: dict[str, Any] = Field(default_factory=dict)


class FocusedObjectView(BaseModel):
    """当前聚焦对象。"""

    type: str
    id: str
    title: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class ChatStateResponse(BaseModel):
    """GET /api/chat/state 的响应体。"""

    sender_id: str
    session_id: str | None = None
    started_at: float | None = None
    active_task: TaskStateView | None = None
    paused_tasks: list[TaskStateView] = Field(default_factory=list)
    focused_object: FocusedObjectView | None = None
    slots: dict[str, Any] = Field(default_factory=dict)
    human_mode: bool = False
    handoff_no: str | None = None


class HandoffRequestView(BaseModel):
    """一条转人工请求。"""

    handoff_no: str
    sender_id: str
    user_id: int | None = None
    session_id: str | None = None
    reason: str | None = None
    status: str
    agent_name: str | None = None
    created_at: datetime | None = None
    taken_at: datetime | None = None
    closed_at: datetime | None = None


class HandoffListResponse(BaseModel):
    list: list[HandoffRequestView]
    total: int


class HandoffTakeoverRequest(BaseModel):
    agent_name: str = "人工客服"


class HandoffReplyRequest(BaseModel):
    text: str
    agent_name: str | None = None


class HandoffReplyResponse(BaseModel):
    handoff_no: str
    text: str
    role: str = "agent"