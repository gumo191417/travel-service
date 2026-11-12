import json
from dataclasses import asdict

from app.domain.messages import BotMessage, MessageType, UserMessage
from app.domain.state import Turn


class HistoryBuilder:
    """把对话轮次拼成提示词使用的纯文本历史。"""

    @staticmethod
    def build(turns: list[Turn]) -> str:
        # 依次输出用户消息、客服消息
        messages: list[str] = []
        for turn in turns:
            messages.append(
                HistoryBuilder.render_user_message(
                    turn.user_message
                )
            )
            for bot_message in turn.bot_messages:
                messages.append(
                    HistoryBuilder.render_bot_message(bot_message)
                )
        return "\n".join(messages)

    @staticmethod
    def render_user_message(user_message: UserMessage) -> str:
        # 文本消息直接输出，对象消息转为单行 JSON
        if user_message.type is MessageType.TEXT:
            return f"USER: {user_message.text}"

        if user_message.object is None:
            return "USER: "

        return (
            "USER: "
            f"{json.dumps(asdict(user_message.object), ensure_ascii=False)}"
        )

    @staticmethod
    def render_bot_message(bot_message: BotMessage) -> str:
        # 文本优先；否则输出对象 JSON
        if bot_message.text:
            return f"BOT: {bot_message.text}"

        if bot_message.object is None:
            return "BOT: "

        return (
            "BOT: "
            f"{json.dumps(asdict(bot_message.object), ensure_ascii=False)}"
        )