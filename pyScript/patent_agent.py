"""
AeroScope Patent Agent - 专利智能代理
负责：批量导入存量专利 + 分类回填 + 新专利发现 + PDF采集存储

用法:
  python pyScript/patent_agent.py                    # 全量运行
  python pyScript/patent_agent.py --import-details   # 仅批量导入patent_details.json
  python pyScript/patent_agent.py --reclassify       # 仅回填分类
  python pyScript/patent_agent.py --import-lowalt    # 仅导入low-alt发现专利
  python pyScript/patent_agent.py --import-cnipa     # 仅导入CNIPA批量数据
  python pyScript/patent_agent.py --import-ehang     # 仅导入EHang专利
  python pyScript/patent_agent.py --collect-pdfs     # 采集PDF到OSS
  python pyScript/patent_agent.py --max 50           # 限制处理数量
  python pyScript/patent_agent.py --dry-run          # 预览模式
"""
import os, sys, json, time, argparse, re
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_DIR = os.path.join(os.path.dirname(os.path.dirname(SCRIPT_DIR)),
                              "agent-workspace", "data-engineer", "data-schemas")
DETAILS_FILE = os.path.join(WORKSPACE_DIR, "patent_details.json")
LOWALT_FILE = os.path.join(WORKSPACE_DIR, "lowalt_patents.json")
CNIPA_FILE = os.path.join(WORKSPACE_DIR, "cnipa_bulk_parsed.json")
EHANG_FILE = os.path.join(WORKSPACE_DIR, "ehang_patents_cnipa.json")

sys.path.insert(0, SCRIPT_DIR)
from collector_core import CollectorCore
from llm_prompts import PATENT_PROMPT
from patent_classification_rules import (
    TECH_CATEGORIES, get_all_tech_categories, get_all_tech_subcategories,
    get_all_chain_positions, get_all_app_fields
)
import requests as http_req
from bs4 import BeautifulSoup
import oss2

VALID_MAIN_CATS = set(get_all_tech_categories())
VALID_SUB_CATS = set(get_all_tech_subcategories())
VALID_CHAIN = set(get_all_chain_positions())
VALID_APPS = set(get_all_app_fields())

FIELD_MAP = {
    "patent_number": "patent_number",
    "title": "title",
    "applicant": "applicant",
    "applicant_cn": "applicant",
    "application_date": "application_date",
    "legal_status": "legal_status",
    "abstract": "abstract",
    "claims": "claims",
    "publication_number": "publication_number",
    "publication_date": "publication_date",
    "grant_date": "grant_date",
    "priority_date": "priority_date",
    "inventors": "inventors",
    "ipc_class": "ipc_class",
    "cpc_class": "cpc_class",
    "citation_count": "citation_count",
    "google_url": "google_url",
}


def normalize_legal_status(raw_status):
    if not raw_status:
        return ""
    s = raw_status.strip().lower()
    if s in ("granted", "active", "valid", "patented case"):
        return "有效"
    if any(kw in s for kw in ("expired", "fee related", "lapsed", "abandoned",
                                "withdrawn", "revoked", "ceased", "terminated",
                                "rejected", "refused", "invalid")):
        return "无效"
    if any(kw in s for kw in ("pending", "application", "filed", "examination",
                                "search report", "substantive examination")):
        return "审中"
    return ""


def infer_patent_type(patent_number):
    if not patent_number:
        return "发明专利"
    pn = patent_number.upper()
    if "U" in pn[-2:]:
        return "实用新型"
    return "发明专利"


