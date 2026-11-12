from app.conf.areas import resolve_area_id
from app.domain.action import Action, ActionResult
from app.domain.state import DialogueState
from app.clients.travel_api import api_get, http_error_text
from app.task.action.support import (
    SEARCH_PAGE_SIZE,
    build_search_summary,
    clock,
    money,
    search_failure,
    search_success,
)


class SearchBusesAction(Action):
    """按出发/到达城市和日期搜索汽车票。"""

    name = "action_search_buses"

    async def run(self, state: DialogueState) -> ActionResult:
        slots = state.task_state.active_task.slots

        departure_city = slots.get("departure_city")
        arrival_city = slots.get("arrival_city")
        departure_date = slots.get("departure_date")

        # 1. 两个城市都要能识别
        departure_area_id = resolve_area_id(departure_city)
        arrival_area_id = resolve_area_id(arrival_city)

        if departure_area_id is None:
            return ActionResult(
                slot_updates=search_failure(
                    f"暂时不支持从“{departure_city or '这个城市'}”出发。"
                )
            )
        if arrival_area_id is None:
            return ActionResult(
                slot_updates=search_failure(
                    f"暂时不支持去往“{arrival_city or '这个城市'}”。"
                )
            )

        # 2. 汽车票搜索必须带出发日期
        if not departure_date:
            return ActionResult(slot_updates={
                "departure_area_id": departure_area_id,
                "arrival_area_id": arrival_area_id,
                **search_failure("请先告诉我出发日期。"),
            })

        # 3. 调用汽车票搜索接口
        try:
            payload = await api_get(
                "/buses/search",
                params={
                    "departureAreaId": departure_area_id,
                    "arrivalAreaId": arrival_area_id,
                    "departureDate": departure_date,
                    "routeName": slots.get("route_name"),
                    "pageNo": 1,
                    "pageSize": SEARCH_PAGE_SIZE,
                },
            )
        except Exception as exc:
            return ActionResult(slot_updates={
                "departure_area_id": departure_area_id,
                "arrival_area_id": arrival_area_id,
                **search_failure(
                    f"汽车票查询失败：{http_error_text(exc)}"
                ),
            })

        # 4. 无结果
        items = payload.get("list") or []
        if not items:
            return ActionResult(slot_updates={
                "departure_area_id": departure_area_id,
                "arrival_area_id": arrival_area_id,
                **search_failure(
                    "没有找到符合条件的班次，"
                    "可以换个日期再试试。"
                ),
            })

        # 5. 归一化结果并生成摘要
        results = [self._normalize(item) for item in items]
        summary = build_search_summary(
            "班次",
            results,
            payload.get("total"),
        )
        return ActionResult(slot_updates={
            "departure_area_id": departure_area_id,
            "arrival_area_id": arrival_area_id,
            **search_success(results, summary),
        })

    @staticmethod
    def _normalize(item: dict) -> dict:
        subtitle = (
            f"{item.get('departureHubName')}→{item.get('arrivalHubName')}"
            f" · {clock(item.get('departureTime'))}出发"
            f" · {money(item.get('salePriceAmount'))}起"
        )
        count = item.get("availableInventory")
        if count is not None:
            subtitle += f" · 余{count}座"

        return {
            "type": "bus",
            "id": str(item.get("departureId")),
            "title": item.get("routeName") or "班次",
            "subtitle": subtitle,
            "attributes": item,
        }