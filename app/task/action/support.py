"""Action 层的展示格式化工具。

接口调用统一走 app.clients.travel_api，这里只负责把数据整理成
槽位可以消费的文本和结构。
"""

from __future__ import annotations

from typing import Any

# 搜索类动作一次取多少条用于摘要展示
SEARCH_PAGE_SIZE = 5


def as_list(value: Any) -> list[str] | None:
    """把单值或逗号分隔的多选值转成列表，供多选查询参数使用。"""
    if value is None:
        return None
    if isinstance(value, (list, tuple, set)):
        items = [str(item).strip() for item in value]
        return [item for item in items if item] or None

    text = str(value).strip()
    if not text:
        return None
    normalized = text.replace("，", ",")
    items = [part.strip() for part in normalized.split(",")]
    return [item for item in items if item] or None


def money(value: Any) -> str:
    """金额展示，保留整数时不带小数。"""
    if value is None:
        return "-"
    try:
        return f"¥{float(value):g}"
    except (TypeError, ValueError):
        return f"¥{value}"


def clock(value: Any) -> str:
    """从 YYYY-MM-DD HH:mm:ss 中取 HH:mm。"""
    text = str(value or "")
    return text[11:16] if len(text) >= 16 else text


def short_time(value: Any) -> str:
    """行程时间展示：整点日期只保留 YYYY-MM-DD。"""
    text = str(value or "")
    if not text:
        return "-"
    if text.endswith(" 00:00:00") or text.endswith("T00:00:00"):
        return text[:10]
    return text[:16]


def build_search_summary(
    label: str,
    results: list[dict[str, Any]],
    total: int | None = None,
) -> str:
    """把归一化后的搜索结果整理成多行文本。"""
    count = total if total is not None else len(results)
    lines = [f"为你找到 {count} 个{label}："]
    for index, result in enumerate(results, start=1):
        lines.append(
            f"{index}. {result['title']}（{result['subtitle']}）"
        )
    if total is not None and total > len(results):
        lines.append("……还有更多结果，可以继续缩小条件。")
    return "\n".join(lines)


def search_success(
    results: list[dict[str, Any]],
    summary: str,
) -> dict[str, Any]:
    """搜索成功时统一写回的槽位。"""
    return {
        "search_found": True,
        "search_results": results,
        "search_result_summary": summary,
    }


def search_failure(summary: str) -> dict[str, Any]:
    """搜索失败或没有结果时统一写回的槽位。"""
    return {
        "search_found": False,
        "search_results": [],
        "search_result_summary": summary,
    }