"""初始化对话状态表。

用法：
    python init_db.py

需要 .env 里的 DATABASE_URL 指向可用的 MySQL，并且数据库已存在。
"""

import asyncio

from app.clients import database
from app.models import dialogue_state_record  # noqa: F401
from app.models import handoff_request  # noqa: F401
from app.models.base import Base


async def init_models() -> None:
    database.init_db_engine()

    async with database.engine.begin() as connection:
        await connection.run_sync(
            Base.metadata.create_all
        )

    await database.close_db_engine()
    print("dialogue_states 表已就绪")


if __name__ == "__main__":
    asyncio.run(init_models())