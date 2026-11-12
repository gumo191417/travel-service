from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients import database
from app.engine.builder import build_dialogue_engine
from app.engine.dialogue_engine import DialogueEngine
from app.repository.dialogue_state_repository import (
    DialogueStateRepository,
)
from app.service.dialogue_service import DialogueService

# 应用级共享引擎，启动时创建一次
_dialogue_engine: DialogueEngine | None = None


def init_dialogue_engine() -> None:
    # 启动时构建引擎（加载 Flow、注册 Action）
    global _dialogue_engine
    _dialogue_engine = build_dialogue_engine()


def get_engine() -> DialogueEngine:
    # 所有请求共享同一个引擎
    if _dialogue_engine is None:
        raise RuntimeError("对话引擎尚未初始化")
    return _dialogue_engine


async def get_db():
    # 每个请求使用独立的数据库 Session
    async with database.session_factory() as session:
        yield session


async def get_repository(
    db: AsyncSession = Depends(get_db),
) -> DialogueStateRepository:
    # 用当前请求的 Session 创建 Repository
    return DialogueStateRepository(db)


async def get_dialogue_service(
    engine: DialogueEngine = Depends(get_engine),
    repository: DialogueStateRepository = Depends(
        get_repository
    ),
) -> DialogueService:
    # 共享引擎 + 当前请求 Repository 组装 Service
    return DialogueService(
        dialogue_state_repository=repository,
        dialogue_engine=engine,
    )