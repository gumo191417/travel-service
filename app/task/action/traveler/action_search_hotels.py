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


class SearchHotelsAction(Action):
    """按城市、入住日期和筛选条件搜索酒店。"""

    name = "action_search_hotels"

    async def run(self, state: DialogueState) -> ActionResult:
        slots = state.task_state.active_task.slots

        city = slots.get("city")
        check_in_date = slots.get("check_in_date")
        check_out_date = slots.get("check_out_date")

        # 1. 城市名 -> areaId
        area_id = resolve_area_id(city)
        if area_id is None:
            return ActionResult(
                slot_updates=search_failure(
                    f"暂时不支持“{city or '这个城市'}”，"
                    "你可以换个城市试试。"
                )
            )

        # 2. 酒店搜索必须带入住、离店日期
        if not check_in_date or not check_out_date:
            return ActionResult(slot_updates={
                "city_area_id": area_id,
                **search_failure("请先告诉我入住和离店日期。"),
            })

        # 3. 调用酒店列表接口
        try:
            payload = await api_get(
                "/hotels",
                params={
                    "areaId": area_id,
                    "checkInDate": check_in_date,
                    "checkOutDate": check_out_date,
                    "starRatingCodes": as_list(slots.get("star_rating")),
                    "hotelTypeCodes": as_list(slots.get("hotel_type")),
                    "keyword": slots.get("keyword"),
                    "pageNo": 1,
                    "pageSize": SEARCH_PAGE_SIZE,
                },
            )
        except Exception as exc:
            return ActionResult(slot_updates={
                "city_area_id": area_id,
                **search_failure(
                    f"酒店查询失败：{http_error_text(exc)}"
                ),
            })

        # 4. 无结果
        items = payload.get("list") or []
        if not items:
            return ActionResult(slot_updates={
                "city_area_id": area_id,
                **search_failure(
                    "没有找到符合条件的酒店，"
                    "可以换个日期或放宽筛选条件。"
                ),
            })

        # 5. 归一化结果并生成摘要
        results = [self._normalize(item) for item in items]
        summary = build_search_summary(
            "酒店",
            results,
            payload.get("total"),
        )
        return ActionResult(slot_updates={
            "city_area_id": area_id,
            **search_success(results, summary),
        })

    @staticmethod
    def _normalize(item: dict) -> dict:
        star = item.get("starRatingCode") or "-"
        subtitle = (
            f"{star}星 · "
            f"{money(item.get('minSalePriceAmount'))}起"
        )
        count = item.get("availableRoomCount")
        if count is not None:
            subtitle += f" · 余{count}间"

        return {
            "type": "hotel",
            "id": str(item.get("hotelId")),
            "title": item.get("hotelName") or "酒店",
            "subtitle": subtitle,
            "attributes": item,
        }