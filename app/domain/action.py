from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.domain.state import DialogueState


@dataclass
class ActionResult:
    """Action 执行结果，slot_updates 会被写回活动任务"""

    slot_updates: dict[str, Any] = field(default_factory=dict)


class Action(ABC):
    """自定义 Action 的抽象父类"""

    name: str

    @abstractmethod
    async def run(self, state: DialogueState) -> ActionResult:
        pass