import json
from dataclasses import asdict

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate

from app.clients.llm import llm
from app.domain.flow_catalog import FlowCatalog
from app.domain.messages import UserMessage
from app.domain.plan import TurnPlan
from app.domain.state import DialogueState
from app.knowledge.intents import KnowledgeIntent
from app.prompts.history_builder import HistoryBuilder
from app.prompts.prompt_loader import load_prompt


class TurnPlanner:
    """理解用户消息并生成本轮 TurnPlan，不判断计划能否执行。"""

    async def predict(
        self,
        state: DialogueState,
        user_message: UserMessage,
        flow_catalog: FlowCatalog,
        knowledge_intents: dict[str, KnowledgeIntent],
    ) -> TurnPlan:
        # 1. 组装提示词变量
        variables = self._build_prompt_variables(
            state,
            user_message,
            flow_catalog,
            knowledge_intents,
        )

        # 2. 调用大模型解析计划
        result = await self._call_llm(
            load_prompt("turn_plan"),
            variables,
        )

        # 3. 输出字典转换为计划模型
        return TurnPlan.from_dict(result)

    async def _call_llm(
        self,
        prompt_text: str,
        variables: dict,
    ) -> dict:
        """单独抽出来，便于测试时替换大模型。"""
        prompt = PromptTemplate.from_template(
            prompt_text,
            template_format="jinja2",
        )
        chain = prompt | llm | JsonOutputParser()
        return await chain.ainvoke(variables)

    @staticmethod
    def _build_prompt_variables(
        state: DialogueState,
        user_message: UserMessage,
        flow_catalog: FlowCatalog,
        knowledge_intents: dict[str, KnowledgeIntent],
    ) -> dict:
        # 当前用户消息：统一渲染为文本
        user_message_text = HistoryBuilder.render_user_message(
            user_message
        )

        # 历史对话：取当前会话的全部 Turn
        session = state.shared_state.current_session()
        conversation_history = HistoryBuilder.build(
            session.turns if session else []
        )

        # 聚焦对象：无对象时传 null
        focused_object = state.shared_state.focused_object
        focused_object_json = json.dumps(
            asdict(focused_object) if focused_object else None,
            ensure_ascii=False,
            indent=2,
        )

        # 任务状态：活动任务与暂停任务
        task_state_json = json.dumps(
            asdict(state.task_state),
            ensure_ascii=False,
            indent=2,
        )

        # 知识意图：只保留 ID、说明和对象依赖
        knowledge_intents_json = json.dumps(
            [
                {
                    "id": intent.id,
                    "description": intent.description,
                    "requires_object": intent.requires_object,
                }
                for intent in knowledge_intents.values()
            ],
            ensure_ascii=False,
            indent=2,
        )

        # 流程能力：去掉 Planning 不需要的 steps
        flows_json = json.dumps(
            [
                {
                    key: value
                    for key, value in asdict(flow).items()
                    if key != "steps"
                }
                for flow in flow_catalog.flows.values()
            ],
            ensure_ascii=False,
            indent=2,
        )

        # 全局槽位目录：Flow.slots 只包含 collect 槽位，
        # 可选筛选字段（星级、车型等）要单独提供给模型
        slots_json = json.dumps(
            [
                {
                    "name": slot.name,
                    "type": slot.type,
                    "label": slot.label,
                    "description": slot.description,
                }
                for slot in flow_catalog.slots.values()
            ],
            ensure_ascii=False,
            indent=2,
        )

        return {
            "user_message": user_message_text,
            "conversation_history": conversation_history,
            "focused_object_json": focused_object_json,
            "task_state_json": task_state_json,
            "knowledge_intents_json": knowledge_intents_json,
            "flows_json": flows_json,
            "slots_json": slots_json,
        }