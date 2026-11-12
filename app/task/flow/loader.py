from pathlib import Path

import yaml

from app.domain.flow_catalog import (
    CollectSlotStep,
    Flow,
    FlowCatalog,
    FlowSlot,
    FlowStep,
)


class FlowLoader:
    """把 YAML 配置加载成 FlowCatalog。"""

    def load(self, path: Path) -> FlowCatalog:
        # 读取 YAML 并转为字典
        with open(path, "r", encoding="utf-8") as file:
            data = yaml.safe_load(file) or {}

        # 先加载 Slot，再加载 Flow
        slots = self._load_slots(data.get("slots", {}))
        flows = self._load_flows(
            data.get("flows", {}),
            slots,
        )
        return FlowCatalog(flows=flows, slots=slots)

    @staticmethod
    def _load_slots(
        slots_data: dict[str, dict],
    ) -> dict[str, FlowSlot]:
        # Slot 名称同时作为 FlowSlot.name 和字典键
        slots: dict[str, FlowSlot] = {}
        for slot_name, slot_data in slots_data.items():
            slots[slot_name] = FlowSlot(
                **slot_data,
                name=slot_name,
            )
        return slots

    def _load_flows(
        self,
        flows_data: dict[str, dict],
        slots: dict[str, FlowSlot],
    ) -> dict[str, Flow]:
        # flow_id -> Flow
        flows: dict[str, Flow] = {}
        for flow_id, flow_data in flows_data.items():
            flows[flow_id] = self._load_flow(
                flow_id,
                flow_data,
                slots,
            )
        return flows

    def _load_flow(
        self,
        flow_id: str,
        flow_data: dict,
        slots: dict[str, FlowSlot],
    ) -> Flow:
        # 逐条解析 Step
        steps = [
            FlowStep.from_dict(step_data)
            for step_data in flow_data["steps"]
        ]
        # Flow 使用的 Slot 来自 collect Step
        flow_slots = [
            slots[step.slot_name]
            for step in steps
            if isinstance(step, CollectSlotStep)
        ]
        return Flow(
            id=flow_id,
            name=flow_data.get("name"),
            description=flow_data.get("description", ""),
            steps=steps,
            slots=flow_slots,
        )

    def load_many(self, paths: list[Path]) -> FlowCatalog:
        # 多个文件分别加载后合并
        flows: dict[str, Flow] = {}
        slots: dict[str, FlowSlot] = {}

        for path in paths:
            catalog = self.load(path)
            flows.update(catalog.flows)
            slots.update(catalog.slots)

        return FlowCatalog(flows=flows, slots=slots)