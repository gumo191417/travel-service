from dataclasses import dataclass
from typing import TypeAlias


@dataclass
class TaskRef:
    """任务引用"""
    task_id: str
    flow_id: str


@dataclass
class TaskStarted:
    """某个任务刚刚开始执行，带上这个任务的引用。"""
    task: TaskRef


@dataclass
class TaskSwitched:
    """从【上一个任务】切到【当前任务】同时持有旧任务、新任务两个引用。"""
    previous: TaskRef
    current: TaskRef


@dataclass
class TaskResumed:
    """任务之前被挂起，现在重新跑起来。"""
    task: TaskRef


@dataclass
class TaskCanceled:
    """务被取消，不再继续执行。"""
    task: TaskRef

# 给联合类型起别名 :这个变量可以是上面 4 种事件中的任意一个
TaskEvent: TypeAlias = (TaskStarted | TaskSwitched | TaskResumed | TaskCanceled)