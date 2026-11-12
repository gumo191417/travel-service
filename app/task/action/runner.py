import logging

from app.domain.action import ActionResult
from app.domain.state import DialogueState
from app.task.action.registry import ActionRegistry

logger = logging.getLogger(__name__)


class ActionRunner:
    """按名称执行 Action，隔离单个动作的异常。"""

    def __init__(self, registry: ActionRegistry) -> None:
        self.registry = registry

    async def run(
        self,
        action_name: str,
        state: DialogueState,
    ) -> ActionResult:
        try:
            action = self.registry.get(action_name)
            return await action.run(state)
        except Exception:
            # 单个动作失败不中断整轮对话，交给后续步骤渲染兜底文案
            logger.exception("Action 执行失败: %s", action_name)
            return ActionResult()