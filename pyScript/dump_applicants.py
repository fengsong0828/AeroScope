"""
从 patents 表提取申请人 → 按原始名称分组的 JSON
不做任何清洗/去重/翻译，完全一致的 applicant 归到一组
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv; load_dotenv()
from collector_core import CollectorCore

core = CollectorCore()

print("查询全部专利...")
all_patents = []
offset, batch = 0, 500
while True:
    r = core.db.table("patents").select("id,patent_number,title,applicant,application_date") \
        .order("id").range(offset, offset + batch - 1).execute()
    if not r.data:
        break
    all_patents.extend(r.data)
    offset += batch
    if len(r.data) < batch:
        break

print(f"共 {len(all_patents)} 条专利")

# 按 applicant 完全一致分组
grouped = {}
for p in all_patents:
    applicant = (p.get("applicant") or "").strip()
    if not applicant:
        applicant = "(无申请人)"
    grouped.setdefault(applicant, []).append({
        "id": p["id"],
        "patent_number": p.get("patent_number", ""),
        "title": p.get("title", ""),
        "application_date": p.get("application_date", ""),
    })

# 按专利数量降序排列
sorted_groups = dict(sorted(grouped.items(), key=lambda x: -len(x[1])))

out_path = r"D:\AI大模型应用\Aeroscope\Agent矩阵\agents\patent\patent_applicants_raw.json"

with open(out_path, "w", encoding="utf-8") as f:
    json.dump(sorted_groups, f, ensure_ascii=False, indent=2)

print(f"申请人种类: {len(sorted_groups)}")
print(f"已写入: {out_path}")
