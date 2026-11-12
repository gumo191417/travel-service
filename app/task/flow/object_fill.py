"""聚焦对象补槽的共用逻辑。

FlowExecutor 在推进 collect 步骤时、DialogueEngine 在收到对象消息时，
都用这里的规则判断"这个对象能不能补进当前槽位"。
"""

from __future__ import annotations

from typing import Any

from app.domain.flow_catalog import CollectSlotStep, Flow
from app.domain.state import FocusedObject


def read_object_field(
    focused_object: FocusedObject,
    field_name: str,
) -> Any:
    """读取对象字段，支持 id / title 以及 attributes.xxx 扩展字段。"""
    if field_name.startswith("attributes."):
        key = field_name.split(".", 1)[1]
        return focused_object.attributes.get(key)
    return getattr(focused_object, field_name, None)


def match_object_slot(
    flow: Flow,
    step: CollectSlotStep,
    focused_object: FocusedObject | None,
) -> tuple[str, Any] | None:
    """
    判断聚焦对象能否补进当前 collect 步骤的槽位。

    只有 FlowSlot 声明了 object_type / object_field，且对象类型、
    取值都有效时才返回 (slot_name, value)。
    """
    if focused_object is None:
        return None

    slot = next(
        (
            item
            for item in flow.slots
            if item.name == step.slot_name
        ),
        None,
    )
    if (
        slot is None
        or not slot.object_type
        or not slot.object_field
    ):
        return None

    if focused_object.type != slot.object_type:
        return None

    value = read_object_field(
        focused_object,
        slot.object_field,
    )
    if value in (None, ""):
        return None

    return step.slot_name, value