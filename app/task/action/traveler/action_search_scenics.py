from app.conf.areas import resolve_area_id
from app.domain.action import Action, ActionResult
from app.domain.state import DialogueState
from app.clients.travel_api import api_get, http_error_text
from app.task.action.support import (
    SEARCH_PAGE_SIZE,
    as_list,
    build_search_summary,
    money,
    search_failure,
    search_success,
)


class SearchScenicsAction(Action):
    """按城市、游玩日期和筛选条件搜索景点。"""

    name = "action_search_scenics"

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

        # 2. 景点搜索必须带游玩日期
        if not travel_date:
            return ActionResult(slot_updates={
                "city_area_id": area_id,
                **search_failure("请先告诉我计划哪一天去玩。"),
            })

        # 3. 调用景点列表接口
        try:
            payload = await api_get(
                "/scenic-spots",
                params={
                    "areaId": area_id,
                    "travelDate": travel_date,
                    "scenicTypeCodes": as_list(slots.get("scenic_type")),
                    "ratingCodes": as_list(slots.get("scenic_rating")),
                    "keyword": slots.get("keyword"),
                    "pageNo": 1,
                    "pageSize": SEARCH_PAGE_SIZE,
                },
            )
        except Exception as exc:
            return ActionResult(slot_updates={
                "city_area_id": area_id,
                **search_failure(
                    f"景点查询失败：{http_error_text(exc)}"
                ),
            })

        # 4. 无结果
        items = payload.get("list") or []
        if not items:
            return ActionResult(slot_updates={
                "city_area_id": area_id,
                **search_failure(
                    "没有找到符合条件的景点，"
                    "可以换个日期或放宽筛选条件。"
                ),
            })

        # 5. 归一化结果并生成摘要
        results = [self._normalize(item) for item in items]
        summary = build_search_summary(
            "景点",
            results,
            payload.get("total"),
        )
        return ActionResult(slot_updates={
            "city_area_id": area_id,
            **search_success(results, summary),
        })

    @staticmethod
    def _normalize(item: dict) -> dict:
        rating = item.get("ratingCode") or "-"
        subtitle = (
            f"{rating} · "
            f"{money(item.get('minSalePriceAmount'))}起"
        )
        count = item.get("availableTicketCount")
        if count is not None:
            subtitle += f" · 余{count}张"

        return {
            "type": "scenic",
            "id": str(item.get("scenicSpotId")),
            "title": item.get("scenicName") or "景点",
            "subtitle": subtitle,
            "attributes": item,
        }