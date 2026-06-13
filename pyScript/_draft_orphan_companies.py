"""将零引用+无元数据的空壳企业批量标记为 draft"""
import sys, os, json
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv; load_dotenv()
from collector_core import CollectorCore

core = CollectorCore()
report_path = os.path.join(os.path.dirname(__file__), "_company_impact_report.json")
with open(report_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# 筛选: total_refs==0 AND richness<=1
to_draft = [r for r in data["details"] if r["total_refs"] == 0 and r["richness"] <= 1]
print(f"待标记为 draft: {len(to_draft)} 条")

batch = 50
for i in range(0, len(to_draft), batch):
    chunk = to_draft[i:i+batch]
    ids = [r["id"] for r in chunk]
    # 已有 draft=True 的跳过
    try:
        core.db_write.table("companies").update({"draft": True}).in_("id", ids).execute()
        print(f"  [{i+1}-{min(i+batch, len(to_draft))}] 已标记 {len(ids)} 条")
    except Exception as e:
        print(f"  [ERR] {e}")

print(f"\n完成! 已标记 {len(to_draft)} 条为 draft")
