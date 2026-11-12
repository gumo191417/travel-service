from pydantic import TypeAdapter
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.state import DialogueState
from app.models.dialogue_state_record import DialogueStateRecord


# DialogueState 与 JSON 的双向转换
DIALOGUE_STATE_ADAPTER = TypeAdapter(DialogueState)

class DialogueStateRepository:
    def __init__(self, session: AsyncSession) -> None:
        # Session 由外部创建并传入
        self.session = session


    async def load_state(
        self,
        sender_id: str,
        for_update: bool = False,
    ) -> DialogueState:
        # 根据主键查询记录；人工回复场景用行锁避免覆盖
        record: DialogueStateRecord | None = await self.session.get(
            DialogueStateRecord,
            sender_id,
            with_for_update=for_update,
        )

        if record:
            # JSON 转回 DialogueState
            state_json = record.state_json
            state = DIALOGUE_STATE_ADAPTER.validate_json(state_json)
            return state

        # 新用户：使用默认值创建空状态
        return DialogueState(sender_id=sender_id)

    async def save_state(
        self,
        state: DialogueState,
    ) -> None:
        # DialogueState 转 JSON 字符串
        state_json = DIALOGUE_STATE_ADAPTER.dump_json(
            state
        ).decode("utf-8")

        # MySQL Upsert：不存在则插入，存在则更新
        statement = insert(DialogueStateRecord).values(
            sender_id=state.sender_id,
            state_json=state_json,
        )
        statement = statement.on_duplicate_key_update(
            state_json=statement.inserted.state_json
        )

        # 执行 SQL 并提交事务
        await self.session.execute(statement)
        await self.session.commit()