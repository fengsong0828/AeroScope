"""
AeroScope 融资事件采集器
从行业媒体采集低空经济领域融资事件，LLM 结构化后入库
"""
import time
import requests
from bs4 import BeautifulSoup

from collector_core import CollectorCore
from llm_prompts import FUNDING_PROMPT

FUNDING_SOURCES = [
    {"name": "36Kr", "url": "https://www.36kr.com/search/articles/低空经济"},
    {"name": "IT桔子", "url": "https://www.itjuzi.com/investevents"},
]

KEYWORDS = ["融资", "投资", "募资", "Pre-A", "A轮", "B轮", "C轮", "种子轮", "天使轮",
            "eVTOL", "无人机", "飞行汽车", "低空"]


class FundingCollector(CollectorCore):
    """融资事件采集器"""

    def collect_from_sources(self) -> int:
        count = 0
        for src in FUNDING_SOURCES:
            try:
                resp = requests.get(src["url"], headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
                soup = BeautifulSoup(resp.text, "html.parser")
                # 提取包含融资关键词的文本块
                articles = soup.find_all(["article", "div"], class_=True)
                for art in articles[:20]:
                    text = art.get_text(separator=" ", strip=True)
                    if not any(kw in text for kw in KEYWORDS):
                        continue
                    if len(text) < 100:
                        continue

                    llm_raw = self.call_llm(FUNDING_PROMPT, text[:4000])
                    data = self.parse_llm_json(llm_raw)
                    if data:
                        data.setdefault("status", "confirmed")
                        data.setdefault("data_source", src["name"])
                        if self.upsert("funding_events", data, "title"):
                            count += 1
                    time.sleep(0.5)
            except Exception as e:
                self.log_collection(src["name"], "FAIL", str(e)[:80])
        return count


if __name__ == "__main__":
    collector = FundingCollector()
    count = collector.collect_from_sources()
    print(f"本次采集入库: {count} 条融资事件")
