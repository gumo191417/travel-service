import importlib
import inspect
import pkgutil

from app.domain.action import Action
from app.task.action.registry import ActionRegistry
from app.task.action.runner import ActionRunner

# 这些模块不包含业务动作，扫描时跳过
_EXCLUDED_MODULES = {
    "support",
    "registry",
    "runner",
    "builder",
}


def register_custom_actions(registry: ActionRegistry) -> None:
    """递归扫描 app.task.action 包（含子包），注册全部 Action 子类。"""
    package = importlib.import_module("app.task.action")

    for module_info in pkgutil.walk_packages(
        package.__path__,
        prefix=f"{package.__name__}.",
    ):
        # 子包本身不注册，walk_packages 会继续遍历其内部模块
        if module_info.ispkg:
            continue

        short_name = module_info.name.rsplit(".", 1)[-1]
        if short_name in _EXCLUDED_MODULES:
            continue

        module = importlib.import_module(module_info.name)
        for _, action_class in inspect.getmembers(
            module,
            inspect.isclass,
        ):
            # 只保留直接继承 Action 的实现，排除抽象父类
            if (
                action_class is Action
                or not issubclass(action_class, Action)
            ):
                continue
            # 只保留当前模块里定义的类，排除 import 进来的类
            if action_class.__module__ != module.__name__:
                continue
            if not getattr(action_class, "name", ""):
                continue

            registry.register(action_class())


def build_action_runner() -> ActionRunner:
    """创建注册表并自动注册全部业务动作。"""
    registry = ActionRegistry()
    register_custom_actions(registry)
    return ActionRunner(registry)