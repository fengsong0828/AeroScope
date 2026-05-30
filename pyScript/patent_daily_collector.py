"""
AeroScope 专利日常采集管道
每天自动：搜索新专利 → 采集详情 → LLM分类(v2.0) → 入库 + 关联企业

用法:
  python pyScript/patent_daily_collector.py           # 单次运行
  python pyScript/patent_daily_collector.py --dry-run # 预览不写入
  python pyScript/patent_daily_collector.py --max 20  # 限制数量
"""
import os, sys, time, json, argparse, re
from datetime import datetime, timedelta, timezone
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv; load_dotenv()
from collector_core import CollectorCore
from llm_prompts import PATENT_PROMPT
from patent_classification_rules import (
    TECH_CATEGORIES, INDUSTRY_CHAIN, APP_FIELDS,
    get_all_tech_categories, get_all_chain_positions, get_all_app_fields
)
import requests as http
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
}

# 低空经济搜索关键词
DAILY_KEYWORDS = [
    "eVTOL 专利", "无人机 专利", "垂直起降 专利", "飞行汽车 专利",
    "低空经济 专利", "城市空中交通 专利", "复合翼 专利", "倾转旋翼 专利"
]

# 备用池存储路径
BACKLOG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
                            "agent-workspace", "data-engineer", "data-schemas",
                            "patent_backlog.json")
DAILY_REPORT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
                            "agent-workspace", "data-engineer", "pipeline-logs",
                            "patent_daily_report.json")

VALID_MAIN_CATS = set(get_all_tech_categories())
VALID_SUB_CATS  = set()
for v in TECH_CATEGORIES.values():
    VALID_SUB_CATS.update(v["sub"])
VALID_CHAIN     = set(get_all_chain_positions())
VALID_APPS      = set(get_all_app_fields())


