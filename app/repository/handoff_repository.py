import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.handoff_request import HandoffRequest


def generate_handoff_no() -> str:
    """生成转人工单号，形如 HO20251110153012A1B2。"""
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"HO{stamp}{uuid.uuid4().hex[:4].upper()}"


class HandoffRepository:
    """转人工请求的读写。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        sender_id: str,
        user_id: int | None,
        session_id: str | None,
        reason: str | None,
    ) -> HandoffRequest:
        request = HandoffRequest(
            handoff_no=generate_handoff_no(),
            sender_id=sender_id,
            user_id=user_id,
            session_id=session_id,
            reason=reason,
            status="pending",
        )
        self.session.add(request)
        await self.session.commit()
        await self.session.refresh(request)
        return request

    async def get(
        self,
        handoff_no: str,
    ) -> HandoffRequest | None:
        result = await self.session.execute(
            select(HandoffRequest).where(
                HandoffRequest.handoff_no == handoff_no
            )
        )
        return result.scalar_one_or_none()

    async def list_requests(
        self,
        *,
        status: str | None = None,
        limit: int = 50,
    ) -> list[HandoffRequest]:
        statement = select(HandoffRequest)
        if status:
            statement = statement.where(
                HandoffRequest.status == status
            )
        statement = statement.order_by(
            HandoffRequest.created_at.desc(),
            HandoffRequest.id.desc(),
        ).limit(limit)

        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def takeover(
        self,
        handoff_no: str,
        agent_name: str,
    ) -> HandoffRequest | None:
        request = await self.get(handoff_no)
        if request is None or request.status == "closed":
            return None

        request.status = "taken"
        request.agent_name = agent_name
        request.taken_at = datetime.now()
        await self.session.commit()
        return request

    def mark_taken_if_pending(
        self,
        request: HandoffRequest,
        agent_name: str,
    ) -> None:
        # 回复时如果还没接单，自动登记接单信息
        if request.status == "pending":
            request.status = "taken"
            request.agent_name = agent_name
            request.taken_at = datetime.now()

    def mark_closed(self, request: HandoffRequest) -> None:
        if request.status != "closed":
            request.status = "closed"
            request.closed_at = datetime.now()