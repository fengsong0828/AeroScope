"""第一步：统计 applicant 中英夹杂的专利"""
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv; load_dotenv()
from collector_core import CollectorCore

core = CollectorCore()

mixed = []    # 同时含中文和英文
pure_en = []   # 纯英文
pure_cn = []   # 纯中文
empty = []

offset, batch = 0, 500
while True:
    r = core.db.table("patents").select(
        "id,applicant,patent_number,pdf_url"
    ).order("id").range(offset, offset + batch - 1).execute()
    if not r.data:
        break
    for p in r.data:
        app = (p.get("applicant") or "").strip()
        has_cn = bool(re.search(r'[\u4e00-\u9fff]', app))
        has_en = bool(re.search(r'[A-Za-z]', app))
        rec = {"id": p["id"], "patent_number": p.get("patent_number",""), "applicant": app, "has_pdf": bool(p.get("pdf_url"))}
        if not app:
            empty.append(rec)
        elif has_cn and has_en:
            mixed.append(rec)
        elif has_cn:
            pure_cn.append(rec)
        elif has_en:
            pure_en.append(rec)
        else:
            empty.append(rec)
    offset += batch
    if len(r.data) < batch:
        break

print(f"总专利数:        {len(mixed)+len(pure_cn)+len(pure_en)+len(empty)}")
print(f"中英夹杂:        {len(mixed)}  (有PDF: {sum(1 for m in mixed if m['has_pdf'])})")
print(f"纯中文:          {len(pure_cn)}")
print(f"纯英文:          {len(pure_en)}  (有PDF: {sum(1 for m in pure_en if m['has_pdf'])})")
print(f"空/无申请人:     {len(empty)}")

# 展示几个中英夹杂的样例
print("\n--- 中英夹杂样例 (前10条) ---")
for m in mixed[:10]:
    pdf_flag = "✓PDF" if m["has_pdf"] else "✗无PDF"
    print(f"  [{pdf_flag}] {m['applicant'][:80]}")

# 展示几个纯英文的样例
print("\n--- 纯英文样例 (前10条) ---")
for m in pure_en[:10]:
    pdf_flag = "✓PDF" if m["has_pdf"] else "✗无PDF"
    print(f"  [{pdf_flag}] {m['applicant'][:80]}")