class PatentAgent(CollectorCore):

    def __init__(self, dry_run=False):
        super().__init__()
        self.dry_run = dry_run
        self.stats = {"new": 0, "updated": 0, "skip": 0, "fail": 0, "classified": 0}
        self._existing_pns = None

    def get_existing_pns(self, refresh=False):
        if self._existing_pns is not None and not refresh:
            return self._existing_pns
        pns = set()
        offset = 0
        batch = 500
        max_retries = 3
        while True:
            for retry in range(max_retries):
                try:
                    result = self.db.table("patents").select("patent_number") \
                        .range(offset, offset + batch - 1).execute()
                    break
                except Exception as e:
                    if retry < max_retries - 1:
                        time.sleep(2 * (retry + 1))
                        self._init_supabase()
                    else:
                        raise e
            if not result.data:
                break
            for r in result.data:
                pns.add(r["patent_number"])
            offset += batch
            if len(result.data) < batch:
                break
        self._existing_pns = pns
        return pns

    def classify_with_llm(self, patent_info):
        text = f"专利标题: {patent_info.get('title', '')}\n"
        text += f"摘要: {patent_info.get('abstract', '')}\n"
        text += f"申请人: {patent_info.get('applicant', '')}"
        if len(text) < 20:
            return None

        llm_raw = self.call_llm(PATENT_PROMPT, text)
        if not llm_raw:
            return None

        llm_data = self.parse_llm_json(llm_raw)
        if not llm_data:
            return None

        confidence = 1.0
        cats = llm_data.get("technical_categories", [])
        if isinstance(cats, str):
            cats = [cats]
        norm_cats = []
        for c in cats:
            if c in VALID_MAIN_CATS:
                norm_cats.append(c)
            else:
                confidence -= 0.1
        llm_data["technical_categories"] = norm_cats if norm_cats else ["其他-待审核"]

        sub = llm_data.get("technical_subcategory", "")
        if isinstance(sub, list):
            sub = sub[0] if sub else ""
        llm_data["technical_subcategory"] = sub if sub in VALID_SUB_CATS else "待分类"

        chain = llm_data.get("industry_chain_position", "")
        llm_data["industry_chain_position"] = chain if chain in VALID_CHAIN else "其他-待审核"

        apps = llm_data.get("application_fields", [])
        if isinstance(apps, str):
            apps = [apps]
        llm_data["application_fields"] = [a for a in apps if a in VALID_APPS] or ["其他-待审核"]

        llm_data["classification_confidence"] = round(max(0.0, min(1.0, confidence)), 2)
        return llm_data

    def insert_patent(self, data):
        pn = data.get("patent_number")
        if not pn:
            return False
        print(f"    [DEBUG] insert_patent called for {pn}")

        record = {}
        for json_key, db_col in FIELD_MAP.items():
            val = data.get(json_key)
            if val and val not in ("", "N/A", "null"):
                record[db_col] = val

        cn = data.get("applicant_cn", "")
        en = data.get("applicant", "")
        if cn and cn not in ("", "N/A", "null"):
            record["applicant"] = cn
        elif en and en not in ("", "N/A", "null"):
            record["applicant"] = en

        if "patent_type" not in record or not record["patent_type"]:
            record["patent_type"] = infer_patent_type(pn)

        raw_status = record.get("legal_status", "")
        record["legal_status"] = normalize_legal_status(raw_status)
        if not record.get("legal_status"):
            record.pop("legal_status", None)

        for df in ["application_date", "publication_date", "grant_date", "priority_date"]:
            if df in record and not record[df]:
                del record[df]

        inventors = record.get("inventors", [])
        if isinstance(inventors, list) and inventors:
            record["inventor_count"] = len(inventors)

        record["draft"] = False
        record["updated_at"] = datetime.now(timezone.utc).isoformat()
        record["data_source"] = "patent_agent"

        if self.dry_run:
            return True

        try:
            existing = self.db.table("patents").select("id").eq("patent_number", pn).execute()
            if existing.data:
                self.db_write.table("patents").update(record).eq("patent_number", pn).execute()
                self.stats["updated"] += 1
                print(f"    DB: updated {pn}")
            else:
                record["created_at"] = datetime.now(timezone.utc).isoformat()
                result = self.db_write.table("patents").insert(record).execute()
                if result.data:
                    self.stats["new"] += 1
                    print(f"    DB: inserted {pn}")
                else:
                    print(f"    DB: no data returned for {pn}")
                    self.stats["fail"] += 1
                    return False
            return True
        except Exception as e:
            print(f"  [FAIL] {pn}: {str(e)[:200]}")
            self.stats["fail"] += 1
            return False

    def import_details_batch(self, max_count=0):
        print("\n=== Phase 1: Import from patent_details.json ===")

        if not os.path.exists(DETAILS_FILE):
            print(f"File not found: {DETAILS_FILE}")
            return

        with open(DETAILS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        patents = data["patents"]
        if max_count > 0:
            patents = patents[:max_count]

        print(f"Loading {len(patents)} patents...")

        existing_pns = self.get_existing_pns()
        print(f"DB has {len(existing_pns)} patents")

        new_patents = [p for p in patents if p["patent_number"] not in existing_pns]
        print(f"New patents to import: {len(new_patents)}")

        for i, p in enumerate(new_patents):
            pn = p["patent_number"]
            print(f"  [{i+1}/{len(new_patents)}] {pn} ...")
            self.insert_patent(p)
            time.sleep(0.1)

        print(f"  New: {self.stats['new']} | Updated: {self.stats['updated']} | Failed: {self.stats['fail']}")

    def import_lowalt_batch(self, max_count=0):
        print("\n=== Phase 2: Import from lowalt_patents.json ===")

        if not os.path.exists(LOWALT_FILE):
            print(f"File not found: {LOWALT_FILE}")
            return

        with open(LOWALT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        patents = data["patents"]
        if max_count > 0:
            patents = patents[:max_count]

        print(f"Loading {len(patents)} patents...")

        existing_pns = self.get_existing_pns()
        print(f"DB has {len(existing_pns)} patents")

        new_patents = [p for p in patents if p["patent_number"] not in existing_pns]
        print(f"New low-alt patents to import: {len(new_patents)}")

        for i, p in enumerate(new_patents):
            pn = p["patent_number"]
            print(f"  [{i+1}/{len(new_patents)}] {pn} - {p.get('title', '')[:60]}")

            classification = self.classify_with_llm(p)
            if classification:
                merged = {**p, **classification}
                self.stats["classified"] += 1
            else:
                merged = p

            print(f"    [TRACE] calling insert_patent for {merged.get('patent_number','?')}")
            self.insert_patent(merged)
            time.sleep(1.0)

        print(f"\n  Classified: {self.stats['classified']} | Skipped: {self.stats['skip']} | Failed: {self.stats['fail']}")

    def import_cnipa_batch(self, max_count=0):
        print("\n=== Phase 4: Import from cnipa_bulk_parsed.json ===")

        if not os.path.exists(CNIPA_FILE):
            print(f"File not found: {CNIPA_FILE}")
            return

        with open(CNIPA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        patents = data["patents"]
        print(f"Loading {len(patents)} patents...")

        existing_pns = self.get_existing_pns()
        print(f"DB has {len(existing_pns)} patents")

        new_patents = []
        seen = set()
        for p in patents:
            pn = p["patent_number"]
            if ";" in pn:
                for sub in pn.split(";"):
                    sub = sub.strip()
                    if sub and sub not in existing_pns and sub not in seen:
                        seen.add(sub)
                        new_patents.append({**p, "patent_number": sub})
            else:
                if pn not in existing_pns and pn not in seen:
                    seen.add(pn)
                    new_patents.append(p)

        if max_count > 0:
            new_patents = new_patents[:max_count]

        print(f"New CNIPA patents to import: {len(new_patents)}")

        for i, p in enumerate(new_patents):
            pn = p["patent_number"]
            t = (p.get("title") or "")[:60]
            try:
                print(f"  [{i+1}/{len(new_patents)}] {pn} - {t}")
            except (UnicodeEncodeError, UnicodeDecodeError):
                print(f"  [{i+1}/{len(new_patents)}] {pn}")

            classification = self.classify_with_llm(p)
            if classification:
                merged = {**p, **classification}
                self.stats["classified"] += 1
            else:
                merged = p

            self.insert_patent(merged)
            time.sleep(1.0)

        print(f"  New: {self.stats['new']} | Classified: {self.stats['classified']} | Failed: {self.stats['fail']}")

    def import_ehang_batch(self, max_count=0):
        print("\n=== Phase 5: Import from ehang_patents_cnipa.json ===")

        if not os.path.exists(EHANG_FILE):
            print(f"File not found: {EHANG_FILE}")
            return

        with open(EHANG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        patents = data["patents"]
        print(f"Loading {len(patents)} patents...")

        existing_pns = self.get_existing_pns()
        print(f"DB has {len(existing_pns)} patents")

        new_patents = []
        seen = set()
        for p in patents:
            pn = p["patent_number"]
            if ";" in pn:
                for sub in pn.split(";"):
                    sub = sub.strip()
                    if sub and sub not in existing_pns and sub not in seen:
                        seen.add(sub)
                        new_patents.append({**p, "patent_number": sub})
            else:
                if pn not in existing_pns and pn not in seen:
                    seen.add(pn)
                    new_patents.append(p)

        if max_count > 0:
            new_patents = new_patents[:max_count]

        print(f"New EHang patents to import: {len(new_patents)}")

        for i, p in enumerate(new_patents):
            pn = p["patent_number"]
            t = (p.get("title") or "")[:60]
            try:
                print(f"  [{i+1}/{len(new_patents)}] {pn} - {t}")
            except (UnicodeEncodeError, UnicodeDecodeError):
                print(f"  [{i+1}/{len(new_patents)}] {pn}")

            classification = self.classify_with_llm(p)
            if classification:
                merged = {**p, **classification}
                self.stats["classified"] += 1
            else:
                merged = p

            self.insert_patent(merged)
            time.sleep(1.0)

        print(f"  New: {self.stats['new']} | Classified: {self.stats['classified']} | Failed: {self.stats['fail']}")

    def _parse_patent_page(self, soup, pn):
        """从Google Patents页面提取：application_number, cpc_class, background_art, pdf_url"""
        result = {}
        
        # 1. 申请号 - 格式: CN2024XXXXXXXX.X 或 CN2024XXXXXXXX.XA
        for dd in soup.find_all(["dd", "span"]):
            text = dd.get_text(strip=True)
            if re.match(r"CN\d{12,}\.\d[A-Z]?", text):
                result["application_number"] = text
                break
        if "application_number" not in result:
            for item in soup.find_all(itemprop="applicationNumber"):
                result["application_number"] = item.get_text(strip=True)

        # 2. CPC分类
        cpc_seen = set()
        cpc_parts = []
        for tag in soup.find_all(["dd", "span", "li", "td"]):
            text = tag.get_text(strip=True)
            if re.match(r"^[A-HY]\d{2}[A-Z]\d+/\d+$", text) and text not in cpc_seen:
                cpc_seen.add(text)
                cpc_parts.append(text)
        if not cpc_parts:
            for tag in soup.find_all(["dd", "span", "li", "td"]):
                text = tag.get_text(strip=True)
                if re.match(r"^[A-HY]\d{2}[A-Z]\d+/\d+", text) and text not in cpc_seen:
                    cpc_seen.add(text)
                    cpc_parts.append(text)
        result["cpc_class"] = ";".join(cpc_parts[:15]) if cpc_parts else ""

        # 3. 背景技术
        desc = ""
        desc_section = soup.find("section", itemprop="description")
        if desc_section:
            desc = desc_section.get_text(separator="\n", strip=True)
        if not desc:
            for div in soup.find_all(["div", "section"]):
                txt = div.get_text(strip=True)[:100]
                if "背景技术" in txt or "Background" in txt:
                    desc = div.find_parent().get_text(separator="\n", strip=True) if div.find_parent() else div.get_text(separator="\n", strip=True)
                    break
        if desc:
            lines = desc.split("\n")
            bg_lines = []
            capture = False
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if re.search(r"背景技术|技术领域|TECHNICAL FIELD|BACKGROUND", line, re.I):
                    capture = True
                    continue
                if capture:
                    if re.search(r"发明内容|附图说明|具体实施|实施方式|SUMMARY|BRIEF DESCRIPTION|DETAILED DESCRIPTION|权利要求|CLAIMS", line, re.I):
                        break
                    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\u200b-\u200f\u2028-\u202f\u2060-\u206f\ufeff]", "", line)
                    if len(cleaned) > 10:
                        bg_lines.append(cleaned)
            result["background_art"] = " ".join(bg_lines)[:3000] if bg_lines else ""

        # 4. PDF URL
        for a in soup.find_all("a", href=re.compile(r"\.pdf$")):
            href = a.get("href", "")
            if "patentimages.storage.googleapis.com" in href:
                result["pdf_found"] = href
                break
        if "pdf_found" not in result:
            for meta in soup.find_all("meta"):
                c = meta.get("content", "")
                if "patentimages.storage.googleapis.com" in c and c.endswith(".pdf"):
                    result["pdf_found"] = c
                    break
        
        return result

    def collect_pdfs_batch(self, max_count=0):
        print("\n=== Phase 6: Enrich from Google Patents (PDF + BG + CPC + AppNum) ===")
        try:
            auth = oss2.Auth(os.getenv("ALIBABA_ACCESS_KEY_ID"), os.getenv("ALIBABA_ACCESS_KEY_SECRET"))
            bucket = oss2.Bucket(auth, os.getenv("OSS_ENDPOINT"), os.getenv("OSS_PRIVATE_BUCKET"))
        except Exception as e:
            print(f"  OSS init failed: {e}")
            return

        query = self.db.table("patents").select("id,patent_number,google_url,pdf_url,application_number,cpc_class,background_art") \
            .is_("pdf_url", "null") \
            .order("application_date", desc=True)
        if max_count > 0:
            query = query.limit(max_count)
        result = query.execute()
        patents = result.data
        print(f"  Patents without PDF: {len(patents)}")
        
        pdf_collected = 0
        bg_updated = 0
        meta_updated = 0
        HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                   "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"}

        for i, p in enumerate(patents):
            pn = p["patent_number"]
            try:
                print(f"  [{i+1}/{len(patents)}] {pn}")
            except:
                print(f"  [{i+1}/{len(patents)}]")

            update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
            need_update = False

            # 1. Scrape Google Patents page
            try:
                gp_url = f"https://patents.google.com/patent/{pn}/zh"
                resp = http_req.get(gp_url, headers=HEADERS, timeout=20)
                if resp.status_code != 200:
                    print(f"    HTTP {resp.status_code}")
                    continue
                soup = BeautifulSoup(resp.text, "html.parser")
                parsed = self._parse_patent_page(soup, pn)
            except Exception as e:
                print(f"    Page error: {e}")
                continue

            # 2. Fill application_number if missing
            if not p.get("application_number") and parsed.get("application_number"):
                update_data["application_number"] = parsed["application_number"]
                meta_updated += 1
                need_update = True

            # 3. Fill cpc_class if missing
            if not p.get("cpc_class") and parsed.get("cpc_class"):
                update_data["cpc_class"] = parsed["cpc_class"]
                meta_updated += 1
                need_update = True

            # 4. Fill background_art if missing
            if not p.get("background_art") and parsed.get("background_art"):
                update_data["background_art"] = parsed["background_art"]
                bg_updated += 1
                need_update = True

            # 5. PDF download + OSS upload (or mark as no_pdf)
            if parsed.get("pdf_found"):
                try:
                    pdf_resp = http_req.get(parsed["pdf_found"], headers=HEADERS, timeout=60)
                    if pdf_resp.status_code == 200:
                        pdf_bytes = pdf_resp.content
                        oss_path = f"patents/{pn}.pdf"
                        bucket.put_object(oss_path, pdf_bytes, headers={
                            "Content-Type": "application/pdf",
                            "Content-Disposition": "inline"
                        })
                        update_data["pdf_url"] = f"/pdf/{oss_path}"
                        pdf_collected += 1
                        need_update = True
                        print(f"    PDF {len(pdf_bytes)/1024:.0f} KB -> OSS")
                except Exception as e:
                    print(f"    PDF error: {e}")
            else:
                # 谷歌无PDF，标记跳过，避免重复查询
                update_data["pdf_url"] = "N/A"
                need_update = True

            # 6. Write to DB
            if need_update:
                try:
                    self.db_write.table("patents").update(update_data).eq("id", p["id"]).execute()
                except Exception as e:
                    print(f"    DB error: {e}")

            time.sleep(1.2)

        print(f"\n  PDFs: {pdf_collected} | BG: {bg_updated} | Meta: {meta_updated}")

    def reclassify_batch(self, max_count=0):
        """委托 PatentReclassify 对存量专利回填分类信息"""
        print("\n=== Phase 3: Reclassify existing patents ===")
        from patent_reclassify import PatentReclassify
        reclass = PatentReclassify(dry_run=self.dry_run, delay=1.0)
        reclass.run(max_count=max_count, only_unclassified=False, force=False, resume=True)

    def run_all(self, max_count=0, phases=None):
        if phases is None:
            phases = ["details", "lowalt", "reclassify"]

        if "details" in phases:
            self.import_details_batch(max_count)

        if "lowalt" in phases:
            self.import_lowalt_batch(max_count)

        if "reclassify" in phases:
            self.reclassify_batch(max_count)

        if "cnipa" in phases:
            self.import_cnipa_batch(max_count)

        if "ehang" in phases:
            self.import_ehang_batch(max_count)

        if "pdfs" in phases:
            self.collect_pdfs_batch(max_count)

        print(f"\n{'='*60}")
        print(f"  PATENT AGENT SUMMARY")
        print(f"  New: {self.stats['new']} | Updated: {self.stats['updated']}")
        print(f"  Classified: {self.stats['classified']} | Skipped: {self.stats['skip']}")
        print(f"  Failed: {self.stats['fail']}")
        print(f"{'='*60}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max", type=int, default=0)
    parser.add_argument("--import-details", action="store_true")
    parser.add_argument("--import-lowalt", action="store_true")
    parser.add_argument("--import-cnipa", action="store_true")
    parser.add_argument("--import-ehang", action="store_true")
    parser.add_argument("--reclassify", action="store_true")
    parser.add_argument("--collect-pdfs", action="store_true")
    args = parser.parse_args()

    agent = PatentAgent(dry_run=args.dry_run)

    phases = []
    if args.import_details:
        phases.append("details")
    if args.import_lowalt:
        phases.append("lowalt")
    if args.import_cnipa:
        phases.append("cnipa")
    if args.import_ehang:
        phases.append("ehang")
    if args.reclassify:
        phases.append("reclassify")
    if args.collect_pdfs:
        phases.append("pdfs")
    if not phases:
        phases = ["details", "lowalt", "reclassify"]

    agent.run_all(max_count=args.max, phases=phases)
