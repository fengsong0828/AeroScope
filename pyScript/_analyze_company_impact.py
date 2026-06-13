"""
分析每家公司对整体数据生态的依赖度
返回一个排序列表: 删除影响最小(孤立节点) → 影响大(多表引用)
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv; load_dotenv()
from collector_core import CollectorCore

core = CollectorCore()

def fetch_all(table, cols="*", extra_condition=""):
    rows = []
    offset, batch = 0, 500
    while True:
        q = core.db.table(table).select(cols).order("id").range(offset, offset+batch-1)
        r = q.execute()
        if not r.data: break
        rows.extend(r.data)
        offset += batch
        if len(r.data) < batch: break
    return rows

print("加载所有表...")
companies  = fetch_all("companies", "id,name,name_en,description,logo_url,website_url,total_funding_est_usd,industry_chain,tags,is_listed,draft")
patents    = fetch_all("patents", "id,related_company_id,applicant")
funding    = fetch_all("funding_events", "id,company_id,company_name")
products   = fetch_all("products", "id,company_id")
news       = fetch_all("news", "id,mentioned_company_ids")
try:
    aliases    = fetch_all("company_aliases", "id,company_id,alias_name")
except:
    aliases = []

# 构建引用索引
company_ids = {c["id"] for c in companies}
patent_refs  = {}  # company_id → count
funding_refs = {}
product_refs = {}
news_refs    = {}
alias_refs   = {}

for p in patents:
    cid = p.get("related_company_id")
    if cid:
        patent_refs[cid] = patent_refs.get(cid, 0) + 1

for f in funding:
    cid = f.get("company_id")
    if cid:
        funding_refs[cid] = funding_refs.get(cid, 0) + 1

for p in products:
    cid = p.get("company_id")
    if cid:
        product_refs[cid] = product_refs.get(cid, 0) + 1

for n in news:
    ids = n.get("mentioned_company_ids") or []
    for cid in ids:
        news_refs[cid] = news_refs.get(cid, 0) + 1

for a in aliases:
    cid = a.get("company_id")
    if cid:
        alias_refs[cid] = alias_refs.get(cid, 0) + 1

# 分析每家公司
results = []
for c in companies:
    cid = c["id"]
    name = c.get("name","")[:50]
    refs = {
        "patents": patent_refs.get(cid, 0),
        "funding": funding_refs.get(cid, 0),
        "products": product_refs.get(cid, 0),
        "news": news_refs.get(cid, 0),
        "aliases": alias_refs.get(cid, 0),
    }
    total_refs = sum(refs.values())
    
    # 元数据丰富度评分
    richness = 0
    if c.get("description") and len(c["description"])>20: richness += 1
    if c.get("logo_url"): richness += 1
    if c.get("website_url") and "http" in str(c.get("website_url","")): richness += 1
    if c.get("total_funding_est_usd"): richness += 1
    if c.get("tags") and len(c.get("tags",[]))>0: richness += 1
    if c.get("industry_chain"): richness += 1
    if c.get("is_listed"): richness += 1
    
    results.append({
        "id": cid,
        "name": name,
        "refs": refs,
        "total_refs": total_refs,
        "richness": richness,
        "draft": c.get("draft", False),
        "name_en": c.get("name_en",""),
        "description": (c.get("description") or "")[:80],
    })

# 按影响度排序 (total_refs 越低越安全)
results.sort(key=lambda x: (x["total_refs"], -x["richness"]))

# 分层统计
zero_refs = [r for r in results if r["total_refs"] == 0]
one_ref   = [r for r in results if r["total_refs"] == 1]
few_refs  = [r for r in results if 2 <= r["total_refs"] <= 5]
high_refs = [r for r in results if r["total_refs"] > 5]

print(f"\n{'='*60}")
print(f"  企业删除影响分析")
print(f"{'='*60}")
print(f"  总企业数:     {len(companies)}")
print(f"  零引用(安全删除):  {len(zero_refs)}")
print(f"  仅1个引用:    {len(one_ref)}")
print(f"  2-5个引用:    {len(few_refs)}")
print(f"  6+引用(核心):  {len(high_refs)}")
print(f"  已draft:      {sum(1 for r in results if r['draft'])}")

# 零引用企业详情
print(f"\n{'─'*60}")
print(f"  零引用企业 (删除无任何影响) — 前30条:")
print(f"{'─'*60}")
for r in zero_refs[:30]:
    draft_tag = "[draft]" if r["draft"] else ""
    rich = "★"*r["richness"]
    print(f"  {draft_tag} [{rich}] {r['name'][:55]} {r.get('description','')[:50]}")

# 零引用 + 元数据极低 (richness<=1)
bare_zero = [r for r in zero_refs if r["richness"] <= 1]
print(f"\n  零引用 + 无元数据 (最安全删除): {len(bare_zero)} 条")

# 保存完整报告
import json
report_path = os.path.join(os.path.dirname(__file__), "_company_impact_report.json")
with open(report_path, "w", encoding="utf-8") as f:
    json.dump({
        "summary": {
            "total": len(companies),
            "zero_refs": len(zero_refs),
            "one_ref": len(one_ref),
            "few_refs": len(few_refs),
            "high_refs": len(high_refs),
            "bare_zero": len(bare_zero),
        },
        "details": results
    }, f, ensure_ascii=False, indent=2)

print(f"\n  完整报告: {report_path}")
