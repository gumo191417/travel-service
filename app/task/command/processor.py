from app.domain.command import (
    CancelTaskCommand,
    Command,
    ResumeTaskCommand,
    SetSlotsCommand,
    StartFlowCommand,
)
from app.domain.flow_catalog import FlowCatalog
from app.domain.state import DialogueState
from app.domain.task import TaskInstance
from app.domain.task_event import TaskEvent


class CommandProcessor:
    """把本轮命令应用到任务状态，并收集产生的事件。"""

    def run(
        self,
        commands: list[Command],
        state: DialogueState,
        flow_catalog: FlowCatalog,
    ) -> list[TaskEvent]:
        events: list[TaskEvent] = []
        for command in commands:
            event = self._apply(command, state, flow_catalog)
            if event is not None:
                events.append(event)
        return events

    def _apply(
        self,
        command: Command,
        state: DialogueState,
        flow_catalog: FlowCatalog,
    ) -> TaskEvent | None:
        # 一条命令最多产生一个事件；set_slots 不产生事件

        if isinstance(command, StartFlowCommand):
            # 取得 Flow 与起始 Step，创建并启动任务实例
            flow = flow_catalog.get_flow(command.flow)
            start_step = (
                flow.get_start_step() if flow is not None else None
            )
            if flow is None or start_step is None:
                return None

            task = TaskInstance(
                flow_id=flow.id,
                step_id=start_step.id,
            )
            return state.task_state.start(task)

        if isinstance(command, SetSlotsCommand):
            # 只写入活动任务的 Slot；没有活动任务时忽略
            if state.task_state.active_task is None:
                return None
            state.task_state.set_slots(command.slots)
            return None

        if isinstance(command, CancelTaskCommand):
            try:
                return state.task_state.cancel(command.task_id)
            except StopIteration:
                return None

        if isinstance(command, ResumeTaskCommand):
            try:
                return state.task_state.resume(command.task_id)
            except StopIteration:
                return None

        return None