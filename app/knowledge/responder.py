from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from app.clients.llm import llm
from app.domain.messages import BotMessage, UserMessage
from app.domain.state import Turn
from app.knowledge.providers import KnowledgeChunk
from app.prompts.history_builder import HistoryBuilder
from app.prompts.prompt_loader import load_prompt


class KnowledgeResponder:
    """把检索片段和对话上下文交给大模型，生成客服回复。"""

    async def respond(
        self,
        user_message: UserMessage,
        recent_turns: list[Turn],
        chunks: list[KnowledgeChunk],
    ) -> list[BotMessage]:
        # 1. 准备提示词变量
        variables = {
            "user_message": HistoryBuilder.render_user_message(
                user_message
            ),
            "history": HistoryBuilder.build(recent_turns),
            # 多个知识片段之间用空行分隔
            "knowledge_content": "\n\n".join(
                chunk.content for chunk in chunks
            ),
        }

        # 2. 加载提示词并调用大模型
        prompt_text = load_prompt("knowledge_respond")
        response = await self._call_llm(prompt_text, variables)

        # 3. 包装为客服消息列表
        return [BotMessage(text=response)]

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