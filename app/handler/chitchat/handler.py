from app.domain.messages import BotMessage, UserMessage
from app.domain.state import DialogueState
from app.handler.chitchat.responder import ChitchatResponder


class ChitchatHandler:
    """闲聊轨道的入口。"""

    def __init__(
        self,
        chitchat_responder: ChitchatResponder,
    ) -> None:
        self.chitchat_responder = chitchat_responder

    async def handle(
        self,
        state: DialogueState,
        user_message: UserMessage,
    ) -> list[BotMessage]:
        # 闲聊只参考当前会话的历史
        recent_turns = (
            state.shared_state.current_session().turns
        )
        return await self.chitchat_responder.respond(
            user_message=user_message,
            recent_turns=recent_turns,
        )