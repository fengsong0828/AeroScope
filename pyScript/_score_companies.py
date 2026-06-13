"""
企业质量评分 — 多维加权排名
输出: S/A/B/C/D 五级分类
"""
import sys, os, re, json
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv; load_dotenv()
from collector_core import CollectorCore

core = CollectorCore()

def fetch_all(table, cols="*"):
    rows, offset, batch = [], 0, 500
    while True:
        r = core.db.table(table).select(cols).order("id").range(offset, offset+batch-1).execute()
        if not r.data: break
        rows.extend(r.data)
        offset += batch
        if len(r.data) < batch: break
    return rows

print("加载数据...")
companies = fetch_all("companies", "id,name,name_en,description,logo_url,website_url,total_funding_est_usd,industry_chain,industry_chain_sub,tags,is_listed,draft,primary_category,country_code,location,founded_year")
patents   = fetch_all("patents", "id,related_company_id,applicant")
funding   = fetch_all("funding_events", "id,company_id")
products  = fetch_all("products", "id,company_id")
news_data = fetch_all("news", "id,mentioned_company_ids")

# 引用计数
refs = {}
for p in patents:
    cid = p.get("related_company_id")
    if cid: refs.setdefault(cid, {"patents":0,"funding":0,"products":0,"news":0})["patents"] += 1
for f in funding:
    cid = f.get("company_id")
    if cid: refs.setdefault(cid, {"patents":0,"funding":0,"products":0,"news":0})["funding"] += 1
for p in products:
    cid = p.get("company_id")
    if cid: refs.setdefault(cid, {"patents":0,"funding":0,"products":0,"news":0})["products"] += 1
for n in news_data:
    for cid in (n.get("mentioned_company_ids") or []):
        refs.setdefault(cid, {"patents":0,"funding":0,"products":0,"news":0})["news"] += 1

def has_chinese(s): return bool(re.search(r'[\u4e00-\u9fff]', s or ""))

def is_person_name(name):
    """判断是否像个人姓名（非企业）"""
    if not name: return False
    # 纯英文短名
    eng = re.findall(r'[A-Za-z]+', name)
    if len(eng) == 2 and all(len(w) < 15 for w in eng):
        return True
    # 纯中文 2-4 字且无公司后缀
    org_suffix = ["公司","有限","集团","大学","学院","研究院","实验室","中心","所","厂","局","部"]
    if has_chinese(name) and len(name) <= 4 and not any(s in name for s in org_suffix):
        return True
    # 含 "Individual" 或 "个人"
    if "individual" in name.lower() or "个人" in name:
        return True
    return False

# 评分
results = []
for c in companies:
    if c.get("draft"): continue  # 跳过已废弃
    cid = c["id"]
    name = c.get("name","").strip()
    r = refs.get(cid, {"patents":0,"funding":0,"products":0,"news":0})
    total_refs = sum(r.values())

    score = 0
    reasons = []

    # 引用分 (最高 25)
    if r["patents"] >= 10:     score += 10; reasons.append("专利≥10")
    elif r["patents"] >= 3:    score += 7;  reasons.append("专利3-9")
    elif r["patents"] >= 1:    score += 4;  reasons.append("专利1-2")
    if r["funding"] >= 1:      score += 8;  reasons.append("有融资")
    if r["products"] >= 1:     score += 4;  reasons.append("有产品")
    if r["news"] >= 1:         score += 3;  reasons.append("被新闻提及")

    # 名称质量 (最高 15)
    if has_chinese(name) and len(name) >= 6: score += 8; reasons.append("中文全名")
    elif has_chinese(name):                  score += 5; reasons.append("中文短名")
    if c.get("name_en"):                     score += 3; reasons.append("有英文名")
    if is_person_name(name):                 score -= 10; reasons.append("疑似个人")
    if not any(kw in (name+ (c.get("name_en") or "")).lower() for kw in ("drone","uav","evtol","aerial","aviation","航空","飞行","无人机","航","空中")):
        if r["patents"] < 1 and r["funding"] < 1:
            score -= 5; reasons.append("非航空领域")

    # 元数据丰富度 (最高 15)
    if c.get("description") and len(c["description"])>30:  score += 5; reasons.append("有详情")
    elif c.get("description") and "系统自动收录" not in c["description"]: score += 2
    if c.get("logo_url"):                                   score += 3; reasons.append("有Logo")
    if c.get("website_url") and "http" in str(c.get("website_url","")): score += 3; reasons.append("有网站")
    if c.get("total_funding_est_usd"):                      score += 2; reasons.append("有融资额")
    if c.get("tags") and len(c.get("tags",[]))>0:           score += 2; reasons.append("有标签")

    # 产业链分类 (最高 10)
    if c.get("industry_chain") in ("upstream","midstream","downstream"):
        score += 6; reasons.append("产业链明确")
    elif c.get("industry_chain_sub"):
        score += 3
    if c.get("primary_category"):                           score += 2; reasons.append("有主分类")
    if c.get("country_code"):                               score += 2

    # 上市/知名
    if c.get("is_listed"):                                  score += 5; reasons.append("已上市")

    # 分级
    if   score >= 30: tier = "S"
    elif score >= 20: tier = "A"
    elif score >= 10: tier = "B"
    elif score >= 0:  tier = "C"
    else:             tier = "D"

    results.append({
        "id": cid, "name": name[:60], "tier": tier, "score": score,
        "refs": r, "reasons": reasons,
        "industry_chain": c.get("industry_chain",""),
        "primary_category": c.get("primary_category",""),
        "description": (c.get("description") or "")[:80],
    })

results.sort(key=lambda x: -x["score"])

# 统计
tiers = {}
for r in results:
    tiers.setdefault(r["tier"], 0)
    tiers[r["tier"]] += 1

print(f"\n{'='*55}")
print(f"  企业质量评级 (排除 draft 后)")
print(f"{'='*55}")
print(f"  S级 (≥30分, 核心企业):     {tiers.get('S',0)}")
print(f"  A级 (20-29分, 优质企业):    {tiers.get('A',0)}")
print(f"  B级 (10-19分, 可信企业):    {tiers.get('B',0)}")
print(f"  C级 (0-9分, 信息不完整):    {tiers.get('C',0)}")
print(f"  D级 (<0分, 建议删除):       {tiers.get('D',0)}")

# S级样例
print(f"\n── S级核心企业 (前15) ──")
s_list = [r for r in results if r["tier"] == "S"]
for r in s_list[:15]:
    print(f"  [{r['score']}分] {r['name'][:50]} | {', '.join(r['reasons'][:4])}")

# D级样例
print(f"\n── D级建议删除 (前15) ──")
d_list = [r for r in results if r["tier"] == "D"]
for r in d_list[:15]:
    print(f"  [{r['score']}分] {r['name'][:50]} | {', '.join(r['reasons'][:4])}")

# 保存报告
out = os.path.join(os.path.dirname(__file__), "_company_quality_report.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump({"tiers": tiers, "results": results}, f, ensure_ascii=False, indent=2)
print(f"\n  完整报告: {out}")
