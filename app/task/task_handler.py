from app.domain.command import Command
from app.domain.flow_catalog import FlowCatalog
from app.domain.messages import BotMessage, UserMessage
from app.domain.state import DialogueState
from app.task.command.processor import CommandProcessor
from app.task.flow.executor import FlowExecutor
from app.task.lifecycle.responder import TaskLifecycleResponder


class TaskHandler:
    """任务轨道的统一入口：命令 -> 事件提示 -> Flow 推进。"""

    def __init__(
        self,
        command_processor: CommandProcessor,
        flow_catalog: FlowCatalog,
        flow_executor: FlowExecutor,
        lifecycle_responder: TaskLifecycleResponder,
    ) -> None:
        self.command_processor = command_processor
        self.flow_catalog = flow_catalog
        self.flow_executor = flow_executor
        self.lifecycle_responder = lifecycle_responder

    async def handle(
        self,
        commands: list[Command],
        state: DialogueState,
        user_message: UserMessage,
    ) -> list[BotMessage]:
        # 1. 执行 Commands，得到任务事件
        events = self.command_processor.run(
            commands,
            state,
            self.flow_catalog,
        )

        # 2. 任务事件转换为状态提示
        messages = self.lifecycle_responder.respond(events)

        # 3. 从当前 Step 推进活动任务，并追加 Flow 消息
        messages.extend(
            await self.flow_executor.run_task(
                state,
                self.flow_catalog,
                user_message,
            )
        )

        # 4. 返回本轮全部消息
        return messages