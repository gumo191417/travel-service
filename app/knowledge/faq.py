"""FAQ 数据与选择逻辑。

FAQ 内容放在 faq_data/travel_faq.yml，由运营维护。
匹配方式：把问题列表交给大模型，让它在列表里挑选相关条目。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate

from app.clients.llm import llm
from app.prompts.prompt_loader import load_prompt

# FAQ 数据文件
FAQ_DATA_FILE = (
    Path(__file__).parent / "faq_data" / "travel_faq.yml"
)

# 一次最多返回几条 FAQ
MAX_SELECTED_FAQS = 3

# 分类编码 -> 中文
CATEGORY_LABELS = {
    "refund_policy": "退款政策",
    "change_policy": "改期改签",
    "booking_rule": "预订规则",
    "travel_notice": "出行须知",
    "general_travel": "通用问题",
}


@dataclass
class FAQEntry:
    """一条 FAQ 问答"""

    id: str
    category: str
    question: str
    answer: str
    keywords: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "FAQEntry":
        return cls(
            id=str(data.get("id") or "").strip(),
            category=str(data.get("category") or "").strip(),
            question=str(data.get("question") or "").strip(),
            answer=str(data.get("answer") or "").strip(),
            keywords=[
                str(item).strip()
                for item in (data.get("keywords") or [])
                if str(item).strip()
            ],
        )

    @property
    def category_label(self) -> str:
        return CATEGORY_LABELS.get(
            self.category,
            self.category or "常见问题",
        )


def load_faq_entries(
    path: Path = FAQ_DATA_FILE,
) -> list[FAQEntry]:
    """读取 FAQ YAML，跳过字段不完整的条目。"""
    if not path.exists():
        return []

    data = yaml.safe_load(
        path.read_text(encoding="utf-8")
    ) or []
    if not isinstance(data, list):
        return []

    entries: list[FAQEntry] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        entry = FAQEntry.from_dict(item)
        if entry.id and entry.question and entry.answer:
            entries.append(entry)
    return entries


class FAQSelector:
    """让大模型从 FAQ 列表中选出与用户问题相关的条目。"""

    def __init__(self, entries: list[FAQEntry]) -> None:
        self.entries = entries
        self._by_id = {
            entry.id: entry for entry in entries
        }

    async def select(
        self,
        user_message: str,
        history: str = "",
    ) -> list[FAQEntry]:
        if not self.entries:
            return []

        variables = {
            "user_message": user_message,
            "history": history,
            "faq_list_json": json.dumps(
                [
                    {
                        "id": entry.id,
                        "category": entry.category,
                        "question": entry.question,
                        "keywords": entry.keywords,
                    }
                    for entry in self.entries
                ],
                ensure_ascii=False,
                indent=2,
            ),
        }

        result = await self._call_llm(
            load_prompt("faq_select"),
            variables,
        )
        return self._to_entries(result)

    async def _call_llm(
        self,
        prompt_text: str,
        variables: dict,
    ) -> dict:
        """单独抽出来，便于测试时替换大模型。"""
        prompt = PromptTemplate.from_template(
            prompt_text,
            template_format="jinja2",
        )
        chain = prompt | llm | JsonOutputParser()
        return await chain.ainvoke(variables)

    def _to_entries(self, result) -> list[FAQEntry]:
        """把模型返回的 ID 列表转换成 FAQ 条目。"""
        if not isinstance(result, dict):
            return []

        raw_ids = result.get("faq_ids")
        if not isinstance(raw_ids, list):
            return []

        selected: list[FAQEntry] = []
        seen: set[str] = set()
        for item in raw_ids:
            faq_id = str(item).strip()
            if not faq_id or faq_id in seen:
                continue
            entry = self._by_id.get(faq_id)
            if entry is None:
                continue
            seen.add(faq_id)
            selected.append(entry)
            if len(selected) >= MAX_SELECTED_FAQS:
                break

        return selected