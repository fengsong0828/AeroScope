"""
AeroScope Patent <-> Company Bi-directional Linker
"""
import sys, os, re, time, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pyScript"))
from dotenv import load_dotenv; load_dotenv()
from collector_core import CollectorCore
from llm_prompts import COMPANY_PROMPT


def normalize_name(name):
    """标准化企业名称，用于模糊匹配"""
    if not name:
        return ""
    n = name.strip()
    # 去掉常见后缀
    suffixes = [
        "股份有限公司", "有限责任公司", "有限公司", "有限合伙", "集团",
        "（深圳）", "（昆山）", "（北京）", "（上海）", "（广州）", "（成都）",
        "(深圳)", "(昆山)", "(北京)", "(上海)", "(广州)", "(成都)",
        "科技", "技术", "信息", "通信"
    ]
    for s in suffixes:
        n = n.replace(s, "")
    # 去括号和空格
    n = re.sub(r'[（(].*?[）)]', '', n)
    n = re.sub(r'\s+', '', n)
    return n.strip()


def match_company(applicant, companies_map):
    """尝试在企业映射表中匹配申请人"""
    if not applicant or not companies_map:
        return None

    norm_app = normalize_name(applicant)
    if not norm_app or len(norm_app) < 2:
        return None

    # 精确匹配
    for name, (cid, full_name) in companies_map.items():
        if applicant == full_name or name == applicant:
            return cid

    # 标准化匹配
    for name, (cid, full_name) in companies_map.items():
        if normalize_name(name) == norm_app:
            return cid

    # 包含匹配
    for name, (cid, full_name) in companies_map.items():
        if norm_app in normalize_name(name) or normalize_name(name) in norm_app:
            return cid

    return None


def build_companies_map(core):
    """从数据库构建企业名→ID映射"""
    r = core.db.table("companies").select("id,name").execute()
    if not r.data:
        return {}
    return {c["name"]: (c["id"], c["name"]) for c in r.data}


def link_patent_to_company(core, patent, companies_map, new_created):
    """将单个专利关联到企业，必要时创建新企业"""
    applicant = patent.get("applicant", "").strip()
    patent_id = patent.get("id")

    if not applicant or not patent_id:
        return

    # 已有关联，跳过
    if patent.get("related_company_id"):
        return

    # 尝试匹配
    cid = match_company(applicant, companies_map)
    if cid:
        core.db.table("patents").update({"related_company_id": cid}).eq("id", patent_id).execute()
        print(f"  [LINK] {applicant[:30]} → 企业ID {cid}")
        return

    # 没有匹配 → AI 提取企业信息并创建
    print(f"  [NEW] 新企业: {applicant[:40]}")
    llm_raw = core.call_llm(COMPANY_PROMPT, f"企业名称: {applicant}")
    data = core.parse_llm_json(llm_raw)

    if data and data.get("name"):
        name = data["name"].strip()
        if name in new_created:
            return  # 避免同一批次重复创建
        ok = core.upsert("companies", data, "name")
        if ok:
            new_created.add(name)
            companies_map[name] = (None, name)  # ID 后续更新
            # 重新获取公司 ID 并更新专利
            time.sleep(0.5)
            r = core.db.table("companies").select("id").eq("name", name).execute()
            if r.data:
                cid = r.data[0]["id"]
                core.db.table("patents").update({"related_company_id": cid}).eq("id", patent_id).execute()
                companies_map[name] = (cid, name)
                print(f"    [OK] 企业创建+关联成功")


def run_linker():
    """主入口：遍历所有未关联的专利，建立企业关联"""
    core = CollectorCore()
    if not core.db:
        print("数据库连接失败")
        return

    print("=" * 60)
    print("  Patent <-> Company Linker")
    print("=" * 60)

    # 1. 获取所有企业映射
    companies_map = build_companies_map(core)
    print(f"\nExisting companies: {len(companies_map)}")

    # 2. Get all patents
    patents = core.db.table("patents").select("id,applicant,title,related_company_id").execute()
    if not patents.data:
        print("No patent data")
        return

    unlinked = [p for p in patents.data if not p.get("related_company_id")]
    total = len(patents.data)
    print(f"Total patents: {total}")
    print(f"Already linked: {total - len(unlinked)}")
    print(f"Need linking: {len(unlinked)}")

    if not unlinked:
        print("\nAll patents already linked!")
        return

    # 3. Link one by one
    new_created = set()
    linked_count = 0
    for i, patent in enumerate(unlinked):
        try:
            link_patent_to_company(core, patent, companies_map, new_created)
            linked_count += 1
            time.sleep(0.3)
        except Exception as e:
            print(f"  [ERR] {patent.get('applicant','?')[:30]}: {str(e)[:80]}")

    print(f"\nLinked: {linked_count} patents")
    print(f"New companies created: {len(new_created)}")


if __name__ == "__main__":
    run_linker()
