import logging
import uuid
from contextlib import asynccontextmanager

from app.clients import database
from app.domain.messages import (
    BotMessage,
    MessageType,
    UserMessage,
)
from app.domain.state import DialogueState, Turn
from app.models.handoff_request import HandoffRequest
from app.repository.dialogue_state_repository import (
    DialogueStateRepository,
)
from app.repository.handoff_repository import HandoffRepository

logger = logging.getLogger(__name__)


class HandoffError(Exception):
    """转人工业务异常。"""


class HandoffNotFound(HandoffError):
    """转人工单不存在。"""


class HandoffClosed(HandoffError):
    """转人工单已关闭。"""


@asynccontextmanager
async def default_unit_of_work():
    """默认工作单元：一个请求共用一个数据库 Session。"""
    if database.session_factory is None:
        raise HandoffError("数据库尚未初始化")
    async with database.session_factory() as session:
        yield (
            HandoffRepository(session),
            DialogueStateRepository(session),
        )


class HandoffService:
    """转人工请求的创建、接单、回复与关闭。"""

    def __init__(self, unit_of_work=None) -> None:
        # 允许测试注入假的工作单元
        self._unit_of_work = unit_of_work or default_unit_of_work

    async def create_request(
        self,
        *,
        sender_id: str,
        user_id: int | None = None,
        session_id: str | None = None,
        reason: str | None = None,
    ) -> HandoffRequest:
        async with self._unit_of_work() as (
            handoff_repo,
            _,
        ):
            return await handoff_repo.create(
                sender_id=sender_id,
                user_id=user_id,
                session_id=session_id,
                reason=reason,
            )

    async def list_requests(
        self,
        status: str | None = None,
        limit: int = 50,
    ) -> list[HandoffRequest]:
        async with self._unit_of_work() as (
            handoff_repo,
            _,
        ):
            return await handoff_repo.list_requests(
                status=status,
                limit=limit,
            )

    async def takeover(
        self,
        handoff_no: str,
        agent_name: str,
    ) -> HandoffRequest:
        async with self._unit_of_work() as (
            handoff_repo,
            _,
        ):
            request = await handoff_repo.takeover(
                handoff_no, agent_name,
            )
            if request is None:
                raise HandoffNotFound(
                    f"转人工单不存在或已关闭: {handoff_no}"
                )
            return request

    async def reply(
        self,
        handoff_no: str,
        text: str,
        agent_name: str | None = None,
    ) -> HandoffRequest:
        content = (text or "").strip()
        if not content:
            raise HandoffError("回复内容不能为空")

        async with self._unit_of_work() as (
            handoff_repo,
            state_repo,
        ):
            request = await handoff_repo.get(handoff_no)
            if request is None:
                raise HandoffNotFound(
                    f"转人工单不存在: {handoff_no}"
                )
            if request.status == "closed":
                raise HandoffClosed(
                    f"转人工单已关闭: {handoff_no}"
                )

            # 未接单时，回复即视为接单
            handoff_repo.mark_taken_if_pending(
                request,
                agent_name or "人工客服",
            )

            # 行锁避免与用户消息互相覆盖
            state = await state_repo.load_state(
                request.sender_id,
                for_update=True,
            )
            self._append_agent_message(
                state,
                BotMessage(text=content, role="agent"),
            )
            # save_state 会提交本次事务，包括接单信息
            await state_repo.save_state(state)
            return request

    async def close(
        self,
        handoff_no: str,
    ) -> HandoffRequest:
        async with self._unit_of_work() as (
            handoff_repo,
            state_repo,
        ):
            request = await handoff_repo.get(handoff_no)
            if request is None:
                raise HandoffNotFound(
                    f"转人工单不存在: {handoff_no}"
                )

            handoff_repo.mark_closed(request)

            state = await state_repo.load_state(
                request.sender_id,
                for_update=True,
            )
            state.shared_state.human_mode = False
            state.shared_state.handoff_no = None
            await state_repo.save_state(state)
            return request

    @staticmethod
    def _append_agent_message(
        state: DialogueState,
        message: BotMessage,
    ) -> None:
        session = state.shared_state.current_session()
        if session is None:
            state.shared_state.start_session()
            session = state.shared_state.current_session()

        if session.turns:
            # 客服回复挂到用户最近一轮之后
            session.turns[-1].bot_messages.append(message)
            return

        # 极端情况：状态里没有轮次，补一轮占位，避免回复丢失
        session.turns.append(
            Turn(
                turn_id=str(uuid.uuid4()),
                user_message=UserMessage(
                    sender_id=state.sender_id,
                    message_id=str(uuid.uuid4()),
                    type=MessageType.TEXT,
                    text="（已转人工客服）",
                ),
                bot_messages=[message],
            )
        )