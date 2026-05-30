"""
AeroScope 新闻采集器
从行业媒体 RSS 和网页抓取低空经济相关新闻，经 LLM 结构化后入库
"""
import time
import feedparser
import requests
from bs4 import BeautifulSoup

from collector_core import CollectorCore
from llm_prompts import NEWS_PROMPT

RSS_SOURCES = [
    "https://www.36kr.com/feed",  # 36氪
]

NEWS_SEARCH_KEYWORDS = [
    "低空经济", "eVTOL", "无人机物流", "飞行汽车", "城市空中交通",
    "适航取证", "民用航空", "无人机配送", "空中出租车"
]


class NewsCollector(CollectorCore):
    """新闻采集器"""

    def collect_from_rss(self) -> int:
        """从 RSS 源采集"""
        count = 0
        for rss_url in RSS_SOURCES:
            try:
                feed = feedparser.parse(rss_url)
                for entry in feed.entries[:10]:
                    title = entry.get("title", "")
                    if not any(kw in title for kw in NEWS_SEARCH_KEYWORDS):
                        continue
                    summary = entry.get("summary", "")
                    published = entry.get("published", "")
                    link = entry.get("link", "")

                    if self._is_duplicate_url(link):
                        continue

                    text = f"标题: {title}\n来源: {rss_url}\n日期: {published}\n内容: {summary}"
                    llm_raw = self.call_llm(NEWS_PROMPT, text)
                    data = self.parse_llm_json(llm_raw)
                    if data:
                        data["source_url"] = link
                        data["source"] = data.get("source", "RSS")
                        if self.upsert("news", data, "source_url"):
                            count += 1
                    time.sleep(1)
            except Exception as e:
                self.log_collection(rss_url, "FAIL", str(e)[:80])
        return count

    def collect_from_webpage(self, url: str) -> bool:
        """从指定网页采集（管理员入口）"""
        try:
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer"]):
                tag.decompose()
            title = soup.title.string if soup.title else ""
            body = soup.get_text(separator="\n", strip=True)[:6000]

            if self._is_duplicate_url(url):
                return True

            text = f"URL: {url}\n标题: {title}\n正文: {body}"
            llm_raw = self.call_llm(NEWS_PROMPT, text)
            data = self.parse_llm_json(llm_raw)
            if data:
                data["source_url"] = url
                return self.upsert("news", data, "source_url")
        except Exception as e:
            self.log_collection(url, "FAIL", str(e)[:80])
        return False

    def _is_duplicate_url(self, url: str) -> bool:
        if not url or not self.db:
            return False
        try:
            r = self.db.table("news").select("id").eq("source_url", url).execute()
            return len(r.data) > 0
        except Exception:
            return False


if __name__ == "__main__":
    collector = NewsCollector()
    count = collector.collect_from_rss()
    print(f"本次采集入库: {count} 条新闻")
