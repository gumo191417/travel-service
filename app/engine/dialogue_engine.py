import logging
import time
import uuid

from app.clarify.responder import ClarifyResponder
from app.domain.command import SetSlotsCommand
from app.domain.flow_catalog import CollectSlotStep
from app.domain.messages import (
    BotMessage,
    MessageType,
    ProcessResult,
    UserMessage,
)
from app.domain.plan import ClarifyReason
from app.domain.state import (
    DialogueState,
    FocusedObject,
    Turn,
)
from app.handler.chitchat.handler import ChitchatHandler
from app.knowledge.handler import KnowledgeHandler
from app.plan.turn_planner import TurnPlanner
from app.plan.validator import TurnPlanValidator
from app.task.flow.object_fill import match_object_slot
from app.task.task_handler import TaskHandler

logger = logging.getLogger(__name__)

# 处理失败时返回给用户的兜底话术
FALLBACK_MESSAGE = (
    "抱歉，刚才处理时出了点问题，"
    "请换个说法再试一次。"
)


class DialogueEngine:
    """对话总入口：组织三条轨道与澄清，不直接访问外部服务。"""

    def __init__(
        self,
        turn_planner: TurnPlanner,
        task_handler: TaskHandler,
        knowledge_handler: KnowledgeHandler,
        chitchat_handler: ChitchatHandler,
        clarify_responder: ClarifyResponder,
        turn_plan_validator: TurnPlanValidator,
        idle_timeout_seconds: int = 60 * 60,
    ) -> None:
        self.turn_planner = turn_planner
        self.task_handler = task_handler
        self.knowledge_handler = knowledge_handler
        self.chitchat_handler = chitchat_handler
        self.clarify_responder = clarify_responder
        self.turn_plan_validator = turn_plan_validator
        self.idle_timeout_seconds = idle_timeout_seconds

    async def process_message(
        self,
        state: DialogueState,
        user_message: UserMessage,
    ) -> ProcessResult:
        # 1. 确保存在可用的 Session
        self._prepare_session(state)

        # 2. 为本轮消息创建 Turn
        turn = Turn(
            turn_id=str(uuid.uuid4()),
            user_message=user_message,
        )

        # 3. 按消息类型选择处理逻辑
        try:
            if state.shared_state.human_mode:
                messages = await self._handle_human_mode(
                    state=state,
                    user_message=user_message,
                )
            elif user_message.type is MessageType.TEXT:
                messages = await self._handle_text_message(
                    state=state,
                    user_message=user_message,
                )
            else:
                messages = await self._handle_object_message(
                    state=state,
                    user_message=user_message,
                )
        except Exception:
            # 单轮失败不影响后续对话
            logger.exception(
                "处理用户消息失败: sender_id=%s",
                user_message.sender_id,
            )
            messages = [BotMessage(text=FALLBACK_MESSAGE)]

        # 4. 本轮全部客服消息与用户消息一起提交
        turn.bot_messages.extend(messages)
        state.shared_state.current_session().turns.append(turn)

        # 5. 返回本轮处理结果
        return ProcessResult(
            sender_id=user_message.sender_id,
            message_id=user_message.message_id,
            messages=messages,
            human_mode=state.shared_state.human_mode,
        )

    async def _handle_human_mode(
        self,
        state: DialogueState,
        user_message: UserMessage,
    ) -> list[BotMessage]:
        # 人工接管中：消息只入库，客服通过接口回复
        return []

    def _prepare_session(self, state: DialogueState) -> None:
        """
        会话生命周期维护
        规则：会话闲置超过阈值，则关闭旧会话，清空上下文，新建会话
        每次调用更新会话最后活跃时间
        """
        now = time.time()

        # 不存在会话，直接新建
        if not state.shared_state.sessions:
            state.shared_state.start_session()
            return

        current_session = state.shared_state.current_session()
        if (
            now - current_session.last_activity_at
            > self.idle_timeout_seconds
        ):
            state.shared_state.close_current_session()
            state.reset_runtime_state_for_new_session()
            state.shared_state.start_session()
        else:
            current_session.last_activity_at = now

    async def _handle_text_message(
        self,
        state: DialogueState,
        user_message: UserMessage,
    ) -> list[BotMessage]:
        # 1. 生成计划
        turn_plan = await self.turn_planner.predict(
            state,
            user_message,
            self.task_handler.flow_catalog,
            self.knowledge_handler.knowledge_intents,
        )

        # 2. 校验计划
        validation_result = self.turn_plan_validator.validate(
            turn_plan,
            state,
            self.task_handler.flow_catalog,
            self.knowledge_handler.knowledge_intents,
        )

        # 3. 校验失败：交给 ClarifyResponder
        if not validation_result.valid:
            return await self.clarify_responder.respond(
                validation_result.reason,
                state,
                user_message,
            )

        # 4. 执行唯一有效方向
        if turn_plan.task:
            return await self.task_handler.handle(
                turn_plan.task.commands,
                state,
                user_message,
            )

        if turn_plan.knowledge:
            return await self.knowledge_handler.handle(
                turn_plan.knowledge.intents,
                state,
                user_message,
            )

        return await self.chitchat_handler.handle(
            state,
            user_message,
        )

    async def _handle_object_message(
        self,
        state: DialogueState,
        user_message: UserMessage,
    ) -> list[BotMessage]:
        # 对象消息先记录为当前聚焦对象
        message_object = user_message.object
        if message_object is None:
            return await self.clarify_responder.respond(
                ClarifyReason.OBJECT_REQUIRES_INTENT,
                state,
                user_message,
            )

        state.shared_state.focused_object = FocusedObject(
            type=message_object.type,
            id=message_object.id,
            title=message_object.title,
            attributes=dict(message_object.attributes),
        )

        matched = self._match_object_slot(state)
        if matched is None:
            # 无法补充任务：询问用户想对对象做什么
            return await self.clarify_responder.respond(
                ClarifyReason.OBJECT_REQUIRES_INTENT,
                state,
                user_message,
            )

        # 对象可补活动任务正在收集的 Slot
        slot_name, value = matched
        command = SetSlotsCommand(
            command="set_slots",
            slots={slot_name: value},
        )
        return await self.task_handler.handle(
            [command],
            state,
            user_message,
        )

    def _match_object_slot(
        self,
        state: DialogueState,
    ) -> tuple[str, object] | None:
        # 1. 必须存在活动任务
        active_task = state.task_state.active_task
        if active_task is None:
            return None

        # 2. 取得活动任务当前 Step
        flow = self.task_handler.flow_catalog.get_flow(
            active_task.flow_id
        )
        if flow is None:
            return None

        step = flow.get_step(active_task.step_id)
        if not isinstance(step, CollectSlotStep):
            return None

        # 3. 对象类型与槽位声明匹配时才能补槽
        return match_object_slot(
            flow,
            step,
            state.shared_state.focused_object,
        )