"""
AeroScope 政策采集器
从政府网站采集低空经济相关政策，LLM 结构化后入库
"""
import requests
from bs4 import BeautifulSoup

from collector_core import CollectorCore
from llm_prompts import POLICY_PROMPT

POLICY_SOURCES = [
    {
        "name": "民航局",
        "url": "https://www.caac.gov.cn/INDEX/",
        "parser": "caac"
    }
]

POLICY_KEYWORDS = ["低空", "无人机", "eVTOL", "通用航空", "空中交通", "适航", "飞行汽车"]


class PolicyCollector(CollectorCore):
    """政策法规采集器"""

    def collect_all(self) -> int:
        count = 0
        for src in POLICY_SOURCES:
            try:
                resp = requests.get(src["url"], headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
                soup = BeautifulSoup(resp.text, "html.parser")
                links = soup.find_all("a", href=True)
                for link in links[:30]:
                    title = link.get_text(strip=True)
                    if not any(kw in title for kw in POLICY_KEYWORDS):
                        continue
                    href = link["href"]
                    if not href.startswith("http"):
                        continue
                    if self._is_duplicate_url(href):
                        continue

                    text = f"标题: {title}\n来源: {src['name']}\n链接: {href}"
                    llm_raw = self.call_llm(POLICY_PROMPT, text)
                    data = self.parse_llm_json(llm_raw)
                    if data:
                        data["source_url"] = href
                        data.setdefault("department", src["name"])
                        if self.upsert("policies", data, "title"):
                            count += 1
            except Exception as e:
                self.log_collection(src["name"], "FAIL", str(e)[:80])
        return count

    def _is_duplicate_url(self, url: str) -> bool:
        if not url or not self.db:
            return False
        try:
            r = self.db.table("policies").select("id").ilike("title", f"%{url[:40]}%").execute()
            return len(r.data) > 0
        except Exception:
            return False


if __name__ == "__main__":
    collector = PolicyCollector()
    count = collector.collect_all()
    print(f"本次采集入库: {count} 条政策")
