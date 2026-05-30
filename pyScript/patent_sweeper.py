"""
AeroScope Patent Sweeper — 专利大而全收集器

用法:
  python pyScript/patent_sweeper.py --company "亿航智能" --seed "URL" --quick --max 100 --export
  python pyScript/patent_sweeper.py --company "亿航智能" --summary --export
  python pyScript/patent_sweeper.py --company "亿航智能" --enrich --max 50

输出: agent-workspace/data-engineer/data-schemas/{公司名}_patents.csv
"""
import os, sys, time, re, json, argparse, csv
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv; load_dotenv()
from collector_core import CollectorCore
from llm_prompts import PATENT_PROMPT
import requests as http_requests
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
}


class PatentSweeper(CollectorCore):
    """快速专利收集器 — 先做大而全，再慢慢充实"""

    CSV_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                           "agent-workspace", "data-engineer", "data-schemas")

    def __init__(self, company_name):
        super().__init__()
        self.company_name = company_name
        self.company_id = self._find_company()
        self.collected = []  # 本次收集的专利
        os.makedirs(self.CSV_DIR, exist_ok=True)

    def _csv_path(self):
        safe_name = re.sub(r'[\\/*?:"<>|]', '', self.company_name)[:30]
        return os.path.join(self.CSV_DIR, f"{safe_name}_patents.csv")

    def export_csv(self):
        """导出已收集专利到 CSV"""
        path = self._csv_path()
        if not self.collected:
            print("  No data to export")
            return

        with open(path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(["company", "patent_number", "title", "legal_status", "google_url", "application_date"])
            for p in self.collected:
                writer.writerow([
                    self.company_name,
                    p.get("patent_number", ""),
                    p.get("title", ""),
                    p.get("legal_status", ""),
                    p.get("google_url", ""),
                    p.get("application_date", "")
                ])
        print(f"\n  📄 CSV exported: {path} ({len(self.collected)} records)")

    def export_summary_csv(self):
        """从数据库导出公司全部专利到 CSV"""
        path = self._csv_path()
        r = self.db.table("patents").select("patent_number,title,legal_status,google_url,application_date,abstract,applicant") \
            .eq("related_company_id", self.company_id).order("created_at", desc=True).execute()

        if not r.data:
            print("  No data to export")
            return

        with open(path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(["company", "patent_number", "title", "applicant", "legal_status",
                             "application_date", "google_url", "abstract"])
            for p in r.data:
                writer.writerow([
                    self.company_name,
                    p.get("patent_number", ""),
                    p.get("title", ""),
                    p.get("applicant", ""),
                    p.get("legal_status", ""),
                    p.get("application_date", ""),
                    p.get("google_url", ""),
                    p.get("abstract", "")[:200]
                ])
        print(f"\n  📄 CSV exported: {path} ({len(r.data)} records)")

    def _find_company(self):
        r = self.db.table("companies").select("id,name,name_en").ilike("name", f"%{self.company_name[:6]}%").limit(1).execute()
        if not r.data:
            r = self.db.table("companies").select("id").ilike("name_en", f"%{self.company_name[:6]}%").limit(1).execute()
        return r.data[0]["id"] if r.data else None

    def quick_sweep(self, seed_url, max_patents=100):
        """Phase 1: 快速扫描 — 只收集基本信息，跳过 LLM"""
        print(f"\n{'='*60}")
        print(f"  Patent Sweeper Phase 1: Quick Collection")
        print(f"  Company: {self.company_name} (id={self.company_id})")
        print(f"  Seed: {seed_url}")
        print(f"  Max: {max_patents}")
        print(f"{'='*60}")

        visited = set()
        queue = [(seed_url, 'seed')]
        stats = {"scanned": 0, "matched": 0, "skipped": 0, "stored": 0}

        while queue and stats["scanned"] < max_patents:
            url, rel = queue.pop(0)
            patent_id = self._extract_id(url)
            if patent_id in visited:
                continue
            visited.add(patent_id)
            stats["scanned"] += 1

            # 抓取页面
            try:
                resp = http_requests.get(url, headers=HEADERS, timeout=30)
                if resp.status_code != 200:
                    continue
            except:
                time.sleep(2)
                continue

            soup = BeautifulSoup(resp.text, 'html.parser')

            # 提取申请人
            assignee_meta = soup.find('meta', {'scheme': 'assignee'})
            assignee = (assignee_meta.get('content', '') if assignee_meta else '').strip()

            # 判断是否属于目标公司
            is_match = False
            if self.company_name[:4] in assignee:
                is_match = True
            else:
                # 查英文名匹配
                r = self.db.table("companies").select("name_en").eq("id", self.company_id).execute()
                if r.data and r.data[0].get("name_en"):
                    en = r.data[0]["name_en"].lower()
                    if en in assignee.lower():
                        is_match = True

            if not is_match:
                stats["skipped"] += 1
                if stats["scanned"] % 20 == 0:
                    print(f"  [{stats['scanned']}] skipped {stats['skipped']}, matched {stats['matched']}, queue {len(queue)}")
            else:
                stats["matched"] += 1
                # 快速提取基本信息
                title = (soup.find('title').text or '').replace(' - Google Patents', '').strip() if soup.find('title') else ''
                status = 'Unknown'
                status_elems = soup.find_all(string=re.compile(r'^Status'))
                for elem in status_elems:
                    text = elem.find_parent().get_text().replace('Status', '').strip()
                    if text:
                        status = text[:100]
                        break

                record = {
                    "patent_number": patent_id,
                    "title": title[:300],
                    "applicant": assignee,
                    "legal_status": status[:100],
                    "google_url": url,
                    "related_company_id": self.company_id,
                    "draft": False
                }
                self.upsert("patents", record, "patent_number")
                stats["stored"] += 1
                self.collected.append(record)
                print(f"  [{stats['scanned']}] ✅ {patent_id} | {title[:40]}")

            # 提取关联专利链接
            for match in re.finditer(r'/patent/([A-Z]{2}\d{7,}[A-Za-z]?)/[a-z]{2}', resp.text):
                pid = match.group(1).upper()
                if pid not in visited and len(pid) >= 12:
                    queue.append((f"https://patents.google.com/patent/{pid}/zh", 'related'))
            time.sleep(0.5)

        print(f"\n  {'='*40}")
        print(f"  Summary: scanned={stats['scanned']} | matched={stats['matched']} | stored={stats['stored']} | skipped={stats['skipped']}")
        return stats

    def enrich_by_company(self, max_patents=50):
        """Phase 2: 充实 — 对已有 URL 的专利做 LLM 结构化"""
        print(f"\n{'='*60}")
        print(f"  Patent Sweeper Phase 2: Enrichment")
        print(f"  Company: {self.company_name}")
        print(f"{'='*60}")

        # 找该公司的专利中 google_url 不为空但缺少详细字段的
        r = self.db.table("patents").select("id,patent_number,google_url,abstract") \
            .eq("related_company_id", self.company_id) \
            .is_("abstract", "null") \
            .limit(max_patents).execute()

        if not r.data or len(r.data) == 0:
            # 尝试只要 google_url 不为空的
            r = self.db.table("patents").select("id,patent_number,google_url") \
                .eq("related_company_id", self.company_id) \
                .limit(max_patents).execute()

        if not r.data:
            print("  No patents to enrich")
            return {"enriched": 0}

        enriched = 0
        for i, p in enumerate(r.data):
            url = p.get("google_url")
            if not url:
                continue
            print(f"  [{i+1}/{len(r.data)}] {p['patent_number']}")

            try:
                resp = http_requests.get(url, headers=HEADERS, timeout=30)
                soup = BeautifulSoup(resp.text, 'html.parser')
                raw_text = soup.get_text(separator="\n", strip=True)[:6000]

                llm_raw = self.call_llm(PATENT_PROMPT, f"Patent URL: {url}\nContent: {raw_text}")
                data = self.parse_llm_json(llm_raw)
                if data:
                    for df in ["application_date", "publication_date", "grant_date", "priority_date"]:
                        if data.get(df, "") in ("", "未知", "Unknown", "N/A", "null"):
                            data.pop(df, None)
                    data["google_url"] = url
                    data["related_company_id"] = self.company_id
                    self.upsert("patents", data, "patent_number")
                    enriched += 1
                    print(f"    ✅ {data.get('title','')[:40]}")
                else:
                    print(f"    ❌ LLM failed")
            except Exception as e:
                print(f"    ❌ {e}")
            time.sleep(1)

        print(f"\n  Enriched: {enriched} patents")
        return {"enriched": enriched}

    def _extract_id(self, url):
        parts = [p for p in url.split('/') if p]
        if 'patent' in parts:
            idx = parts.index('patent')
            return parts[idx + 1] if idx + 1 < len(parts) else parts[-1]
        return url.split('/')[-1]

    def summary(self):
        """公司专利汇总"""
        r = self.db.table("patents").select("id,patent_number,title,legal_status,google_url,abstract") \
            .eq("related_company_id", self.company_id) \
            .order("created_at", desc=True).execute()

        print(f"\n{'='*60}")
        print(f"  Patent Summary: {self.company_name}")
        print(f"  Total: {len(r.data) if r.data else 0} patents")
        print(f"{'='*60}")

        if r.data:
            active = sum(1 for p in r.data if p.get("legal_status", "") in ("有效", "Active", "Granted"))
            with_url = sum(1 for p in r.data if p.get("google_url"))
            with_abstract = sum(1 for p in r.data if p.get("abstract"))
            print(f"  Active: {active} | With URL: {with_url} | With Details: {with_abstract}")

            print(f"\n  Patent List:")
            for p in r.data[:20]:
                status = p.get("legal_status", "?")[:10]
                url_mark = "🔗" if p.get("google_url") else "  "
                detail_mark = "📄" if p.get("abstract") else "  "
                print(f"  {url_mark}{detail_mark} {p['patent_number']} [{status}] {str(p.get('title',''))[:50]}")

        return r.data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Patent Sweeper")
    parser.add_argument("--company", required=True)
    parser.add_argument("--seed", help="Seed patent URL for discovery")
    parser.add_argument("--max", type=int, default=100)
    parser.add_argument("--quick", action="store_true", help="Phase 1: quick collection")
    parser.add_argument("--enrich", action="store_true", help="Phase 2: LLM enrichment")
    parser.add_argument("--summary", action="store_true", help="Show company patent summary")
    parser.add_argument("--export", action="store_true", help="Export to CSV")
    args = parser.parse_args()

    sweeper = PatentSweeper(args.company)

    if args.quick and args.seed:
        sweeper.quick_sweep(args.seed, args.max)
        if args.export:
            sweeper.export_csv()
    elif args.enrich:
        sweeper.enrich_by_company(args.max)
        if args.export:
            sweeper.export_summary_csv()
    elif args.summary:
        sweeper.summary()
        if args.export:
            sweeper.export_summary_csv()
    else:
        if args.seed:
            sweeper.quick_sweep(args.seed, args.max)
        sweeper.summary()
        if args.export:
            sweeper.export_summary_csv()
