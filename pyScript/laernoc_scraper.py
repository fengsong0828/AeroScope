"""
laernoc.com 全量采集 — 同步 Playwright 版
采集政策/企业/航空器/新闻，LLM结构化后导入AeroScope
"""
import os, sys, re, json, time
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv; load_dotenv()
from collector_core import CollectorCore
from playwright.sync_api import sync_playwright
from urllib.parse import urljoin

BASE = 'https://www.laernoc.com'
CATS = {
    'policy':   {'path': '/flfg',    'label': '政策法规', 'table': 'policies',  'level': '国家级'},
    'company':  {'path': '/dkzzy',   'label': '企业库',   'table': 'companies', 'level': None},
    'aircraft': {'path': '/eVTOL',   'label': '航空器',   'table': 'products',  'level': None},
    'news':     {'path': '/gsxw',    'label': '公司新闻', 'table': 'news',      'level': None},
}

EXTRACT_PROMPT = """你是低空经济数据提取专家。从以下网页文本提取JSON。
规则：
- 政策类: {"type":"policy","title":"...","department":"...","publish_date":"YYYY-MM-DD","content":"...","summary":"..."}
- 企业类: {"type":"company","name":"...","description":"...","location":"...","website":"..."}
- 航空器类: {"type":"aircraft","name":"...","manufacturer":"...","model_type":"eVTOL/无人机/直升机","specs":"..."}
- 新闻类: {"type":"news","title":"...","publish_date":"YYYY-MM-DD","summary":"...","content":"..."}
只输出JSON。"""


class LaernocScraper(CollectorCore):

    def __init__(self, dry_run=False, cat=None):
        super().__init__()
        self.dry_run = dry_run
        self.cat = cat
        self.stats = {'found': 0, 'saved': 0, 'skip': 0}

    def run(self):
        targets = {self.cat: CATS[self.cat]} if self.cat else CATS

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={'width': 1920, 'height': 1080})

            for key, info in targets.items():
                print(f"\n{'='*50}\n  {info['label']}\n{'='*50}")
                url = f"{BASE}{info['path']}"
                try:
                    page.goto(url, timeout=20000, wait_until='load')
                    page.wait_for_timeout(4000)
                except Exception as e:
                    print(f"  Page error: {e}")
                    continue

                # 提取所有可点击标题链接
                items = page.evaluate('''() => {
                    const r = []; const seen = new Set();
                    document.querySelectorAll('a[href]').forEach(a => {
                        const h = a.getAttribute('href');
                        const t = a.innerText.trim();
                        if (!h || h === "#" || h === "/" || seen.has(h)) return;
                        if (t.length < 6) return;
                        if (["首页","查看更多","友情链接","联系我们","关于我们","留言","登录","注册","提交","免责声明"].includes(t)) return;
                        seen.add(h);
                        r.push({title: t.substring(0,120), link: h});
                    });
                    return r;
                }''')

                print(f"  Found {len(items)} links")
                for i, item in enumerate(items):
                    title = item.get('title', '')
                    link = item.get('link', '')
                    print(f"  [{i+1}/{len(items)}] {title[:50]}")

                    # 提取详情
                    text = title
                    if link.startswith('/'):
                        try:
                            page.goto(urljoin(BASE, link), timeout=15000, wait_until='load')
                            page.wait_for_timeout(2000)
                            body = page.evaluate('document.body.innerText')
                            text = body[:5000] if body else title
                        except:
                            pass

                    # LLM提取
                    llm_raw = self.call_llm(EXTRACT_PROMPT, text)
                    data = self.parse_llm_json(llm_raw)
                    if not data:
                        print(f"    -> LLM fail")
                        continue

                    data['source_url'] = urljoin(BASE, link) if link.startswith('/') else link
                    self._save(key, info, data)
                    self.stats['found'] += 1
                    time.sleep(0.8)

                page.goto(url, timeout=15000, wait_until='load')
                page.wait_for_timeout(1000)

            browser.close()

        print(f"\nDone: found={self.stats['found']} saved={self.stats['saved']} skip={self.stats['skip']}")

    def _save(self, key, info, data):
        tbl = info['table']
        if key == 'policy':
            payload = {
                'title': data.get('title',''), 'department': data.get('department',''),
                'publish_date': data.get('publish_date'), 'content': data.get('content',''),
                'summary': data.get('summary',''), 'level': info['level'],
                'source_url': data.get('source_url',''), 'draft': False,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            unique_key = 'title'
        elif key == 'company':
            payload = {
                'name': data.get('name',''), 'description': data.get('description',''),
                'location': data.get('location',''), 'website_url': data.get('website',''),
                'draft': False
            }
            unique_key = 'name'
        else:
            return

        if self.dry_run:
            self.stats['saved'] += 1
            return

        exist = self.db.table(tbl).select('id').eq(unique_key, payload[unique_key]).execute()
        if exist.data:
            self.stats['skip'] += 1
            return

        try:
            self.db_write.table(tbl).insert(payload).execute()
            self.stats['saved'] += 1
            print(f"    -> saved")
        except Exception as e:
            print(f"    -> err: {e}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--cat', choices=['policy','company','aircraft','news'])
    a = ap.parse_args()
    LaernocScraper(dry_run=a.dry_run, cat=a.cat).run()
