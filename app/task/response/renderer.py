import logging

from jinja2 import Template
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from app.clients.llm import llm
from app.domain.flow_catalog import ResponseMode, ResponseTemplate
from app.domain.messages import BotMessage, UserMessage
from app.domain.state import DialogueState
from app.prompts.history_builder import HistoryBuilder

logger = logging.getLogger(__name__)


class ResponseRenderer:
    """按模板生成客服回复，支持 static 与 rephrase 两种模式。"""

    async def render(
        self,
        template: ResponseTemplate,
        state: DialogueState,
        user_message: UserMessage | None = None,
    ) -> BotMessage:
        slots = (
            state.task_state.active_task.slots
            if state.task_state.active_task
            else {}
        )

        # 1. 先用 Jinja2 渲染基础文案
        base_text = Template(template.text or "").render(
            slots=slots
        )

        # 2. 静态回复直接返回
        if template.mode is ResponseMode.STATIC:
            return BotMessage(text=base_text)

        # 3. 改写模式：没有配置 prompt 时退回基础文案
        if template.mode is ResponseMode.REPHRASE:
            if not template.prompt:
                return BotMessage(text=base_text)
            try:
                text = await self._call_llm(
                    template.prompt,
                    state,
                    user_message,
                    current_response=base_text,
                )
            except Exception:
                # 大模型不可用时不影响业务回复
                logger.exception("回复改写失败，返回基础文案")
                return BotMessage(text=base_text)
            return BotMessage(text=text)

        return BotMessage(text=base_text)

    async def _call_llm(
        self,
        prompt_text: str,
        state: DialogueState,
        user_message: UserMessage | None,
        current_response: str = "",
    ) -> str:
        # Jinja2 格式的提示词 + 大模型
        prompt = PromptTemplate.from_template(
            prompt_text,
            template_format="jinja2",
        )
        chain = prompt | llm | StrOutputParser()

        session = state.shared_state.current_session()
        turns = session.turns if session else []

        return await chain.ainvoke({
            "history": HistoryBuilder.build(turns),
            "user_message": (
                HistoryBuilder.render_user_message(user_message)
                if user_message
                else ""
            ),
            "current_response": current_response,
        })