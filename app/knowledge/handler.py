import asyncio

from app.domain.messages import BotMessage, UserMessage
from app.domain.state import DialogueState
from app.knowledge.intents import KnowledgeIntent
from app.knowledge.providers import (
    KnowledgeChunk,
    KnowledgeProvider,
)
from app.knowledge.responder import KnowledgeResponder


class KnowledgeHandler:
    """知识咨询的统一入口。"""

    def __init__(
        self,
        knowledge_responder: KnowledgeResponder,
        providers: list[KnowledgeProvider],
        knowledge_intents: dict[str, KnowledgeIntent],
    ) -> None:
        self._providers_by_id = {
            provider.provider_id: provider
            for provider in providers
        }
        self.knowledge_intents = knowledge_intents
        self._knowledge_responder = knowledge_responder

    async def handle(
        self,
        intents: list[str],
        state: DialogueState,
        user_message: UserMessage,
    ) -> list[BotMessage]:
        # 1. 根据意图标识，解析为预定义的知识意图对象
        resolved_intents = self._resolve_intents(intents)
        # 2. 收集所有关联的 Provider ID（去重）
        provider_ids = self._collect_provider_ids(
            resolved_intents
        )
        # 3. 并发调用各 Provider 检索相关片段
        chunks = await self._retrieve_all(
            state,
            user_message,
            provider_ids,
        )
        # 4. 交给应答器生成回复
        return await self._knowledge_responder.respond(
            user_message=user_message,
            recent_turns=self._recent_turns(state),
            chunks=chunks,
        )

    def _resolve_intents(
        self,
        intents: list[str],
    ) -> list[KnowledgeIntent]:
        resolved: list[KnowledgeIntent] = []
        for intent_id in intents:
            knowledge_intent = self.knowledge_intents.get(
                intent_id
            )
            if knowledge_intent:
                resolved.append(knowledge_intent)
        return resolved

    def _collect_provider_ids(
        self,
        resolved_intents: list[KnowledgeIntent],
    ) -> list[str]:
        provider_ids: set[str] = set()
        for knowledge_intent in resolved_intents:
            provider_ids.update(knowledge_intent.provider_ids)
        return list(provider_ids)

    async def _retrieve_all(
        self,
        state: DialogueState,
        user_message: UserMessage,
        provider_ids: list[str],
    ) -> list[KnowledgeChunk]:
        if not provider_ids:
            return []

        async def _safe_retrieve(
            provider_id: str,
        ) -> list[KnowledgeChunk]:
            # Provider 不存在或内部失败时返回空片段，不影响其他来源
            provider = self._providers_by_id.get(provider_id)
            if provider is None:
                return []
            try:
                return await provider.retrieve(
                    state,
                    user_message,
                )
            except Exception:
                return []

        chunks_list = await asyncio.gather(*[
            _safe_retrieve(provider_id)
            for provider_id in provider_ids
        ])
        return [
            chunk
            for chunks in chunks_list
            for chunk in chunks
        ]

    @staticmethod
    def _recent_turns(state: DialogueState):
        session = state.shared_state.current_session()
        return session.turns if session else []