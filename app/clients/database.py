from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.conf.config import settings

# 全局异步数据库引擎实例
engine: AsyncEngine | None = None
# 全局异步会话工厂
session_factory: async_sessionmaker[AsyncSession] | None = None


def init_db_engine():
    """
    初始化数据库异步引擎和会话工厂（同步函数，启动时调用）
    """
    global engine, session_factory
    # 创建异步数据库引擎
    engine = create_async_engine(settings.database_url)
    # 提交后不让 ORM 对象过期，异步项目常用配置
    session_factory = async_sessionmaker(
        engine,
        expire_on_commit=False,
    )


async def close_db_engine():
    """
    关闭、释放数据库连接资源（异步函数，优雅关闭时调用）
    """
    global engine, session_factory
    # 释放底层连接池
    if engine is not None:
        await engine.dispose()
    # 置空全局变量，标记已关闭
    engine = None
    session_factory = None