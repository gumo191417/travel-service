from app.domain.flow_catalog import FlowCatalog
from app.domain.messages import BotMessage
from app.domain.task_event import (
    TaskCanceled,
    TaskEvent,
    TaskResumed,
    TaskStarted,
    TaskSwitched,
)


class TaskLifecycleResponder:
    """把任务生命周期事件转换成提示语。"""

    def __init__(self, flow_catalog: FlowCatalog) -> None:
        self.flow_catalog = flow_catalog

    def respond(self, events: list[TaskEvent]) -> list[BotMessage]:
        # 按事件产生顺序逐条生成提示
        messages: list[BotMessage] = []
        for event in events:
            messages.append(self._message_for(event))
        return messages

    def _message_for(self, event: TaskEvent) -> BotMessage:
        # 不同类型的事件对应不同提示
        if isinstance(event, TaskStarted):
            flow_name = self._flow_name(event.task.flow_id)
            return BotMessage(
                text=f"好的，我们先处理{flow_name}。"
            )

        if isinstance(event, TaskSwitched):
            previous_name = self._flow_name(
                event.previous.flow_id
            )
            current_name = self._flow_name(
                event.current.flow_id
            )
            return BotMessage(
                text=(
                    f"好的，我们先把{previous_name}放一放，"
                    f"先处理{current_name}。"
                )
            )

        if isinstance(event, TaskResumed):
            flow_name = self._flow_name(event.task.flow_id)
            return BotMessage(
                text=f"好的，我们继续刚才的{flow_name}。"
            )

        if isinstance(event, TaskCanceled):
            flow_name = self._flow_name(event.task.flow_id)
            return BotMessage(
                text=f"好的，{flow_name}先帮你取消。"
            )

        raise TypeError(
            f"Unsupported task event: {type(event).__name__}"
        )

    def _flow_name(self, flow_id: str) -> str:
        # 优先使用用户可读的 Flow 名称
        flow = self.flow_catalog.get_flow(flow_id)
        if flow is None:
            return flow_id
        return flow.name or flow.id