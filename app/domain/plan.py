from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from app.domain.command import Command


@dataclass
class TaskTurnPlan:
    commands: list[Command] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "TaskTurnPlan":
        # commands 缺失或类型不对时按空列表处理，交给校验器判定
        raw_commands = (
            data.get("commands", [])
            if isinstance(data, dict)
            else []
        )
        if not isinstance(raw_commands, list):
            raw_commands = []

        return cls(
            commands=[
                Command.from_dict(command)
                for command in raw_commands
                if isinstance(command, dict)
            ]
        )


@dataclass
class KnowledgeTurnPlan:
    intents: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(
        cls,
        data: dict,
    ) -> "KnowledgeTurnPlan":
        raw_intents = (
            data.get("intents", [])
            if isinstance(data, dict)
            else []
        )
        if not isinstance(raw_intents, list):
            raw_intents = []

        return cls(
            intents=[
                str(intent)
                for intent in raw_intents
                if isinstance(intent, str)
            ]
        )


@dataclass
class ChitchatTurnPlan:
    pass


@dataclass
class TurnPlan:
    task: TaskTurnPlan | None = None
    knowledge: KnowledgeTurnPlan | None = None
    chitchat: ChitchatTurnPlan | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "TurnPlan":
        if not isinstance(data, dict):
            return cls()

        # 空字典按"未命中"处理；chitchat 的空字典是合法值
        task_data = data.get("task")
        knowledge_data = data.get("knowledge")
        chitchat_data = data.get("chitchat")

        return cls(
            task=(
                TaskTurnPlan.from_dict(task_data)
                if task_data
                else None
            ),
            knowledge=(
                KnowledgeTurnPlan.from_dict(knowledge_data)
                if knowledge_data
                else None
            ),
            chitchat=(
                ChitchatTurnPlan()
                if chitchat_data is not None
                else None
            ),
        )


class ClarifyReason(str, Enum):
    """计划无法执行的原因，供 ClarifyResponder 生成澄清回复。"""

    MISSING_TRACK = "missing_track"                          # 三个方向都为空
    MULTIPLE_TRACKS = "multiple_tracks"                      # 同时命中多个方向
    MISSING_TASK_COMMANDS = "missing_task_commands"          # 任务计划无 Command
    MISSING_KNOWLEDGE_INTENT = "missing_knowledge_intent"    # 知识计划无 Intent
    MISSING_FOCUSED_OBJECT = "missing_focused_object"        # 缺少所需聚焦对象
    OBJECT_REQUIRES_INTENT = "object_requires_intent"        # 只有对象、没有操作意图
    INVALID_TASK_COMMAND = "invalid_task_command"            # Command 在当前状态下不可执行
    UNKNOWN_KNOWLEDGE_INTENT = "unknown_knowledge_intent"    # Intent 不受系统支持


@dataclass
class TurnPlanValidationResult:
    """计划校验结果：valid 为 False 时 reason 说明原因。"""

    valid: bool
    reason: ClarifyReason | None = None