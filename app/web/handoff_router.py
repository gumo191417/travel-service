from fastapi import APIRouter, Depends, HTTPException, Query

from app.clients.handoff import get_handoff_service
from app.service.handoff_service import (
    HandoffClosed,
    HandoffError,
    HandoffNotFound,
    HandoffService,
)
from app.web.schemas import (
    HandoffListResponse,
    HandoffReplyRequest,
    HandoffReplyResponse,
    HandoffRequestView,
    HandoffTakeoverRequest,
)

handoff_router = APIRouter(
    prefix="/api/handoff",
    tags=["handoff"],
)


@handoff_router.get(
    "/requests",
    response_model=HandoffListResponse,
)
async def list_requests(
    status: str | None = Query(default=None),
    handoff_service: HandoffService = Depends(
        get_handoff_service
    ),
) -> HandoffListResponse:
    requests = await handoff_service.list_requests(
        status=status
    )
    views = [_to_view(request) for request in requests]
    return HandoffListResponse(list=views, total=len(views))


@handoff_router.post(
    "/requests/{handoff_no}/takeover",
    response_model=HandoffRequestView,
)
async def takeover(
    handoff_no: str,
    payload: HandoffTakeoverRequest,
    handoff_service: HandoffService = Depends(
        get_handoff_service
    ),
) -> HandoffRequestView:
    try:
        request = await handoff_service.takeover(
            handoff_no,
            payload.agent_name,
        )
    except HandoffError as exc:
        _raise_http(exc)

    return _to_view(request)


@handoff_router.post(
    "/requests/{handoff_no}/reply",
    response_model=HandoffReplyResponse,
)
async def reply(
    handoff_no: str,
    payload: HandoffReplyRequest,
    handoff_service: HandoffService = Depends(
        get_handoff_service
    ),
) -> HandoffReplyResponse:
    try:
        await handoff_service.reply(
            handoff_no,
            payload.text,
            payload.agent_name,
        )
    except HandoffError as exc:
        _raise_http(exc)

    return HandoffReplyResponse(
        handoff_no=handoff_no,
        text=payload.text,
        role="agent",
    )


@handoff_router.post(
    "/requests/{handoff_no}/close",
    response_model=HandoffRequestView,
)
async def close(
    handoff_no: str,
    handoff_service: HandoffService = Depends(
        get_handoff_service
    ),
) -> HandoffRequestView:
    try:
        request = await handoff_service.close(handoff_no)
    except HandoffError as exc:
        _raise_http(exc)

    return _to_view(request)


def _to_view(request) -> HandoffRequestView:
    return HandoffRequestView(
        handoff_no=request.handoff_no,
        sender_id=request.sender_id,
        user_id=request.user_id,
        session_id=request.session_id,
        reason=request.reason,
        status=request.status,
        agent_name=request.agent_name,
        created_at=request.created_at,
        taken_at=request.taken_at,
        closed_at=request.closed_at,
    )


def _raise_http(exc: HandoffError) -> None:
    if isinstance(exc, HandoffNotFound):
        raise HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, HandoffClosed):
        raise HTTPException(status_code=409, detail=str(exc))
    raise HTTPException(status_code=400, detail=str(exc))