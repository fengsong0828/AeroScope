"""
AeroScope 专利采集器
基于 Google Patents API 采集 + LLM 结构化 + Supabase 入库
"""
import time
import requests

from collector_core import CollectorCore
from llm_prompts import PATENT_PROMPT

PATENT_SEARCH_KEYWORDS = [
    "eVTOL", "urban air mobility", "drone delivery", "flying car",
    "倾转旋翼", "复合翼", "多旋翼无人机", "低空飞行器"
]


class PatentCollector(CollectorCore):
    """专利采集器"""

    def search_google_patents(self, keyword: str, limit: int = 10) -> int:
        """从 Google Patents 搜索并入库"""
        count = 0
        try:
            url = f"https://patents.google.com/?q={keyword}&language=ZH&num={limit}"
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
            # Google Patents 页面是 JS 渲染的，这里用简化方式获取
            # 实际生产环境建议用 Google Patents Public API
            text = resp.text[:8000]
            if not text:
                return 0

            llm_raw = self.call_llm(PATENT_PROMPT, f"搜索关键词: {keyword}\n页面内容: {text}")
            data = self.parse_llm_json(llm_raw)
            if data:
                if self.upsert("patents", data, "patent_number"):
                    count += 1
        except Exception as e:
            self.log_collection(f"Google Patents ({keyword})", "FAIL", str(e)[:80])
        return count

    def collect_all_keywords(self) -> int:
        total = 0
        for kw in PATENT_SEARCH_KEYWORDS:
            total += self.search_google_patents(kw, limit=5)
            time.sleep(3)

        # 采集后自动运行关联引擎
        if total > 0:
            print(f"\n  Auto-linking {total} new patents to companies...")
            try:
                from linker_patent_company import run_linker
                run_linker()
            except Exception as e:
                print(f"  Linker failed: {e}")

        return total

    def batch_import(self, patent_list: list) -> int:
        """批量导入已有专利数据（JSON 列表）"""
        count = 0
        for item in patent_list:
            if self.upsert("patents", item, "patent_number"):
                count += 1
        return count


if __name__ == "__main__":
    collector = PatentCollector()
    count = collector.collect_all_keywords()
    print(f"本次采集入库: {count} 条专利")
