"""travel-data 接口的统一调用入口。

业务动作（task/action）和知识检索（knowledge/providers）都从这里取数据，
避免两边各拼一套 URL、请求头和错误处理。
"""

from __future__ import annotations

from typing import Any

import httpx

from app.clients import http_client
from app.conf.config import settings
from app.domain.state import DialogueState

# travel-data 的统一接口前缀
API_PREFIX = "/api/v1"

# 订单列表分页参数
ORDER_PAGE_SIZE = 100
ORDER_MAX_PAGES = 10


def api_url(path: str) -> str:
    """拼接完整的 travel-data 接口地址。"""
    return f"{settings.travel_api_base_url.rstrip('/')}{API_PREFIX}{path}"


def resolve_user_id(state: DialogueState) -> int:
    """取当前对话的业务用户 ID，缺省回退到演示用户。"""
    return state.user_id or settings.demo_user_id


def ensure_client() -> httpx.AsyncClient:
    """复用全局 HTTP 客户端；未初始化时按需创建。"""
    if http_client.http_client is None:
        http_client.init_http_client()
    return http_client.http_client


def _headers(user_id: int | None) -> dict[str, str]:
    # 公开浏览接口不传用户身份
    return {"X-User-Id": str(user_id)} if user_id is not None else {}


def _clean_params(
    params: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not params:
        return None
    return {
        key: value
        for key, value in params.items()
        if value not in (None, "", [], {})
    }


async def api_get(
    path: str,
    *,
    user_id: int | None = None,
    params: dict[str, Any] | None = None,
) -> Any:
    """GET travel-data 接口，返回原始 JSON。"""
    response = await ensure_client().get(
        api_url(path),
        params=_clean_params(params),
        headers=_headers(user_id),
    )
    response.raise_for_status()
    return response.json()


async def api_post(
    path: str,
    *,
    user_id: int | None = None,
    json: dict[str, Any] | None = None,
) -> Any:
    """POST travel-data 接口，返回原始 JSON。"""
    response = await ensure_client().post(
        api_url(path),
        json=json,
        headers=_headers(user_id),
    )
    response.raise_for_status()
    return response.json()


async def find_order_by_no(
    user_id: int,
    order_no: str,
) -> dict | None:
    """在用户订单列表中按订单号匹配订单，找不到返回 None。"""
    target = str(order_no or "").strip().upper()
    if not target:
        return None

    page_no = 1
    while page_no <= ORDER_MAX_PAGES:
        payload = await api_get(
            "/orders",
            user_id=user_id,
            params={
                "pageNo": page_no,
                "pageSize": ORDER_PAGE_SIZE,
            },
        )
        items = payload.get("list") or []

        for item in items:
            current = str(item.get("orderNo") or "").strip()
            if current.upper() == target:
                return item

        total = payload.get("total") or 0
        if not items or page_no * ORDER_PAGE_SIZE >= total:
            break
        page_no += 1

    return None


async def get_order_detail(
    user_id: int,
    order_id: Any,
) -> dict:
    """按数字订单 ID 查询订单详情。"""
    return await api_get(
        f"/orders/{order_id}",
        user_id=user_id,
    )


def http_error_text(exc: Exception) -> str:
    """把接口异常转换成可以直接放进回复的短句。"""
    if isinstance(exc, httpx.HTTPStatusError):
        detail = ""
        try:
            payload = exc.response.json()
            if isinstance(payload, dict):
                detail = str(
                    payload.get("detail")
                    or payload.get("message")
                    or ""
                ).strip()
        except Exception:
            detail = (exc.response.text or "").strip()[:120]

        if detail:
            return detail
        return f"业务服务返回 {exc.response.status_code}"

    if isinstance(exc, httpx.TimeoutException):
        return "业务服务响应超时"
    if isinstance(exc, httpx.HTTPError):
        return "业务服务暂时不可用"
    return "处理请求时发生异常"