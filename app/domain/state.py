import time
import uuid
from typing import Any
from dataclasses import dataclass, field

from app.domain.messages import UserMessage, BotMessage
from app.domain.task import TaskState


@dataclass
class Turn:
    """一轮对话：一条用户消息 + 本轮产生的全部客服消息"""

    turn_id: str
    user_message: UserMessage
    bot_messages: list[BotMessage] = field(default_factory=list)

@dataclass
class Session:
    """一段连续的对话，保存开始、活跃、关闭时间及全部轮次"""

    session_id: str
    started_at: float
    last_activity_at: float
    closed_at: float | None = None
    turns: list[Turn] = field(default_factory=list)

@dataclass
class FocusedObject:
    """当前聚焦的订单业务对象"""

    type: str
    id: str
    title: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class SharedState:
    """三种对话类型共同使用的全局状态"""

    focused_object: FocusedObject | None = None
    sessions: list[Session] = field(default_factory=list)
    # 人工接管：开启后机器人不再自动回复
    human_mode: bool = False
    handoff_no: str | None = None

    def current_session(self) -> Session | None:
        # 会话按创建顺序保存，最后一个即当前会话
        if not self.sessions:
            return None
        return self.sessions[-1]

    def start_session(self):
        # 新建会话：唯一 ID + 当前时间作为开始/活跃时间
        now = time.time()
        session = Session(
            session_id=str(uuid.uuid4()),
            started_at=now,
            last_activity_at=now,
        )
        self.sessions.append(session)

    def close_current_session(self):
        # 只记录关闭时间，不删除会话
        self.current_session().closed_at = time.time()


@dataclass
class DialogueState:
    """某个用户的完整对话状态"""

    sender_id: str
    # 业务用户标识，用于请求头 X-User-Id；sender_id 只作为会话键
    user_id: int | None = None
    shared_state: SharedState = field(
        default_factory=SharedState
    )
    task_state: TaskState = field(
        default_factory=TaskState
    )

    def reset_runtime_state_for_new_session(self):
        # 清理只属于旧会话的运行状态
        self.shared_state.focused_object = None
        self.shared_state.human_mode = False
        self.shared_state.handoff_no = None
        self.task_state.active_task = None
        self.task_state.paused.clear()