from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.clients.travel_api import (
    api_get,
    find_order_by_no,
    get_order_detail,
    http_error_text,
    resolve_user_id,
)
from app.domain.messages import UserMessage
from app.domain.state import DialogueState, FocusedObject
from app.knowledge.faq import FAQSelector, load_faq_entries
from app.prompts.history_builder import HistoryBuilder

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeChunk:
    """一段可以提供给大模型的知识内容"""

    content: str


class KnowledgeProvider(ABC):
    """所有知识来源的统一接口"""

    provider_id = ""

    @abstractmethod
    async def retrieve(
        self,
        state: DialogueState,
        user_message: UserMessage,
    ) -> list[KnowledgeChunk]:
        pass


def _focused_object(
    state: DialogueState,
    object_type: str,
) -> FocusedObject | None:
    """取指定类型的聚焦对象，类型不匹配时返回 None。"""
    focused_object = state.shared_state.focused_object
    if focused_object is None:
        return None
    if focused_object.type != object_type:
        return None
    return focused_object


def _json_chunk(title: str, data) -> KnowledgeChunk:
    return KnowledgeChunk(
        content=(
            f"{title}：\n"
            f"{json.dumps(data, ensure_ascii=False, indent=2)}"
        )
    )


def _error_chunk(title: str, exc: Exception) -> KnowledgeChunk:
    return KnowledgeChunk(
        content=f"{title}获取失败：{http_error_text(exc)}"
    )


class _DetailProvider(KnowledgeProvider):
    """按聚焦对象 ID 查询详情的 Provider 基类。"""

    object_type = ""
    path_template = ""
    title = ""

    async def retrieve(
        self,
        state: DialogueState,
        user_message: UserMessage,
    ) -> list[KnowledgeChunk]:
        focused_object = _focused_object(
            state,
            self.object_type,
        )
        if focused_object is None:
            return []

        path = self.path_template.format(
            object_id=focused_object.id
        )
        try:
            data = await api_get(path)
        except Exception as exc:
            return [_error_chunk(self.title, exc)]

        return [_json_chunk(self.title, data)]


class HotelAPIProvider(_DetailProvider):
    """酒店详情"""

    provider_id = "api.hotel"
    object_type = "hotel"
    path_template = "/hotels/{object_id}"
    title = "酒店信息"


class ScenicAPIProvider(_DetailProvider):
    """景点详情"""

    provider_id = "api.scenic"
    object_type = "scenic"
    path_template = "/scenic-spots/{object_id}"
    title = "景点信息"


class FlightAPIProvider(_DetailProvider):
    """航班详情"""

    provider_id = "api.flight"
    object_type = "flight"
    path_template = "/flights/{object_id}"
    title = "航班信息"


class TrainAPIProvider(_DetailProvider):
    """车次详情"""

    provider_id = "api.train"
    object_type = "train"
    path_template = "/trains/{object_id}"
    title = "车次信息"


class BusAPIProvider(_DetailProvider):
    """汽车班次详情"""

    provider_id = "api.bus"
    object_type = "bus"
    path_template = "/buses/{object_id}"
    title = "班次信息"


class TransferAPIProvider(_DetailProvider):
    """接送服务详情"""

    provider_id = "api.transfer"
    object_type = "transfer"
    path_template = "/transfers/{object_id}"
    title = "接送服务信息"


class OrderAPIProvider(KnowledgeProvider):
    """订单详情：订单号 -> 订单 ID -> 详情"""

    provider_id = "api.order"

    async def retrieve(
        self,
        state: DialogueState,
        user_message: UserMessage,
    ) -> list[KnowledgeChunk]:
        focused_object = _focused_object(state, "order")
        if focused_object is None:
            return []

        user_id = resolve_user_id(state)
        try:
            order = await find_order_by_no(
                user_id,
                focused_object.id,
            )
            if order is None:
                return [KnowledgeChunk(
                    content=f"没有找到订单 {focused_object.id}。"
                )]
            detail = await get_order_detail(
                user_id,
                order.get("orderId"),
            )
        except Exception as exc:
            return [_error_chunk("订单信息", exc)]

        return [_json_chunk("订单信息", detail)]


