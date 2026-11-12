import logging

from app.clients.handoff import get_handoff_service
from app.domain.action import Action, ActionResult
from app.domain.state import DialogueState

logger = logging.getLogger(__name__)


class RequestHumanHandoffAction(Action):
    """创建转人工请求，并把会话切换到人工模式。"""

    name = "action_request_human_handoff"

    async def run(
        self,
        state: DialogueState,
    ) -> ActionResult:
        slots = state.task_state.active_task.slots
        reason = str(
            slots.get("handoff_reason")
            or "用户请求转人工客服"
        ).strip()

        session = state.shared_state.current_session()

        try:
            request = await get_handoff_service().create_request(
                sender_id=state.sender_id,
                user_id=state.user_id,
                session_id=(
                    session.session_id if session else None
                ),
                reason=reason,
            )
        except Exception:
            logger.exception("创建转人工请求失败")
            return ActionResult(slot_updates={
                "handoff_success": False,
                "handoff_message": (
                    "转接人工客服没有成功，请稍后再试。"
                ),
            })

        # 切换人工模式，后续消息不再由机器人回复
        state.shared_state.human_mode = True
        state.shared_state.handoff_no = request.handoff_no

        return ActionResult(slot_updates={
            "handoff_success": True,
            "handoff_no": request.handoff_no,
            "handoff_message": (
                f"好的，已为你转接人工客服，"
                f"工单号 {request.handoff_no}，"
                "客服会尽快回复，请稍候。"
            ),
        })