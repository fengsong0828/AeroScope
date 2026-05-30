"""
AeroScope RAG Chat Handler
搜索 Supabase 数据库 + DeepSeek 生成回答
"""
import os
import json
import requests
from collector_core import CollectorCore


CHAT_SYSTEM_PROMPT = """你是 AeroBot，低空经济领域的智能情报助手。

你的知识来源是 AeroScope Insight 平台的数据库，包括：
- 低空经济新闻资讯 (news)
- 各级政府政策法规 (policies)
- 企业信息与融资数据 (companies, funding_events)
- 技术专利 (patents)
- eVTOL/无人机产品 (products)

回答规则：
1. 基于下方提供的【数据库检索结果】回答，不要编造信息
2. 如果数据库中没有相关信息，诚实告知"目前数据库暂无相关信息"
3. 回答要简洁专业，分点列出关键信息
4. 在回答末尾标注信息来源

格式：Markdown，重点加粗"""


class ChatHandler:
    def __init__(self):
        self.core = CollectorCore()
        self.db = self.core.db

    def handle(self, question: str) -> dict:
        contexts = self._search_all(question)
        reply, sources = self._generate(question, contexts)
        return {"reply": reply, "sources": sources}

    def _search_all(self, question: str) -> dict:
        results = {}
        keywords = self._extract_keywords(question)

        for kw in keywords[:3]:
            self._search_table("companies", "name", kw, results, limit=2)
            self._search_table("companies", "description", kw, results, limit=2)
            self._search_table("news", "title", kw, results, limit=2)
            self._search_table("news", "summary", kw, results, limit=2)
            self._search_table("policies", "title", kw, results, limit=2)
            self._search_table("policies", "summary", kw, results, limit=2)
            self._search_table("patents", "title", kw, results, limit=2)
            self._search_table("patents", "abstract", kw, results, limit=2)
            self._search_table("products", "name", kw, results, limit=2)
            self._search_table("products", "manufacturer", kw, results, limit=2)
            self._search_table("funding_events", "company_name", kw, results, limit=2)
            self._search_table("funding_events", "title", kw, results, limit=2)

        return results

    def _search_table(self, table: str, column: str, keyword: str, results: dict, limit: int = 2):
        if not self.db:
            return
        try:
            r = self.db.table(table).select("*").ilike(column, f"%{keyword}%").limit(limit).execute()
            if r.data:
                key = f"{table}:{column}"
                if key not in results:
                    results[key] = []
                for row in r.data:
                    cleaned = {k: v for k, v in row.items() if v and k not in ("id", "created_at", "draft")}
                    results[key].append(cleaned)
        except Exception:
            pass

    def _extract_keywords(self, question: str) -> list:
        important = [
            "eVTOL", "无人机", "飞行汽车", "低空经济", "适航", "融资", "专利",
            "政策", "城市空中交通", "倾转旋翼", "复合翼", "多旋翼",
            "亿航", "峰飞", "小鹏", "沃飞", "时的", "御风", "零重力",
            "电池", "电机", "飞控", "航电", "碳纤维",
            "民航局", "发改委", "深圳", "广州", "合肥", "成都", "北京", "上海",
            "适航取证", "型号合格证", "TC", "PC", "AC",
            "物流配送", "载人交通", "应急救援", "农业植保",
        ]
        found = [kw for kw in important if kw.lower() in question.lower()]
        if not found:
            found = [question[:20]]
        return found

    def _generate(self, question: str, contexts: dict) -> tuple:
        ctx_text = self._format_context(contexts)
        if not ctx_text.strip():
            return (
                "目前数据库中暂无相关信息。我正在持续学习低空经济领域的知识，建议您先浏览平台的「资讯快报」和「企业数据库」板块获取最新信息。",
                []
            )

        body = {
            "model": self.core.llm_model,
            "messages": [
                {"role": "system", "content": CHAT_SYSTEM_PROMPT},
                {"role": "user", "content": f"【数据库检索结果】\n{ctx_text}\n\n【用户问题】\n{question}"}
            ],
            "temperature": 0.3,
            "max_tokens": 1500
        }
        headers = {
            "Authorization": f"Bearer {self.core.llm_api_key}",
            "Content-Type": "application/json"
        }
        try:
            resp = requests.post(
                f"{self.core.llm_base_url}/chat/completions",
                headers=headers, json=body, timeout=60
            )
            resp.raise_for_status()
            reply = resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            reply = f"AI 服务暂时不可用，请稍后重试。（错误：{str(e)[:100]}）"

        sources = self._extract_sources(contexts)
        return reply, sources

    def _format_context(self, contexts: dict) -> str:
        parts = []
        total_chars = 0
        max_chars = 4000

        for key, items in contexts.items():
            table, col = key.split(":", 1)
            for item in items[:3]:
                lines = [f"【{table}】"]
                for k, v in item.items():
                    if isinstance(v, str) and len(v) > 300:
                        v = v[:300] + "..."
                    lines.append(f"  {k}: {v}")
                block = "\n".join(lines)
                if total_chars + len(block) < max_chars:
                    parts.append(block)
                    total_chars += len(block)

        return "\n\n".join(parts)

    def _extract_sources(self, contexts: dict) -> list:
        sources = []
        seen = set()
        for key, items in contexts.items():
            table = key.split(":", 1)[0]
            for item in items[:2]:
                title = item.get("title") or item.get("name") or item.get("company_name") or item.get("applicant") or ""
                if title and title not in seen:
                    seen.add(title)
                    sources.append({"table": table, "title": str(title)[:80]})
        return sources[:5]
