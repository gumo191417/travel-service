from app.domain.action import Action


class ActionRegistry:
    """按名称保存已注册的 Action 实例。"""

    def __init__(self) -> None:
        self._actions: dict[str, Action] = {}

    def register(self, action: Action) -> None:
        # 同名的后注册者覆盖先注册者，便于本地调试时替换实现
        if not getattr(action, "name", ""):
            raise ValueError(
                f"{type(action).__name__} 缺少 name 属性"
            )
        self._actions[action.name] = action

    def get(self, name: str) -> Action:
        action = self._actions.get(name)
        if action is None:
            raise KeyError(f"Action 未注册: {name}")
        return action

    def names(self) -> list[str]:
        # 便于启动日志与排查
        return sorted(self._actions)