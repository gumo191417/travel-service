from dataclasses import dataclass, field
from enum import Enum
from typing import Any


@dataclass
class MessageObject:
    """用户从页面选择的订单等结构化对象"""

    type: str                                  # 对象类型，如 order
    id: str                                    # 对象唯一标识
    title: str | None = None                   # 对象标题
    attributes: dict[str, Any] = field(default_factory=dict)  # 扩展属性


@dataclass
class UserMessage:
    """一条用户消息"""

    sender_id: str
    message_id: str
    type: "MessageType"
    text: str | None = None                    # 文本消息内容
    object: MessageObject | None = None        # 对象消息内容


class MessageType(Enum):
    """消息类型"""

    TEXT = "text"
    OBJECT = "object"


@dataclass
class ProcessResult:
    """一次消息处理结果"""

    sender_id: str
    message_id: str
    messages: list["BotMessage"]               # 本轮产生的客服消息
    human_mode: bool = False                   # 当前是否处于人工接管模式


@dataclass
class BotMessage:
    """一条客服消息"""

    text: str | None = None
    object: MessageObject | None = None
    # 消息来源：bot 机器人，agent 人工客服
    role: str = "bot"