class PaymentAPIProvider(KnowledgeProvider):
    """订单支付记录"""

    provider_id = "api.payment"

    async def retrieve(
        self,
        state: DialogueState,
        user_message: UserMessage,
    ) -> list[KnowledgeChunk]:
        focused_object = _focused_object(state, "order")
        if focused_object is None:
            return []

        user_id = resolve_user_id(state)
        try:
            order = await find_order_by_no(
                user_id,
                focused_object.id,
            )
            if order is None:
                return [KnowledgeChunk(
                    content=f"没有找到订单 {focused_object.id}。"
                )]
            data = await api_get(
                f"/orders/{order.get('orderId')}/payments",
                user_id=user_id,
            )
        except Exception as exc:
            return [_error_chunk("支付信息", exc)]

        return [_json_chunk("支付信息", data)]


class UserAPIProvider(KnowledgeProvider):
    """用户资料、常用出行人与会员账户"""

    provider_id = "api.user"

    async def retrieve(
        self,
        state: DialogueState,
        user_message: UserMessage,
    ) -> list[KnowledgeChunk]:
        user_id = resolve_user_id(state)
        chunks: list[KnowledgeChunk] = []

        try:
            profile = await api_get("/me", user_id=user_id)
            chunks.append(_json_chunk("用户信息", profile))
        except Exception as exc:
            chunks.append(_error_chunk("用户信息", exc))

        try:
            travelers = await api_get(
                "/me/travelers",
                user_id=user_id,
                params={"pageNo": 1, "pageSize": 10},
            )
            chunks.append(_json_chunk(
                "常用出行人",
                travelers.get("list") or [],
            ))
        except Exception as exc:
            chunks.append(_error_chunk("常用出行人", exc))

        try:
            member = await api_get(
                "/me/member-account",
                user_id=user_id,
            )
            chunks.append(_json_chunk("会员信息", member))
        except Exception as exc:
            chunks.append(_error_chunk("会员信息", exc))

        return chunks


class RefundAPIProvider(KnowledgeProvider):
    """当前用户的退款申请列表"""

    provider_id = "api.refund"

    async def retrieve(
        self,
        state: DialogueState,
        user_message: UserMessage,
    ) -> list[KnowledgeChunk]:
        try:
            data = await api_get(
                "/refund-requests",
                user_id=resolve_user_id(state),
                params={"pageNo": 1, "pageSize": 10},
            )
        except Exception as exc:
            return [_error_chunk("退款信息", exc)]

        return [_json_chunk("退款信息", data)]


class FAQProvider(KnowledgeProvider):
    """标准问答库：由大模型从 FAQ 列表中挑选相关条目。"""

    provider_id = "faq.default"

    def __init__(self) -> None:
        self.entries = load_faq_entries()
        self.selector = FAQSelector(self.entries)

    async def retrieve(
        self,
        state: DialogueState,
        user_message: UserMessage,
    ) -> list[KnowledgeChunk]:
        text = (user_message.text or "").strip()
        if not text or not self.entries:
            return []

        # 最近三轮对话用于理解"那退款呢"这类指代
        session = state.shared_state.current_session()
        history = (
            HistoryBuilder.build(session.turns[-3:])
            if session and session.turns
            else ""
        )

        try:
            entries = await self.selector.select(text, history)
        except Exception:
            logger.exception("FAQ 选择失败")
            return []

        return [
            KnowledgeChunk(
                content=(
                    f"【{entry.category_label}】"
                    f"{entry.question}\n{entry.answer}"
                )
            )
            for entry in entries
        ]


class RAGProvider(KnowledgeProvider):
    """文档知识库（当前为基础实现）"""

    provider_id = "rag.default"

    async def retrieve(
        self,
        state: DialogueState,
        user_message: UserMessage,
    ) -> list[KnowledgeChunk]:
        return [
            KnowledgeChunk(content="未检索到相关信息")
        ]


def build_default_providers() -> list[KnowledgeProvider]:
    """返回默认可用的全部知识 Provider。"""
    return [
        HotelAPIProvider(),
        ScenicAPIProvider(),
        FlightAPIProvider(),
        TrainAPIProvider(),
        BusAPIProvider(),
        TransferAPIProvider(),
        OrderAPIProvider(),
        PaymentAPIProvider(),
        UserAPIProvider(),
        RefundAPIProvider(),
        FAQProvider(),
        RAGProvider(),
    ]