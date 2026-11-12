import json
import logging
from dataclasses import asdict

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from app.clients.llm import llm
from app.domain.messages import BotMessage, UserMessage
from app.domain.plan import ClarifyReason
from app.domain.state import DialogueState
from app.prompts.history_builder import HistoryBuilder
from app.prompts.prompt_loader import load_prompt

logger = logging.getLogger(__name__)


class ClarifyResponder:
    """按澄清原因生成话术，并交给大模型自然化。"""

    async def respond(
        self,
        reason: ClarifyReason,
        state: DialogueState,
        user_message: UserMessage,
    ) -> list[BotMessage]:
        # 1. 根据原因生成基础澄清话术
        clarify_message = self.build_clarify_message(
            reason=reason,
            state=state,
        )

        # 2. 准备当前用户消息、历史对话、聚焦对象
        session = state.shared_state.current_session()
        focused_object = state.shared_state.focused_object

        variables = {
            "reason": reason.value,
            "clarify_message": clarify_message,
            "focused_object": (
                json.dumps(
                    asdict(focused_object),
                    ensure_ascii=False,
                )
                if focused_object is not None
                else None
            ),
            "history": HistoryBuilder.build(
                session.turns if session else []
            ),
            "user_message": HistoryBuilder.render_user_message(
                user_message
            ),
        }

        # 3. 调用大模型完成自然化改写
        try:
            rewritten = await self._call_llm(
                load_prompt("clarify_respond"),
                variables,
            )
        except Exception:
            # 改写失败不影响澄清本身
            logger.exception("澄清话术改写失败，返回基础话术")
            return [BotMessage(text=clarify_message)]

        # 4. 包装为客服消息列表
        return [BotMessage(text=rewritten)]

    async def _call_llm(
        self,
        prompt_text: str,
        variables: dict,
    ) -> str:
        """单独抽出来，便于测试时替换大模型。"""
        prompt = PromptTemplate.from_template(
            prompt_text,
            template_format="jinja2",
        )
        chain = prompt | llm | StrOutputParser()
        return await chain.ainvoke(variables)

    def build_clarify_message(
        self,
        reason: ClarifyReason,
        state: DialogueState,
    ) -> str:
        # 每个澄清原因对应一条基础话术
        if reason is ClarifyReason.MISSING_TRACK:
            return (
                "你是想查产品、查订单，"
                "还是咨询退改政策呢？"
            )

        if reason is ClarifyReason.MULTIPLE_TRACKS:
            return (
                "你这次同时提到了多个方向。我们先处理一个，"
                "你想先办业务还是先咨询信息呢？"
            )

        if reason is ClarifyReason.MISSING_TASK_COMMANDS:
            return (
                "你想办理什么业务呢？"
                "比如查订单状态、查行程信息，或者申请退款。"
            )

        if reason is ClarifyReason.MISSING_KNOWLEDGE_INTENT:
            return (
                "你想了解酒店、景点、交通票务，"
                "还是退改政策和预订规则呢？"
            )

        if reason is ClarifyReason.MISSING_FOCUSED_OBJECT:
            return (
                "请先选择你想咨询的产品或订单，"
                "我再继续帮你看。"
            )

        if reason is ClarifyReason.OBJECT_REQUIRES_INTENT:
            return self._object_clarify_message(state)

        if reason is ClarifyReason.INVALID_TASK_COMMAND:
            return (
                "当前任务状态不支持这个操作。"
                "你可以告诉我想开始、继续还是取消哪个任务。"
            )

        if reason is ClarifyReason.UNKNOWN_KNOWLEDGE_INTENT:
            return (
                "我暂时没能识别这个咨询方向。"
                "你可以具体说说想了解的酒店、景点、"
                "交通或者订单问题。"
            )

        # 无对应分支时的通用话术
        return (
            "我还需要再确认一下你的意思，"
            "你可以换个更具体的说法告诉我。"
        )

    @staticmethod
    def _object_clarify_message(state: DialogueState) -> str:
        # 不同业务对象可以执行的操作不同
        focused_object = state.shared_state.focused_object
        if focused_object is None:
            return (
                "我已经收到你选择的内容了。"
                "你想了解详情、查政策，还是办理售后呢？"
            )

        object_type = focused_object.type

        if object_type == "order":
            return (
                "我已经收到这个订单了。你想查订单状态、"
                "查行程信息，还是申请退款呢？"
            )

        if object_type == "hotel":
            return (
                "我已经收到这家酒店了。你想了解房型设施、"
                "入住退房时间，还是退改政策呢？"
            )

        if object_type == "scenic":
            return (
                "我已经收到这个景点门票了。你想了解景点介绍、"
                "开放时间，还是退改政策呢？"
            )

        if object_type in ("flight", "train", "bus"):
            return (
                "我已经收到这个班次了。你想了解出发到达时间、"
                "舱位席位，还是退改政策呢？"
            )

        if object_type == "transfer":
            return (
                "我已经收到这个接送服务了。你想了解车型、"
                "载客人数，还是服务范围呢？"
            )

        return (
            "我已经收到你选择的内容了。"
            "你想了解详情、查政策，还是办理售后呢？"
        )