from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FlowStepType(Enum):
    """Step 类型"""

    START = "start"
    ACTION = "action"
    RESPONSE = "response"
    COLLECT = "collect"
    END = "end"


class ResponseMode(Enum):
    """回复模式"""

    STATIC = "static"
    REPHRASE = "rephrase"


@dataclass
class FlowStepLink:
    """Step 之间的连接线，target 为下一个 Step ID"""

    target: str


@dataclass
class StaticLink(FlowStepLink):
    """直接跳转"""


@dataclass
class ConditionalLink(FlowStepLink):
    """条件成立时跳转"""

    condition: str


@dataclass
class FallbackLink(FlowStepLink):
    """条件都不成立时的 else 跳转"""


@dataclass
class FlowSlot:
    """Flow 可以使用的一个业务字段"""

    name: str
    type: str = "any"
    label: str = ""
    description: str = ""
    # 用户点选业务对象时，按对象类型把指定字段补进该槽位
    object_type: str | None = None
    object_field: str | None = None


@dataclass
class ResponseTemplate:
    """collect / response Step 使用的回复模板"""

    mode: ResponseMode = ResponseMode.STATIC
    text: str | None = None
    prompt: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "ResponseTemplate":
        # mode 缺省为 static
        return cls(
            mode=ResponseMode(
                data.get("mode", ResponseMode.STATIC)
            ),
            text=data.get("text"),
            prompt=data.get("prompt"),
        )


@dataclass
class SlotValidation:
    """Slot 校验条件与失败回复"""

    condition: str
    failure_template: ResponseTemplate


@dataclass
class FlowStep:
    """Flow 中的一个执行节点"""

    id: str
    type: FlowStepType
    next: list[FlowStepLink] = field(default_factory=list)

    @classmethod
    def from_dict(cls, step_data: dict[str, Any]) -> "FlowStep":
        # 按 type 找到具体 Step 类再解析
        step_type = step_data["type"]
        step_class = STEP_TYPE_TO_CLASS[step_type]
        return step_class.from_dict(step_data)

    @staticmethod
    def base_fields(
        step_data: dict[str, Any],
    ) -> dict[str, Any]:
        # 解析所有 Step 的公共字段
        return {
            "id": step_data["id"],
            "type": FlowStepType(step_data["type"]),
            "next": FlowStep.build_links(
                step_data.get("next", [])
            ),
        }

    @staticmethod
    def build_links(
        next_data: str | list,
    ) -> list[FlowStepLink]:
        # 空连线
        if not next_data:
            return []

        # 字符串：直接跳转
        if isinstance(next_data, str):
            return [StaticLink(target=next_data)]

        # 列表：条件跳转 / else 跳转
        links: list[FlowStepLink] = []
        for link_data in next_data:
            if "if" in link_data:
                links.append(ConditionalLink(
                    target=link_data["then"],
                    condition=link_data["if"],
                ))
            else:
                links.append(
                    FallbackLink(target=link_data["else"])
                )
        return links


@dataclass
class StartFlowStep(FlowStep):
    """Flow 入口，只负责进入下一个 Step"""

    @classmethod
    def from_dict(
        cls,
        step_data: dict[str, Any],
    ) -> "StartFlowStep":
        return cls(**FlowStep.base_fields(step_data))


@dataclass
class ActionFlowStep(FlowStep):
    """调用业务 Action"""

    action: str = ""

    @classmethod
    def from_dict(
        cls,
        step_data: dict[str, Any],
    ) -> "ActionFlowStep":
        return cls(
            **FlowStep.base_fields(step_data),
            action=step_data["action"],
        )


@dataclass
class ResponseFlowStep(FlowStep):
    """生成客服回复"""

    template: ResponseTemplate = field(
        default_factory=ResponseTemplate
    )

    @classmethod
    def from_dict(
        cls,
        step_data: dict[str, Any],
    ) -> "ResponseFlowStep":
        return cls(
            **FlowStep.base_fields(step_data),
            template=ResponseTemplate.from_dict(
                step_data.get("template", {})
            ),
        )


@dataclass
class CollectSlotStep(FlowStep):
    """收集并校验一个 Slot"""

    slot_name: str = ""
    template: ResponseTemplate = field(
        default_factory=ResponseTemplate
    )
    validation: SlotValidation | None = None

    @classmethod
    def from_dict(
        cls,
        step_data: dict[str, Any],
    ) -> "CollectSlotStep":
        # validation 为可选配置
        validation = None
        if "validation" in step_data:
            validation_data = step_data["validation"]
            validation = SlotValidation(
                condition=validation_data["condition"],
                failure_template=ResponseTemplate.from_dict(
                    validation_data["failure_template"]
                ),
            )

        return cls(
            **FlowStep.base_fields(step_data),
            slot_name=step_data["slot_name"],
            template=ResponseTemplate.from_dict(
                step_data.get("template", {})
            ),
            validation=validation,
        )


@dataclass
class EndFlowStep(FlowStep):
    """Flow 执行完成"""

    @classmethod
    def from_dict(
        cls,
        step_data: dict[str, Any],
    ) -> "EndFlowStep":
        return cls(**FlowStep.base_fields(step_data))


@dataclass
class Flow:
    """一项完整任务"""

    id: str
    description: str = ""
    steps: list[FlowStep] = field(default_factory=list)
    slots: list[FlowSlot] = field(default_factory=list)
    name: str | None = None

    def get_start_step(self) -> FlowStep | None:
        # 找到入口 Step
        for step in self.steps:
            if step.type is FlowStepType.START:
                return step
        return None

    def get_step(self, step_id: str) -> FlowStep | None:
        # 按 ID 找到当前 Step
        for step in self.steps:
            if step.id == step_id:
                return step
        return None


@dataclass
class FlowCatalog:
    """集中保存加载完成的 Flow 和 Slot"""

    flows: dict[str, Flow] = field(default_factory=dict)
    slots: dict[str, FlowSlot] = field(default_factory=dict)

    def get_flow(self, flow_id: str) -> Flow | None:
        # Flow 不存在时返回 None，由调用方决定如何提示
        return self.flows.get(flow_id)


# Step 类型映射
STEP_TYPE_TO_CLASS = {
    "start": StartFlowStep,
    "collect": CollectSlotStep,
    "action": ActionFlowStep,
    "response": ResponseFlowStep,
    "end": EndFlowStep,
}