class PatentDailyCollector(CollectorCore):
    """每日专利采集 + 分类 + 入库管道"""

    def __init__(self, dry_run=False):
        super().__init__()
        self.dry_run = dry_run
        self.stats = {"searched": 0, "collected": 0, "classified": 0, "saved": 0, "skipped": 0}
        self.backlog = self._load_backlog()

    def _load_backlog(self):
        if os.path.exists(BACKLOG_FILE):
            with open(BACKLOG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f).get('backlog', [])
        return []

    def _save_backlog(self):
        os.makedirs(os.path.dirname(BACKLOG_FILE), exist_ok=True)
        with open(BACKLOG_FILE, 'w', encoding='utf-8') as f:
            json.dump({'backlog': self.backlog, 'count': len(self.backlog),
                       'updated': datetime.now().isoformat()}, f, ensure_ascii=False, indent=2)

    # ─── Step 1: 搜索最近公开的专利 ───
    def search_recent(self, days_back=7, max_per_kw=5):
        """通过 Google Patents 按日期搜索近期专利"""
        found = []
        before_date = datetime.now().strftime('%Y%m%d')
        after_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y%m%d')

        for kw in DAILY_KEYWORDS[:4]:  # 只搜前4个关键词避免过多请求
            try:
                url = f"https://patents.google.com/?q={kw}&before=priority:{before_date}&after=priority:{after_date}&num={max_per_kw}"
                resp = http.get(url, headers=HEADERS, timeout=20)
                if resp.status_code != 200:
                    continue
                # 提取页面中的专利号链接
                soup = BeautifulSoup(resp.text, 'html.parser')
                links = soup.find_all('a', href=re.compile(r'/patent/[A-Z]{2}\d+'))
                seen = set()
                for link in links:
                    href = link.get('href', '')
                    match = re.search(r'/patent/([A-Z]{2}\d+[A-Z]?\d*)', href)
                    if match:
                        pn = match.group(1)
                        if pn not in seen and len(pn) >= 8:
                            seen.add(pn)
                            found.append({'patent_number': pn, 'google_url': f'https://patents.google.com{href}',
                                          'title': link.get_text(strip=True)[:80]})
                time.sleep(2)
            except Exception as e:
                print(f"  search error ({kw}): {e}")
        self.stats["searched"] = len(found)
        return found

    # ─── Step 2: 抓取专利详情 ───
    def fetch_detail(self, patent_number, google_url):
        """从 Google Patents 页面提取专利详情"""
        try:
            resp = http.get(google_url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                return None
            soup = BeautifulSoup(resp.text, 'html.parser')
            # 尝试提取摘要
            abstract_tag = soup.find('div', class_='abstract') or soup.find('section', attrs={'itemprop': 'abstract'})
            abstract = abstract_tag.get_text(strip=True)[:500] if abstract_tag else ''
            # 提取标题
            title_tag = soup.find('h1') or soup.find('title')
            title = title_tag.get_text(strip=True).replace(' - Google Patents', '')[:100] if title_tag else ''
            # 提取申请人
            assignee_tag = soup.find('dd', itemprop='assignee') or soup.find('dd')
            applicant = assignee_tag.get_text(strip=True)[:200] if assignee_tag else ''
            return {
                'patent_number': patent_number,
                'google_url': google_url,
                'title': title,
                'abstract': abstract,
                'applicant': applicant
            }
        except:
            return None

    # ─── Step 3: LLM 分类 + 模板校验 ───
    def classify_patent(self, patent_info):
        """调用 LLM 提取结构化信息并按固定模板校验"""
        text = f"专利标题: {patent_info.get('title','')}\n摘要: {patent_info.get('abstract','')}\n申请人: {patent_info.get('applicant','')}"
        if len(text) < 20:
            return None
        llm_raw = self.call_llm(PATENT_PROMPT, text)
        if not llm_raw:
            return None
        data = self.parse_llm_json(llm_raw)
        if not data:
            return None
        # 校验并归一化
        confidence = 1.0
        cats = data.get('technical_categories', [])
        if isinstance(cats, str): cats = [cats]
        norm_cats = []
        for c in cats:
            if c in VALID_MAIN_CATS: norm_cats.append(c)
            else: confidence -= 0.1
        data['technical_categories'] = norm_cats if norm_cats else ['其他-待审核']

        sub = data.get('technical_subcategory', '')
        if isinstance(sub, list): sub = sub[0] if sub else ''
        data['technical_subcategory'] = sub if sub in VALID_SUB_CATS else '待分类'

        chain = data.get('industry_chain_position', '')
        data['industry_chain_position'] = chain if chain in VALID_CHAIN else '其他-待审核'

        apps = data.get('application_fields', [])
        if isinstance(apps, str): apps = [apps]
        data['application_fields'] = [a for a in apps if a in VALID_APPS] or ['其他-待审核']

        data['classification_confidence'] = round(max(0.0, min(1.0, confidence)), 2)
        data['draft'] = False
        data['updated_at'] = datetime.now(timezone.utc).isoformat()
        data['data_source'] = 'patent_daily_collector'
        return data

    # ─── Step 4: 入库 ───
    def save_patent(self, data):
        pn = data.get('patent_number')
        if not pn:
            return False
        # 检查是否已存在
        existing = self.db.table('patents').select('id').eq('patent_number', pn).execute()
        if existing.data:
            self.stats["skipped"] += 1
            return False
        if self.dry_run:
            self.stats["saved"] += 1
            return True
        try:
            self.db_write.table('patents').insert(data).execute()
            self.stats["saved"] += 1
            return True
        except Exception as e:
            print(f"  save error [{pn}]: {e}")
            return False

    # ─── 总管线 ───
    def run(self, max_results=0, days_back=7):
        print(f"\n{'='*60}")
        print(f"  AeroScope 专利日常采集 v2.0")
        print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"  范围: 最近 {days_back} 天 | 模式: {'预览' if self.dry_run else '写入'}")
        print(f"{'='*60}\n")

        # Step 1
        found = self.search_recent(days_back=days_back)
        print(f"[1/4] 搜索到 {len(found)} 条候选专利")
        if max_results > 0:
            found = found[:max_results]

        for i, p in enumerate(found):
            pn = p['patent_number']
            print(f"[2/4] [{i+1}/{len(found)}] {pn} ...")

            # Step 2: 抓取详情
            detail = self.fetch_detail(pn, p['google_url'])
            if not detail:
                self.backlog.append(p)
                print(f"  - 详情抓取失败，加入后备池")
                time.sleep(1)
                continue
            self.stats["collected"] += 1

            # Step 3: LLM 分类
            result = self.classify_patent(detail)
            if not result:
                self.backlog.append(detail)
                print(f"  - LLM 分类失败，加入后备池")
                time.sleep(1)
                continue
            self.stats["classified"] += 1
            conf = result.get('classification_confidence', 1.0)
            print(f"  -> {result.get('technical_categories',[])} | {result.get('industry_chain_position','')} | conf={conf}")

            # Step 4: 入库
            self.save_patent(result)
            time.sleep(1)

        # 保存后备池
        self._save_backlog()
        self._save_report()
        print(f"\n{'='*60}")
        print(f"  采集完成")
        print(f"  搜索: {self.stats['searched']} | 抓取: {self.stats['collected']} | 分类: {self.stats['classified']}")
        print(f"  入库: {self.stats['saved']} | 跳过: {self.stats['skipped']} | 后备: {len(self.backlog)}")
        print(f"{'='*60}")
        return self.stats

    def _save_report(self):
        os.makedirs(os.path.dirname(DAILY_REPORT), exist_ok=True)
        report = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'stats': self.stats,
            'backlog_count': len(self.backlog)
        }
        with open(DAILY_REPORT, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max", type=int, default=0)
    parser.add_argument("--days", type=int, default=7)
    args = parser.parse_args()
    p = PatentDailyCollector(dry_run=args.dry_run)
    p.run(max_results=args.max, days_back=args.days)
