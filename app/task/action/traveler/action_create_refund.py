from app.clients.travel_api import (
    api_post,
    http_error_text,
    resolve_user_id,
)
from app.domain.action import Action, ActionResult
from app.domain.state import DialogueState
from app.task.action.support import money

# 退款申请状态编码 -> 中文
REFUND_STATUS_LABELS = {
    "pending": "待处理",
    "approved": "已通过",
    "rejected": "已拒绝",
    "success": "已退款",
}


class CreateRefundAction(Action):
    """对订单明细提交退款申请。"""

    name = "action_create_refund"

    async def run(self, state: DialogueState) -> ActionResult:
        slots = state.task_state.active_task.slots

        order_id = slots.get("order_id")
        order_no = str(slots.get("order_no") or "").strip()
        items = slots.get("order_items") or []

        # 1. 必须已经通过 action_lookup_order 定位到订单
        if not order_id:
            return self._fail(
                "还没有定位到订单，请先提供订单号。"
            )
        if not items:
            return self._fail("这个订单没有可以退款的明细。")

        # 2. 单明细直接退；多明细按用户描述匹配
        item, error = self._pick_item(
            items,
            slots.get("refund_item_hint"),
        )
        if item is None:
            return self._fail(error)

        # 3. 退款金额缺省取明细售价
        amount = slots.get("refund_amount")
        if amount in (None, ""):
            amount = item.get("saleAmount")

        try:
            requested_amount = float(amount)
        except (TypeError, ValueError):
            return self._fail(
                "退款金额不正确，请重新确认后再说一次。"
            )

        reason = str(
            slots.get("refund_reason") or "用户申请退款"
        ).strip()

        # 4. 提交退款申请
        try:
            payload = await api_post(
                (
                    f"/orders/{order_id}/items/"
                    f"{item.get('orderItemId')}/refund-requests"
                ),
                user_id=resolve_user_id(state),
                json={
                    "requestedAmount": requested_amount,
                    "reason": reason,
                },
            )
        except Exception as exc:
            return self._fail(
                f"退款申请没有提交成功：{http_error_text(exc)}"
            )

        # 5. 写回退款结果
        status = payload.get("statusCode") or "pending"
        status_label = REFUND_STATUS_LABELS.get(status, status)
        item_name = item.get("productName") or "该产品"

        return ActionResult(slot_updates={
            "refund_success": True,
            "order_item_id": item.get("orderItemId"),
            "order_item_name": item_name,
            "refund_amount": requested_amount,
            "refund_no": payload.get("refundRequestNo"),
            "refund_status": status_label,
            "refund_result": (
                f"已为订单 {order_no} 中的「{item_name}」提交退款申请，"
                f"退款金额 {money(requested_amount)}，"
                f"申请单号 {payload.get('refundRequestNo')}，"
                f"当前状态：{status_label}。"
            ),
        })

    @staticmethod
    def _pick_item(
        items: list[dict],
        hint: str | None,
    ) -> tuple[dict | None, str]:
        """按用户描述挑选订单明细，匹配失败时返回提示语。"""
        if len(items) == 1:
            return items[0], ""

        names = "、".join(
            str(item.get("productName") or "未命名产品")
            for item in items
        )

        text = str(hint or "").strip()
        if not text:
            return (
                None,
                f"这个订单包含多个产品：{names}。"
                "请告诉我要退哪一个。",
            )

        target = text.casefold()
        matched = [
            item
            for item in items
            if target in str(item.get("productName") or "").casefold()
        ]

        if len(matched) == 1:
            return matched[0], ""

        if not matched:
            return (
                None,
                f"没有找到与「{text}」匹配的产品，"
                f"订单中包含：{names}。",
            )

        matched_names = "、".join(
            str(item.get("productName") or "未命名产品")
            for item in matched
        )
        return (
            None,
            f"「{text}」匹配到多个产品：{matched_names}，"
            "请说得更具体一些。",
        )

    @staticmethod
    def _fail(message: str) -> ActionResult:
        return ActionResult(slot_updates={
            "refund_success": False,
            "refund_result": message,
        })