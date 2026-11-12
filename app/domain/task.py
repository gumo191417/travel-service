import uuid
from dataclasses import dataclass, field
from typing import Any

from app.domain.task_event import (
    TaskRef,
    TaskEvent,
    TaskStarted,
    TaskSwitched,
    TaskCanceled,
    TaskResumed,
)


@dataclass
class TaskInstance:
    """某条任务流程的一次具体执行"""

    flow_id: str
    step_id: str | None = None
    slots: dict[str, Any] = field(default_factory=dict)
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_ref(self) -> TaskRef:
        # 转换为只包含标识的任务引用
        return TaskRef(
            task_id=self.task_id,
            flow_id=self.flow_id,
        )


@dataclass
class TaskState:
    """当前活动任务与已暂停任务"""

    active_task: TaskInstance | None = None
    paused: list[TaskInstance] = field(default_factory=list)

    def start(self, task: TaskInstance) -> TaskEvent:
        # 没有活动任务：直接开始
        if self.active_task is None:
            self.active_task = task
            return TaskStarted(task=task.to_ref())

        # 已有活动任务：原任务进入暂停，新任务成为活动任务
        previous = self.active_task
        self.paused.append(previous)
        self.active_task = task
        return TaskSwitched(
            previous=previous.to_ref(),
            current=task.to_ref(),
        )

    def set_slots(self, slots: dict[str, Any]) -> None:
        # 向活动任务写入 Slot，不产生事件
        self.active_task.slots.update(slots)

    def remove_slot(self, slot_name: str) -> None:
        # 删除校验失败的 Slot
        self.active_task.slots.pop(slot_name, None)

    def cancel(self, task_id: str) -> TaskCanceled:
        # 取消活动任务：清空 active
        if self.active_task is not None and self.active_task.task_id == task_id:
            canceled = self.active_task
            self.active_task = None
            return TaskCanceled(task=canceled.to_ref())

        # 取消暂停任务：从 paused 中移除
        canceled = next(
            task
            for task in self.paused
            if task.task_id == task_id
        )
        self.paused.remove(canceled)
        return TaskCanceled(task=canceled.to_ref())

    def resume(self, task_id: str) -> TaskEvent:
        # 从 paused 中取出目标任务
        target = next(
            task
            for task in self.paused
            if task.task_id == task_id
        )
        self.paused.remove(target)

        # 没有活动任务：直接恢复
        if self.active_task is None:
            self.active_task = target
            return TaskResumed(task=target.to_ref())

        # 已有活动任务：原任务暂停，目标任务成为活动任务
        previous = self.active_task
        self.paused.append(previous)
        self.active_task = target
        return TaskSwitched(
            previous=previous.to_ref(),
            current=target.to_ref(),
        )