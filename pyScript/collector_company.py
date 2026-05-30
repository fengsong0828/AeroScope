"""
AeroScope 企业采集器
从公开数据源采集低空经济企业信息，LLM 结构化后入库
"""
import time
import requests
from bs4 import BeautifulSoup

from collector_core import CollectorCore
from llm_prompts import COMPANY_PROMPT

COMPANY_SEARCH_QUERIES = [
    "eVTOL 飞行器 制造商 公司 融资",
    "无人机 物流配送 企业 生产基地",
    "低空经济 飞行汽车 适航取证 公司",
    "城市空中交通 UAM 整机厂商",
    "倾转旋翼 复合翼 电动垂直起降 企业",
]

NAME_BLACKLIST = [
    "无", "未知", "未命名", "匿名", "暂无", "N/A", "n/a", "none", "null", "",
    "公司名", "企业名", "名字", "名称"
]


class CompanyCollector(CollectorCore):
    """企业信息采集器"""

    def collect_from_search(self, query: str) -> int:
        """搜索结果中提取企业信息"""
        count = 0
        try:
            search_url = f"https://www.bing.com/search?q={requests.utils.quote(query)}"
            resp = requests.get(search_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
            soup = BeautifulSoup(resp.text, "html.parser")
            text = soup.get_text(separator="\n", strip=True)[:5000]

            llm_raw = self.call_llm(COMPANY_PROMPT, f"搜索词: {query}\n搜索结果: {text}")
            data = self.parse_llm_json(llm_raw)
            if data:
                # LLM 判断非低空经济企业，跳过
                if data.get("skip"):
                    self.log_collection(query, "SKIP", "非低空经济企业")
                    return 0
                name = data.get("name", "").strip()
                if not name or name in NAME_BLACKLIST or len(name) < 2:
                    self.log_collection(query, "SKIP", f"无效企业名: {name}")
                    return 0
                if self.upsert("companies", data, "name"):
                    count += 1
        except Exception as e:
            self.log_collection(query, "FAIL", str(e)[:80])
        return count

    def collect_all(self) -> int:
        total = 0
        for q in COMPANY_SEARCH_QUERIES:
            total += self.collect_from_search(q)
            time.sleep(3)
        return total


if __name__ == "__main__":
    collector = CompanyCollector()
    count = collector.collect_all()
    print(f"本次采集入库: {count} 家企业")
