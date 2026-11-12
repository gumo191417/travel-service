from dataclasses import dataclass, fields
from typing import Any


@dataclass
class Command:
    command: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Command":
        # 非字典或未知命令返回占位对象，交给校验器判 INVALID_TASK_COMMAND
        if not isinstance(data, dict):
            return Command(command="")

        name = str(data.get("command") or "").strip()
        command_class = COMMAND_NAME_TO_CLASS.get(name)
        if command_class is None:
            return Command(command=name)

        # 只保留命令类声明的字段，忽略 LLM 多输出的说明性字段
        field_names = {item.name for item in fields(command_class)}
        payload = {
            key: value
            for key, value in data.items()
            if key in field_names
        }
        try:
            return command_class(**payload)
        except TypeError:
            # 缺少必填字段时同样降级为占位命令
            return Command(command=name)


@dataclass
class StartFlowCommand(Command):
    flow: str


@dataclass
class SetSlotsCommand(Command):
    slots: dict[str, Any]


@dataclass
class CancelTaskCommand(Command):
    task_id: str


@dataclass
class ResumeTaskCommand(Command):
    task_id: str

COMMAND_NAME_TO_CLASS: dict[str, type[Command]] = {
    "start_flow": StartFlowCommand,
    "set_slots": SetSlotsCommand,
    "cancel_task": CancelTaskCommand,
    "resume_task": ResumeTaskCommand,
}