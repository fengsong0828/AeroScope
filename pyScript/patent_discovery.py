"""
AeroScope 专利递归发现引擎
从一个已知专利 URL 出发，通过 Google Patents 页面关联关系
递归发现同一申请人的所有相关专利
"""
import os, sys, time, re
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


class PatentDiscoveryEngine(CollectorCore):
    """递归专利发现引擎"""

    def discover_from_seed(self, seed_url, company_name, max_patents=50):
        """
        从种子专利出发，递归发现同一申请人的专利
        每发现一个专利就抓取详情、LLM 结构化、入库
        """
        print(f"\n===== Discovery Engine =====")
        print(f"  Seed: {seed_url}")
        print(f"  Target company: {company_name}")
        print(f"  Max: {max_patents}")

        visited = set()
        queue = [(seed_url, 'seed')]
        stats = {"found": 0, "scraped": 0, "new": 0, "exists": 0, "fail": 0, "not_matching": 0}

        while queue and stats["scraped"] < max_patents:
            url, rel_type = queue.pop(0)
            patent_id = self._extract_id(url)

            if patent_id in visited:
                continue
            visited.add(patent_id)

            print(f"\n  [{stats['scraped']+1}] {patent_id} ({rel_type})")

            # Scrape the page (with retries)
            resp = None
            for attempt in range(3):
                try:
                    resp = http_requests.get(url, headers=HEADERS, timeout=45)
                    if resp.status_code == 200:
                        break
                except Exception as e:
                    if attempt < 2:
                        print(f"    Retry {attempt+1} (timeout)...")
                        time.sleep(3)
                    else:
                        print(f"    Failed after 3 attempts: {e}")
            if not resp or resp.status_code != 200:
                print(f"    HTTP {resp.status_code if resp else 'timeout'}, skip")
                continue

            html = resp.text
            soup = BeautifulSoup(html, 'html.parser')

            # --- 先提取所有关联专利（不论是否匹配）---
            backward_refs = set()
            for row in soup.find_all('tr', {'itemprop': 'backwardReferences'}):
                for m in re.finditer(r'([A-Z]{2}\d{7,}[A-Za-z]?)', row.get_text()):
                    backward_refs.add(m.group(1).upper())

            forward_refs = set()
            for row in soup.find_all('tr', {'itemprop': 'forwardReferences'}):
                for m in re.finditer(r'([A-Z]{2}\d{7,}[A-Za-z]?)', row.get_text()):
                    forward_refs.add(m.group(1).upper())

            similar_refs = set()
            section = soup.find('section', {'id': 'similarDocuments'})
            if section:
                for m in re.finditer(r'([A-Z]{2}\d{7,}[A-Za-z]?)', section.get_text()):
                    similar_refs.add(m.group(1).upper())

            all_found = set()
            for match in re.finditer(r'/patent/([A-Z]{2}\d{7,}[A-Za-z]?)/[a-z]{2}', html):
                pid = match.group(1).upper()
                if pid not in visited and len(pid) >= 12:
                    all_found.add(pid)
                    rel = []
                    if pid in backward_refs: rel.append('cites')
                    if pid in forward_refs: rel.append('cited_by')
                    if pid in similar_refs: rel.append('similar')
                    if not rel: rel.append('related')
                    queue.append((f"https://patents.google.com/patent/{pid}/zh", ','.join(rel)))
                    stats["found"] += 1

            print(f"    Linked: {len(backward_refs)}c / {len(forward_refs)}f / {len(similar_refs)}s / +{len(all_found)-len(backward_refs)-len(forward_refs)-len(similar_refs)} others")

            if stats["found"] % 50 == 0:
                print(f"  [Q] Queue: {len(queue)}, Visited: {len(visited)}")

            # --- 然后判断是否属于目标公司 ---
            assignee_meta = soup.find('meta', {'scheme': 'assignee'})
            assignee = (assignee_meta.get('content', '') if assignee_meta else '').lower()
            company_lower = company_name.lower()

            # 匹配逻辑：中文名 vs 英文名都可能
            is_match = False
            if company_lower in assignee or (company_lower.replace(' ','') in assignee.replace(' ','')):
                is_match = True
            else:
                # 从数据库查公司的英文名
                r = self.db.table("companies").select("name,name_en").ilike("name", f"%{company_name[:6]}%").limit(1).execute()
                if r.data and r.data[0]:
                    en_name = (r.data[0].get("name_en") or "").lower()
                    if en_name and (en_name in assignee or assignee in en_name):
                        is_match = True

            if not is_match and rel_type == 'seed':
                print(f"    ⚠ 种子专利不属于「{company_name}」！")
                print(f"    申请人: {assignee_meta.get('content','未知') if assignee_meta else '未知'}")
                print(f"    请去 patents.google.com 搜索「{company_name}」找一个真正属于该公司的专利作为种子")

            if not is_match:
                print(f"    Not matching: {assignee[:50]}")
                stats["not_matching"] = stats.get("not_matching", 0) + 1
            else:
                # This patent belongs to our company → LLM structure + store
                raw_text = soup.get_text(separator="\n", strip=True)[:6000]
                llm_raw = self.call_llm(PATENT_PROMPT,
                    f"Company: {company_name}\nPatent URL: {url}\nAssignee: {assignee}\nContent: {raw_text}")
                data = self.parse_llm_json(llm_raw)
                if data:
                    for df in ["application_date", "publication_date", "grant_date", "priority_date"]:
                        val = data.get(df, "")
                        if not val or val in ("", "未知", "Unknown", "N/A", "null"):
                            data.pop(df, None)

                    data["patent_number"] = patent_id
                    data["google_url"] = url
                    data["applicant"] = assignee_meta.get('content', company_name) if assignee_meta else company_name

                    related = []
                    for pid in backward_refs:
                        related.append({"patent_id": pid, "relation": "cites", "url": f"https://patents.google.com/patent/{pid}/zh"})
                    for pid in forward_refs:
                        related.append({"patent_id": pid, "relation": "cited_by", "url": f"https://patents.google.com/patent/{pid}/zh"})
                    for pid in similar_refs:
                        related.append({"patent_id": pid, "relation": "similar", "url": f"https://patents.google.com/patent/{pid}/zh"})
                    data["related_patents"] = related[:50]

                    r = self.db.table("companies").select("id").ilike("name", f"%{company_name[:6]}%").limit(1).execute()
                    if not r.data:
                        r = self.db.table("companies").select("id").ilike("name_en", f"%{company_name[:6]}%").limit(1).execute()
                    if r.data:
                    if r.data:
                        data["related_company_id"] = r.data[0]["id"]

                    ok = self.upsert("patents", data, "patent_number")
                    if ok:
                        stats["new"] += 1
                        print(f"    [SAVED] {data.get('title','')[:40]}")
                    else:
                        stats["fail"] += 1
                        print(f"    [FAIL] upsert error")
                else:
                    stats["fail"] += 1

            stats["scraped"] += 1

        print(f"\n  Done: found={stats['found']}, scraped={stats['scraped']}, new={stats['new']}, not_matching={stats.get('not_matching',0)}, fail={stats['fail']}")
        return stats

    def _extract_id(self, url):
        parts = [p for p in url.split('/') if p]
        if 'patent' in parts:
            idx = parts.index('patent')
            return parts[idx + 1] if idx + 1 < len(parts) else parts[-1]
        return url.split('/')[-1]


def discover(seed_url, company_name, max_patents=50):
    engine = PatentDiscoveryEngine()
    return engine.discover_from_seed(seed_url, company_name, max_patents)


if __name__ == "__main__":
    discover(
        "https://patents.google.com/patent/CN110267876B/zh",
        "AutoFlight",
        max_patents=30
    )
