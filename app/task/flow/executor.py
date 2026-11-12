import logging
from typing import Any

from app.domain.flow_catalog import (
    ActionFlowStep,
    CollectSlotStep,
    ConditionalLink,
    EndFlowStep,
    FallbackLink,
    Flow,
    FlowCatalog,
    FlowStep,
    ResponseFlowStep,
    StartFlowStep,
    StaticLink,
)
from app.domain.messages import BotMessage, UserMessage
from app.domain.state import DialogueState
from app.task.action.runner import ActionRunner
from app.task.flow.object_fill import match_object_slot
from app.task.response.renderer import ResponseRenderer

logger = logging.getLogger(__name__)


class FlowExecutor:
    """按 Step 推进活动任务，直到需要用户输入或任务结束。"""

    def __init__(
        self,
        action_runner: ActionRunner,
        response_renderer: ResponseRenderer,
        max_steps_per_turn: int = 100,
    ) -> None:
        self.action_runner = action_runner
        self.response_renderer = response_renderer
        self.max_steps_per_turn = max_steps_per_turn

    async def run_task(
        self,
        state: DialogueState,
        flow_catalog: FlowCatalog,
        user_message: UserMessage,
    ) -> list[BotMessage]:
        # 本轮累计的消息
        messages: list[BotMessage] = []

        # 每轮循环都重新读取活动任务，保证拿到最新 Step
        for _ in range(self.max_steps_per_turn):
            task = state.task_state.active_task
            if task is None:
                return messages

            flow = flow_catalog.get_flow(task.flow_id)
            if flow is None:
                logger.warning(
                    "活动任务引用了不存在的 Flow: %s",
                    task.flow_id,
                )
                state.task_state.active_task = None
                return messages

            step = flow.get_step(task.step_id)
            if step is None:
                logger.warning(
                    "Flow %s 中找不到 Step: %s",
                    task.flow_id,
                    task.step_id,
                )
                state.task_state.active_task = None
                return messages

            # start：直接进入下一个 Step
            if isinstance(step, StartFlowStep):
                self._advance(step, state)
                continue

            # response：生成回复后进入下一个 Step
            if isinstance(step, ResponseFlowStep):
                messages.append(
                    await self.response_renderer.render(
                        step.template,
                        state,
                        user_message=user_message,
                    )
                )
                self._advance(step, state)
                continue

            # collect：收集 Slot，需要用户输入时停止推进
            if isinstance(step, CollectSlotStep):
                should_wait = await self._run_collect_step(
                    step,
                    flow,
                    state,
                    user_message,
                    messages,
                )
                if should_wait:
                    return messages
                self._advance(step, state)
                continue

            # action：执行 Action 并写回 Slot，再进入下一个 Step
            if isinstance(step, ActionFlowStep):
                result = await self.action_runner.run(
                    step.action,
                    state,
                )
                if result.slot_updates:
                    state.task_state.set_slots(
                        result.slot_updates
                    )
                self._advance(step, state)
                continue

            # end：完成活动任务
            if isinstance(step, EndFlowStep):
                state.task_state.active_task = None
                return messages

        # 单轮推进步数过多，停止以避免死循环
        logger.warning(
            "单轮推进超过 %s 步，停止执行",
            self.max_steps_per_turn,
        )
        return messages

    def _advance(
        self,
        step: FlowStep,
        state: DialogueState,
    ) -> None:
        # 选择下一个 Step，只改 step_id，不立即执行
        task = state.task_state.active_task
        if task is None:
            return

        for link in step.next:
            if isinstance(link, StaticLink):
                task.step_id = link.target
                return

            if (
                isinstance(link, ConditionalLink)
                and self.validate_condition(
                    link.condition,
                    {"slots": task.slots},
                )
            ):
                task.step_id = link.target
                return

            if isinstance(link, FallbackLink):
                task.step_id = link.target
                return

        # 没有可走的连线：结束任务，避免卡在同一个 Step
        logger.warning(
            "Step %s 没有可用的下一跳，任务结束",
            step.id,
        )
        state.task_state.active_task = None

    def validate_condition(
        self,
        condition: str,
        data: dict[str, Any],
    ) -> bool:
        """
        条件表达式校验：基于 data 计算布尔表达式
        第二个参数清空内置函数，做沙箱隔离
        """
        try:
            return bool(
                eval(condition, {"__builtins__": {}}, data)
            )
        except Exception:
            logger.exception(
                "条件表达式执行失败: %s",
                condition,
            )
            return False

    async def _run_collect_step(
        self,
        step: CollectSlotStep,
        flow: Flow,
        state: DialogueState,
        user_message: UserMessage,
        bot_messages: list[BotMessage],
    ) -> bool:
        task = state.task_state.active_task

        # 1. Slot 为空时，先尝试从聚焦对象补充
        slot_value = task.slots.get(step.slot_name)
        if not slot_value:
            self._try_to_fill_slot_from_focused_object(
                step,
                flow,
                state,
            )

        # 2. 重新读取 Slot
        slot_value = task.slots.get(step.slot_name)

        # 3. 仍然为空：询问用户并等待输入
        if not slot_value:
            bot_messages.append(
                await self.response_renderer.render(
                    step.template,
                    state,
                    user_message,
                )
            )
            return True

        # 4. 未配置校验：直接通过
        if not step.validation:
            return False

        # 5. 校验 Slot：失败时删除并等待重新输入
        result = self.validate_condition(
            step.validation.condition,
            {"slots": task.slots},
        )
        if result:
            return False

        state.task_state.remove_slot(step.slot_name)
        bot_messages.append(
            await self.response_renderer.render(
                step.validation.failure_template,
                state,
                user_message,
            )
        )
        return True

    @staticmethod
    def _try_to_fill_slot_from_focused_object(
        step: CollectSlotStep,
        flow: Flow,
        state: DialogueState,
    ) -> None:
        matched = match_object_slot(
            flow,
            step,
            state.shared_state.focused_object,
        )
        if matched is None:
            return

        slot_name, value = matched
        state.task_state.set_slots({
            slot_name: value
        })