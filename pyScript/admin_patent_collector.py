"""
AeroScope Admin: Company Patent Collector
Headless version — search Google Patents by company name + low-altitude keywords,
LLM structure, insert to Supabase, and auto-link to company.
"""
import os, sys, json, time, re, urllib.parse
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from dotenv import load_dotenv; load_dotenv()
from collector_core import CollectorCore
from llm_prompts import PATENT_PROMPT
import requests as http_requests
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
}

LOWALT_KEYWORDS = [
    "eVTOL", "drone", "UAV", "UAM", "AAM", "urban air mobility",
    "vertical takeoff", "multirotor", "tilting rotor", "flying car",
    "low altitude", "unmanned aerial", "electric aircraft",
    "battery drone", "flight control drone", "air taxi"
]


class CompanyPatentCollector(CollectorCore):

    def _search_google_patents(self, company_name, max_results):
        """Google Patents 搜索 - 已被屏蔽，返回空"""
        return []  # Google blocks automated search, use _search_wipo instead

    def _search_wipo_patents(self, company_name, max_results):
        """WIPO Patentscope 专利搜索（支持中文）"""
        results = []
        seen = set()

        # 中英文关键词组合
        search_combos = [
            (company_name, ""),                          # 纯公司名
            (company_name, "eVTOL OR drone OR UAV"),     # 英文低空
            (company_name, "无人机 OR 飞行器 OR 低空"),   # 中文低空
            (company_name, "垂直起降 OR 倾转旋翼"),        # 技术关键词
        ]

        for cn, kw in search_combos:
            if len(results) >= max_results:
                break
            q = f'PA:"{cn}"' if not kw else f'PA:"{cn}" AND EN_AB:({kw})'
            url = f"https://patentscope.wipo.int/search/en/result.jsf?query={urllib.parse.quote(q)}"
            print(f"  WIPO: PA:{cn} + {kw[:40]}")

            try:
                resp = http_requests.get(url, headers={
                    "User-Agent": "Mozilla/5.0",
                    "Accept": "text/html,application/json"
                }, timeout=30)
                html = resp.text

                # 方法1: 找专利号 — 严格验证格式
                patents_found = 0
                for pattern in [
                    r'(CN\d{8,10}[A-Za-z]?)',      # 中国: CN + 8~10位数字 + 可选的字母
                    r'WO(\d{4}/\d{6})',              # WIPO: WO2024/123456
                    r'(US\d{7,11}[A-Za-z]?)',        # 美国
                    r'(EP\d{7,8}[A-Za-z]?)',         # 欧洲
                ]:
                    for match in re.finditer(pattern, html):
                        pn = match.group(1).replace('/','')
                        # 长度校验：真实专利号 >= 10 个字符
                        if len(pn) >= 10 and pn not in seen:
                            seen.add(pn)
                            results.append({
                                "patent_id": pn,
                                "title": "",
                                "url": f"https://patents.google.com/patent/{pn}/zh"
                            })
                            patents_found += 1
                            if len(results) >= max_results:
                                break
                    if len(results) >= max_results:
                        break

                if patents_found > 0:
                    print(f"    Found {patents_found} patents: {[r['patent_id'] for r in results[-patents_found:]]}")

                if patents_found == 0:
                    # 方法2: 尝试提取 JSON 数据（如果页面包含）
                    json_match = re.search(r'searchResultData\s*=\s*(\{.*?\});', html, re.DOTALL)
                    if json_match:
                        try:
                            jdata = json.loads(json_match.group(1))
                            for item in jdata.get("results", []):
                                pn = item.get("woNum") or item.get("appNum", "")
                                if pn and pn not in seen:
                                    seen.add(pn)
                                    results.append({
                                        "patent_id": pn,
                                        "title": item.get("title", ""),
                                        "url": f"https://patents.google.com/patent/{pn}/zh"
                                    })
                        except:
                            pass

                time.sleep(2)
            except Exception as e:
                print(f"    WIPO failed: {e}")

        return results[:max_results]

    _search_wipo_patents = _search_google_patents  # WIPO 不可靠，禁用

    def _search_bing_patents(self, company_name, max_results):
        """通过 Bing 搜索结果中提取 Google Patents 链接"""
        results = []
        seen = set()

        for kw in ["eVTOL", "无人机 专利"]:
            if len(results) >= max_results:
                break
            query = f'{company_name} {kw} site:patents.google.com'
            url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}&count=30"
            print(f"  Bing search: {query[:60]}")

            try:
                resp = http_requests.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept-Language": "zh-CN,zh;q=0.9"
                }, timeout=15)
                html = resp.text

                # 从 Bing 搜索结果中提取 Google Patents 链接
                # Bing 的搜索结果链接格式: <a href="https://patents.google.com/patent/CNxxxxx/zh" ...>
                for match in re.finditer(r'patents\.google\.com/patent/([A-Z]{2}\d{7,}[A-Za-z]?)/[a-z]{2}', html):
                    pn = match.group(1).upper()
                    if pn not in seen and len(pn) >= 12:
                        patent_url = f"https://patents.google.com/patent/{pn}/zh"
                        # 验证该页面真的存在（HEAD request）
                        try:
                            hr = http_requests.head(patent_url, headers=HEADERS, timeout=10, allow_redirects=True)
                            if hr.status_code == 200:
                                seen.add(pn)
                                results.append({"patent_id": pn, "title": "", "url": patent_url})
                                print(f"    [valid] {pn}")
                            else:
                                print(f"    [skip] {pn} (HTTP {hr.status_code})")
                        except:
                            print(f"    [skip] {pn} (unreachable)")
                        if len(results) >= max_results:
                            break
                time.sleep(2)
            except Exception as e:
                print(f"    Bing failed: {e}")

        if results:
            print(f"    Verified: {[r['patent_id'] for r in results]}")
        else:
            print(f"    0 verified results")
        return results[:max_results]

    def search_new_patents(self, company_name, max_results=20):
        """通过 Bing → Google Patents 搜索公司相关专利"""
        all_results = self._search_bing_patents(company_name, max_results)
        print(f"  Total verified: {len(all_results)} patents for {company_name}")
        return all_results[:max_results]

    def get_company_patents(self, company_name):
        """获取公司已关联的专利列表"""
        patents = []
        seen = set()

        # 1. 找到所有匹配的公司（中文名+英文名都搜）
        company_ids = []
        r = self.db.table("companies").select("id,name,name_en").ilike("name", f"%{company_name[:6]}%").execute()
        if r.data:
            for c in r.data:
                company_ids.append(c["id"])

        # 也搜英文名
        r2 = self.db.table("companies").select("id").ilike("name_en", f"%{company_name[:6]}%").execute()
        if r2.data:
            for c in r2.data:
                if c["id"] not in company_ids:
                    company_ids.append(c["id"])

        # 2. 通过所有 company_ids 查关联专利
        for cid in company_ids:
            pr = self.db.table("patents").select("id,title,patent_number,legal_status,application_date,related_company_id") \
                .eq("related_company_id", cid).order("application_date", desc=True).limit(50).execute()
            if pr.data:
                for p in pr.data:
                    if p["id"] not in seen:
                        seen.add(p["id"])
                        patents.append(p)

        # 3. 按 applicant 搜索（用前几个字 + 英文名）
        name_key = company_name[:6]
        pr = self.db.table("patents").select("id,title,patent_number,legal_status,application_date,related_company_id") \
            .ilike("applicant", f"%{name_key}%").order("application_date", desc=True).limit(50).execute()
        if pr.data:
            for p in pr.data:
                if p["id"] not in seen:
                    seen.add(p["id"])
                    patents.append(p)

        return patents

    def collect_new_patents(self, company_name, max_results=10):
        """搜索+抓取新的专利: 搜索 → 逐个抓取详情 → LLM → 入库 → 关联"""
        print(f"\n===== Collecting new patents for: {company_name} =====")
        search_results = self.search_new_patents(company_name, max_results)
        stats = {"found": len(search_results), "new": 0, "exists": 0, "fail": 0}

        for i, item in enumerate(search_results):
            print(f"  [{i+1}/{len(search_results)}] {item['patent_id']}")
            res = self.scrape_and_store(company_name, item["url"], item["patent_id"])
            stats[res["status"]] = stats.get(res["status"], 0) + 1
            time.sleep(1)

        print(f"  Done: {stats}")
        return stats

    def add_patent_url(self, patent_url, company_name):
        """手动添加单条专利: 抓取→LLM→入库→关联"""
        patent_id = self._extract_patent_id(patent_url)
        if not patent_id:
            patent_id = patent_url.split('/')[-1]
        return self.scrape_and_store(company_name, patent_url, patent_id)

    def scrape_and_store(self, company_name, patent_url, patent_id):
        """抓取单个专利详情，LLM结构化，入库，关联企业"""
        try:
            resp = http_requests.get(patent_url, headers=HEADERS, timeout=30)
            soup = BeautifulSoup(resp.text, 'html.parser')
        except Exception as e:
            return {"status": "fail", "reason": str(e)[:60]}

        raw_text = soup.get_text(separator="\n", strip=True)[:6000]

        company_id = None
        r = self.db.table("companies").select("id,name").ilike("name", f"%{company_name}%").execute()
        if r.data:
            company_id = r.data[0]["id"]

        existing = self.db.table("patents").select("id,related_company_id").eq("patent_number", patent_id).execute()
        if existing.data:
            e = existing.data[0]
            if company_id and not e.get("related_company_id"):
                self.db.table("patents").update({"related_company_id": company_id}).eq("id", e["id"]).execute()
                return {"status": "linked", "patent_id": patent_id}
            return {"status": "exists", "patent_id": patent_id}

        llm_raw = self.call_llm(PATENT_PROMPT, f"Company: {company_name}\nPatent URL: {patent_url}\nContent: {raw_text}")
        data = self.parse_llm_json(llm_raw)
        if not data:
            return {"status": "fail", "reason": "LLM parse failed"}

        # 清洗日期字段：空值/无效值删除，避免数据库报错
        date_fields = ["application_date", "publication_date", "grant_date", "priority_date"]
        for df in date_fields:
            val = data.get(df, "")
            if not val or val in ("", "未知", "Unknown", "N/A", "null", "None"):
                del data[df]

        data["applicant"] = data.get("applicant", company_name)
        data["patent_number"] = patent_id
        data["google_url"] = patent_url
        if company_id:
            data["related_company_id"] = company_id

        ok = self.upsert("patents", data, "patent_number")
        return {"status": "ok" if ok else "fail", "patent_id": patent_id}

    def _extract_patent_id(self, href):
        parts = [p for p in href.split('/') if p]
        if 'patent' in parts:
            idx = parts.index('patent')
            return parts[idx + 1] if idx + 1 < len(parts) else parts[-1]
        return None


def search_by_company(company_name, max_results=10):
    """外部调用入口"""
    collector = CompanyPatentCollector()
    return collector.collect_for_company(company_name, max_results)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--company", required=True, help="Company name to search")
    parser.add_argument("--max", type=int, default=10, help="Max patents to collect")
    args = parser.parse_args()
    search_by_company(args.company, args.max)
