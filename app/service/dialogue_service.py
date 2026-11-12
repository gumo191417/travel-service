from app.conf.config import settings
from app.domain.messages import ProcessResult, UserMessage
from app.domain.state import DialogueState, Session
from app.engine.dialogue_engine import DialogueEngine
from app.repository.dialogue_state_repository import (
    DialogueStateRepository,
)


class DialogueService:
    """接口层与对话引擎之间的入口"""

    def __init__(
        self,
        dialogue_state_repository: DialogueStateRepository,
        dialogue_engine: DialogueEngine,
    ) -> None:
        self.dialogue_state_repository = (
            dialogue_state_repository
        )
        self.dialogue_engine = dialogue_engine

    async def process_message(
        self,
        user_message: UserMessage,
        user_id: int | None = None,
    ) -> ProcessResult:
        # 1. 根据用户 ID 加载对话状态
        state = await self.dialogue_state_repository.load_state(
            user_message.sender_id
        )
        self._apply_user_id(state, user_id)

        # 2. 交给引擎处理
        process_result = await self.dialogue_engine.process_message(
            state,
            user_message,
        )

        # 3. 保存更新后的对话状态
        await self.dialogue_state_repository.save_state(state)

        # 4. 返回本轮处理结果
        return process_result

    async def get_state(
        self,
        sender_id: str,
    ) -> DialogueState:
        # 只读取状态，不保存
        return await self.dialogue_state_repository.load_state(
            sender_id
        )

    async def start_new_session(
        self,
        sender_id: str,
        user_id: int | None = None,
    ) -> Session:
        """关闭当前会话、清理运行态，并开启一段新会话。"""
        state = await self.dialogue_state_repository.load_state(
            sender_id
        )
        self._apply_user_id(state, user_id)

        if state.shared_state.sessions:
            state.shared_state.close_current_session()

        state.reset_runtime_state_for_new_session()
        state.shared_state.start_session()

        await self.dialogue_state_repository.save_state(state)
        return state.shared_state.current_session()

    @staticmethod
    def _apply_user_id(
        state: DialogueState,
        user_id: int | None,
    ) -> None:
        # 显式传入优先，其次保留历史值，最后回退到演示用户
        if user_id is not None:
            state.user_id = user_id
        elif state.user_id is None:
            state.user_id = settings.demo_user_id