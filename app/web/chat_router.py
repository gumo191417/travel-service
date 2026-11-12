import uuid

from fastapi import APIRouter, Depends

from app.domain.messages import (
    BotMessage,
    MessageObject,
    MessageType,
    ProcessResult,
    UserMessage,
)
from app.domain.task import TaskInstance
from app.service.dialogue_service import DialogueService
from app.web.dependencies import get_dialogue_service
from app.web.schemas import (
    ChatBotMessage,
    ChatObject,
    ChatRequest,
    ChatResponse,
    ChatStateResponse,
    FocusedObjectView,
    HistoryMessage,
    HistoryResponse,
    SessionRequest,
    SessionResponse,
    TaskStateView,
)

chat_router = APIRouter()


@chat_router.post("/api/chat")
async def chat(
    chat_request: ChatRequest,
    dialogue_service: DialogueService = Depends(
        get_dialogue_service
    ),
) -> ChatResponse:
    # 1. 接口模型 -> 领域消息
    user_message = _build_user_message(chat_request)

    # 2. 交给 Service 处理
    process_result = await dialogue_service.process_message(
        user_message,
        user_id=chat_request.user_id,
    )

    # 3. 处理结果 -> 接口响应
    return _build_chat_response(process_result)


@chat_router.get("/api/chat/history")
async def history(
    sender_id: str,
    dialogue_service: DialogueService = Depends(
        get_dialogue_service
    ),
) -> HistoryResponse:
    # 1. 只读取状态，不重新保存
    state = await dialogue_service.get_state(sender_id)

    # 2. 按 Session / Turn 顺序展开成一维消息列表
    messages: list[HistoryMessage] = []
    for session in state.shared_state.sessions:
        for turn in session.turns:
            # 每轮先追加用户消息
            messages.append(
                HistoryMessage(
                    role="user",
                    text=turn.user_message.text,
                    object=_build_chat_object(
                        turn.user_message.object
                    ),
                )
            )
            # 再追加该轮全部客服消息
            messages.extend(
                [
                    HistoryMessage(
                        role=message.role or "bot",
                        text=message.text,
                        object=_build_chat_object(
                            message.object
                        ),
                    )
                    for message in turn.bot_messages
                ]
            )

    return HistoryResponse(
        sender_id=sender_id,
        messages=messages,
        human_mode=state.shared_state.human_mode,
    )


@chat_router.post("/api/chat/sessions")
async def create_session(
    session_request: SessionRequest,
    dialogue_service: DialogueService = Depends(
        get_dialogue_service
    ),
) -> SessionResponse:
    # 关闭旧会话、清理运行态并开启新会话
    session = await dialogue_service.start_new_session(
        session_request.sender_id,
        user_id=session_request.user_id,
    )

    return SessionResponse(
        sender_id=session_request.sender_id,
        session_id=session.session_id,
        started_at=session.started_at,
    )


@chat_router.get("/api/chat/state")
async def get_chat_state(
    sender_id: str,
    dialogue_service: DialogueService = Depends(
        get_dialogue_service
    ),
) -> ChatStateResponse:
    # 1. 只读取状态
    state = await dialogue_service.get_state(sender_id)

    # 2. 当前会话信息
    session = state.shared_state.current_session()

    # 3. 任务与聚焦对象
    active_task = _build_task_view(
        state.task_state.active_task
    )
    paused_tasks = [
        _build_task_view(task)
        for task in state.task_state.paused
    ]
    focused_object = _build_focused_object_view(
        state.shared_state.focused_object
    )

    return ChatStateResponse(
        sender_id=sender_id,
        session_id=session.session_id if session else None,
        started_at=session.started_at if session else None,
        active_task=active_task,
        paused_tasks=[
            task for task in paused_tasks if task is not None
        ],
        focused_object=focused_object,
        slots=active_task.slots if active_task else {},
        human_mode=state.shared_state.human_mode,
        handoff_no=state.shared_state.handoff_no,
    )


def _build_user_message(
    chat_request: ChatRequest,
) -> UserMessage:
    # 客户端未提供 message_id 时由服务端生成
    return UserMessage(
        sender_id=chat_request.sender_id,
        message_id=(
            chat_request.message_id
            or str(uuid.uuid4())
        ),
        # text 与 object 只会存在一个
        type=(
            MessageType.TEXT
            if chat_request.text is not None
            else MessageType.OBJECT
        ),
        text=chat_request.text,
        object=(
            MessageObject(
                type=chat_request.object.type,
                id=chat_request.object.id,
                title=chat_request.object.title,
                # 复制字典，避免接口模型与领域模型共享可变对象
                attributes=dict(
                    chat_request.object.attributes
                ),
            )
            if chat_request.object is not None
            else None
        ),
    )


def _build_chat_response(
    process_result: ProcessResult,
) -> ChatResponse:
    # 领域消息列表 -> 接口响应消息列表
    return ChatResponse(
        sender_id=process_result.sender_id,
        message_id=process_result.message_id,
        messages=[
            ChatBotMessage(
                text=message.text,
                object=_build_chat_object(message.object),
            )
            for message in process_result.messages
        ],
        human_mode=process_result.human_mode,
    )


def _build_chat_object(
    message_object: MessageObject | None,
) -> ChatObject | None:
    # 消息处理接口与历史接口共用
    if message_object is None:
        return None

    return ChatObject(
        type=message_object.type,
        id=message_object.id,
        title=message_object.title,
        attributes=dict(message_object.attributes),
    )


def _build_task_view(
    task: TaskInstance | None,
) -> TaskStateView | None:
    if task is None:
        return None

    return TaskStateView(
        task_id=task.task_id,
        flow_id=task.flow_id,
        step_id=task.step_id,
        slots=dict(task.slots),
    )


def _build_focused_object_view(
    focused_object,
) -> FocusedObjectView | None:
    if focused_object is None:
        return None

    return FocusedObjectView(
        type=focused_object.type,
        id=focused_object.id,
        title=focused_object.title,
        attributes=dict(focused_object.attributes),
    )