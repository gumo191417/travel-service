from app.conf.areas import resolve_area_id
from app.domain.action import Action, ActionResult
from app.domain.state import DialogueState
from app.clients.travel_api import api_get, http_error_text
from app.task.action.support import (
    SEARCH_PAGE_SIZE,
    as_list,
    build_search_summary,
    search_failure,
    search_success,
)


class SearchTransfersAction(Action):
    """按城市、服务日期和筛选条件搜索接送服务。"""

    name = "action_search_transfers"

    async def run(self, state: DialogueState) -> ActionResult:
        slots = state.task_state.active_task.slots

        city = slots.get("city")
        travel_date = slots.get("travel_date")

        # 1. 城市名 -> areaId
        area_id = resolve_area_id(city)
        if area_id is None:
            return ActionResult(
                slot_updates=search_failure(
                    f"暂时不支持“{city or '这个城市'}”，"
                    "你可以换个城市试试。"
                )
            )

        # 2. 接送服务必须带服务日期
        if not travel_date:
            return ActionResult(slot_updates={
                "city_area_id": area_id,
                **search_failure("请先告诉我用车日期。"),
            })

        # 3. 调用接送服务列表接口
        try:
            payload = await api_get(
                "/transfers",
                params={
                    "areaId": area_id,
                    "businessDate": travel_date,
                    "serviceTypeCodes": as_list(slots.get("service_type")),
                    "vehicleTypeCodes": as_list(slots.get("vehicle_type")),
                    "pageNo": 1,
                    "pageSize": SEARCH_PAGE_SIZE,
                },
            )
        except Exception as exc:
            return ActionResult(slot_updates={
                "city_area_id": area_id,
                **search_failure(
                    f"接送服务查询失败：{http_error_text(exc)}"
                ),
            })

        # 4. 无结果
        items = payload.get("list") or []
        if not items:
            return ActionResult(slot_updates={
                "city_area_id": area_id,
                **search_failure(
                    "没有找到符合条件的接送服务，"
                    "可以换个日期或车型再试试。"
                ),
            })

        # 5. 归一化结果并生成摘要
        results = [self._normalize(item) for item in items]
        summary = build_search_summary(
            "接送服务",
            results,
            payload.get("total"),
        )
        return ActionResult(slot_updates={
            "city_area_id": area_id,
            **search_success(results, summary),
        })

    @staticmethod
    def _normalize(item: dict) -> dict:
        subtitle = (
            f"{item.get('vehicleTypeCode') or '-'}"
            f" · 载客{item.get('passengerCapacity') or '-'}人"
        )
        count = item.get("availableInventory")
        if count is not None:
            subtitle += f" · 余{count}单"

        return {
            "type": "transfer",
            "id": str(item.get("serviceId")),
            "title": item.get("serviceName") or "接送服务",
            "subtitle": subtitle,
            "attributes": item,
        }