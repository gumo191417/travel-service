from app.clients.travel_api import (
    find_order_by_no,
    get_order_detail,
    http_error_text,
    resolve_user_id,
)
from app.domain.action import Action, ActionResult
from app.domain.state import DialogueState
from app.task.action.support import money, short_time

# 订单状态编码 -> 中文
STATUS_LABELS = {
    "pending_payment": "待支付",
    "cancelled": "已取消",
    "paid": "已支付",
    "ticketed": "已出票",
    "in_progress": "进行中",
    "finished": "已完成",
}

# 订单类型编码 -> 中文
TYPE_LABELS = {
    "hotel_room": "酒店订单",
    "scenic_ticket": "景点门票订单",
    "flight_cabin": "机票订单",
    "train_seat": "火车票订单",
    "bus_seat": "汽车票订单",
    "transfer_service": "接送服务订单",
}


class LookupOrderAction(Action):
    """按订单号定位订单，写回状态、摘要和行程信息。"""

    name = "action_lookup_order"

    async def run(self, state: DialogueState) -> ActionResult:
        slots = state.task_state.active_task.slots
        order_no = str(slots.get("order_no") or "").strip()

        if not order_no:
            return self._fail("请提供要查询的订单号。")

        user_id = resolve_user_id(state)

        # 1. 当前用户订单列表里按订单号匹配
        try:
            order = await find_order_by_no(user_id, order_no)
        except Exception as exc:
            return self._fail(
                f"订单查询失败：{http_error_text(exc)}"
            )

        if order is None:
            return self._fail(
                f"没有找到订单 {order_no}，"
                "请核对订单号后重试。"
            )

        # 2. 用订单 ID 查详情
        order_id = order.get("orderId")
        try:
            detail = await get_order_detail(user_id, order_id)
        except Exception as exc:
            return self._fail(
                f"订单详情查询失败：{http_error_text(exc)}"
            )

        items = detail.get("items") or []
        return ActionResult(slot_updates={
            "order_found": True,
            "order_id": order_id,
            "order_status": self._status_label(detail),
            "order_summary": self._summary(order_no, detail),
            "order_items": items,
            "order_item_count": len(items),
            "travel_summary": self._travel_summary(items),
        })

    @staticmethod
    def _status_label(detail: dict) -> str:
        status = detail.get("statusCode")
        return STATUS_LABELS.get(status, status or "未知")

    def _summary(self, order_no: str, detail: dict) -> str:
        type_label = TYPE_LABELS.get(
            detail.get("orderTypeCode"),
            detail.get("orderTypeCode") or "订单",
        )
        parts = [
            f"订单 {order_no} 是{type_label}，"
            f"当前状态：{self._status_label(detail)}"
        ]

        if detail.get("payableAmount") is not None:
            parts.append(
                f"应付金额 {money(detail.get('payableAmount'))}"
            )
        if detail.get("paidAmount") is not None:
            parts.append(
                f"实付金额 {money(detail.get('paidAmount'))}"
            )
        if detail.get("createdAt"):
            parts.append(
                f"下单时间 {short_time(detail.get('createdAt'))}"
            )

        return "，".join(parts) + "。"

    @staticmethod
    def _travel_summary(items: list[dict]) -> str:
        if not items:
            return "该订单没有行程明细。"

        lines: list[str] = []
        for item in items:
            name = item.get("productName") or "出行产品"
            start = item.get("travelTime")
            end = item.get("travelEndTime")

            if not start:
                lines.append(f"{name}：出行时间待确认")
                continue

            start_text = short_time(start)
            end_text = short_time(end)
            if end_text and end_text != "-" and end_text != start_text:
                lines.append(f"{name}：{start_text} 至 {end_text}")
            else:
                lines.append(f"{name}：{start_text}")

        return "\n".join(lines)

    @staticmethod
    def _fail(message: str) -> ActionResult:
        return ActionResult(slot_updates={
            "order_found": False,
            "order_summary": message,
        })