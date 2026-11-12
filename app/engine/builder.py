from pathlib import Path

from app.clarify.responder import ClarifyResponder
from app.domain.flow_catalog import FlowCatalog
from app.engine.dialogue_engine import DialogueEngine
from app.handler.chitchat.handler import ChitchatHandler
from app.handler.chitchat.responder import ChitchatResponder
from app.knowledge.handler import KnowledgeHandler
from app.knowledge.intents import KNOWLEDGE_INTENTS
from app.knowledge.providers import build_default_providers
from app.knowledge.responder import KnowledgeResponder
from app.plan.turn_planner import TurnPlanner
from app.plan.validator import TurnPlanValidator
from app.task.action.builder import build_action_runner
from app.task.command.processor import CommandProcessor
from app.task.flow.executor import FlowExecutor
from app.task.flow.loader import FlowLoader
from app.task.lifecycle.responder import TaskLifecycleResponder
from app.task.response.renderer import ResponseRenderer
from app.task.task_handler import TaskHandler

# 项目根目录（app/engine/builder.py 向上两级）
_PACKAGE_ROOT = Path(__file__).parents[2]
# 任务流程配置文件
_FLOW_CONFIG_FILE = (
    _PACKAGE_ROOT / "flow_config" / "travel_flows.yml"
)


def build_dialogue_engine() -> DialogueEngine:
    # 1. 加载 Flow 配置
    flow_catalog: FlowCatalog = FlowLoader().load(
        _FLOW_CONFIG_FILE
    )

    # 2. 创建底层执行组件
    response_renderer = ResponseRenderer()
    action_runner = build_action_runner()

    # 3. 装配任务轨道
    task_handler = TaskHandler(
        command_processor=CommandProcessor(),
        flow_catalog=flow_catalog,
        flow_executor=FlowExecutor(
            action_runner=action_runner,
            response_renderer=response_renderer,
        ),
        lifecycle_responder=TaskLifecycleResponder(
            flow_catalog=flow_catalog,
        ),
    )

    # 4. 装配知识轨道
    knowledge_handler = KnowledgeHandler(
        knowledge_responder=KnowledgeResponder(),
        providers=build_default_providers(),
        knowledge_intents=KNOWLEDGE_INTENTS,
    )

    # 5. 组装对话引擎
    return DialogueEngine(
        turn_planner=TurnPlanner(),
        task_handler=task_handler,
        knowledge_handler=knowledge_handler,
        chitchat_handler=ChitchatHandler(
            chitchat_responder=ChitchatResponder(),
        ),
        clarify_responder=ClarifyResponder(),
        turn_plan_validator=TurnPlanValidator(),
    )