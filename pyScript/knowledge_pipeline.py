"""
AeroScope Knowledge Pipeline
专利 → 企业 → 产品，链式知识提取

Phase 1: 从专利库提取所有申请人 → 创建/更新企业记录
Phase 2: 对企业做低空关键词匹配 → 筛选目标企业
Phase 3: 从专利标题/摘要提取产品信息 → 创建产品记录
Phase 4: 企业反查专利 → 补充缺失的专利数

用法:
  python pyScript/knowledge_pipeline.py
  python pyScript/knowledge_pipeline.py --company "亿航智能"
"""
import os, sys, re, time
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv; load_dotenv()
from collector_core import CollectorCore
from llm_prompts import COMPANY_PROMPT
import requests as http_requests

# 低空产品关键词
PRODUCT_KEYWORDS = [
    "eVTOL", "飞行器", "无人机", "多旋翼", "倾转旋翼", "复合翼", "飞翼",
    "垂直起降", "空中出租车", "物流无人机", "载人飞行器", "自动驾驶飞行器",
    "EH216", "V1500M", "V2000CG", "X2", "旅航者", "盛世龙", "峰飞",
    "电动垂直起降", "涵道风扇", "飞行汽车",
    "drone", "UAV", "aircraft", "multicopter", "tiltrotor", "air taxi",
    "VTOL", "UAM", "cargo drone", "passenger drone"
]

LOWALT_CHAIN = ["上游-原材料", "上游-核心零部件", "中游-分系统", "中游-整机制造", "下游-运营服务", "下游-飞行保障", "其他-待审核"]


class KnowledgePipeline(CollectorCore):
    """知识管线：专利驱动企业/产品图谱"""

    def __init__(self):
        super().__init__()
        self.stats = {"companies": 0, "products": 0}

    # ─── Phase 1: 专利 → 企业 ───
    def extract_companies_from_patents(self, limit=500):
        """从专利库提取所有申请人，创建企业记录"""
        print("\n" + "=" * 50)
        print("  Phase 1: Patents → Companies")
        print("=" * 50)

        # 获取所有不同申请人
        r = self.db.table("patents").select("applicant").neq("applicant", "null").limit(limit).execute()
        if not r.data:
            return

        applicants = {}
        for p in r.data:
            names = re.split(r'[;；]', p.get("applicant", ""))
            for name in names:
                name = name.strip()
                if len(name) >= 4:
                    applicants[name] = applicants.get(name, 0) + 1

        sorted_apps = sorted(applicants.items(), key=lambda x: -x[1])
        print(f"  Unique applicants: {len(sorted_apps)}")

        for name, count in sorted_apps[:100]:
            # 检查是否已存在
            existing = self.db.table("companies").select("id").ilike("name", f"%{name[:6]}%").limit(1).execute()
            if existing.data:
                continue

            # 判断是否是机构（非个人）
            if not self._is_org(name):
                continue

            # LLM 提取企业信息
            llm_raw = self.call_llm(COMPANY_PROMPT, f"企业名称: {name}\n该企业在低空经济领域有 {count} 项专利")
            data = self.parse_llm_json(llm_raw)
            if data and data.get("name"):
                chain = data.get("industry_chain", "")
                cat = data.get("primary_category", "")
                if chain or cat:
                    data["draft"] = False
                    self.upsert("companies", data, "name")
                    self.stats["companies"] += 1
                    print(f"  🏢 {data['name'][:40]} ({cat})")
            time.sleep(0.3)

        print(f"  Companies created: {self.stats['companies']}")

    # ─── Phase 2: 企业关联专利计数 ───
    def link_company_patents(self):
        """为每家企业统计关联专利数并更新"""
        print("\n" + "=" * 50)
        print("  Phase 2: Link Companies ← Patents")
        print("=" * 50)

        r = self.db.table("companies").select("id,name").execute()
        if not r.data:
            return

        for co in r.data:
            name = co.get("name", "")[:10]
            if not name:
                continue
            # 统计 applicant 匹配的专利数
            pr = self.db.table("patents").select("id", count="exact").ilike("applicant", f"%{name}%").execute()
            count = pr.count
            if count > 0:
                print(f"  {co['name'][:30]}: {count} patents")
            time.sleep(0.1)
        print(f"  Done")

    # ─── Phase 3: 专利 → 产品 ───
    def extract_products_from_patents(self, company_name=None):
        """从专利标题/摘要中提取产品信息"""
        print("\n" + "=" * 50)
        print(f"  Phase 3: Patents → Products ({company_name or 'all'})")
        print("=" * 50)

        query = self.db.table("patents").select("id,title,abstract,applicant,related_company_id").limit(200)
        if company_name:
            query = query.ilike("applicant", f"%{company_name}%")

        r = query.execute()
        if not r.data:
            print("  No patents to process")
            return

        for p in r.data[:50]:
            title = p.get("title", "")
            abstract = p.get("abstract", "")

            # 判断是否包含产品关键词
            text = f"{title} {abstract}"
            matched = [kw for kw in PRODUCT_KEYWORDS if kw.lower() in text.lower()]
            if not matched:
                continue

            # 尝试提取产品名
            product_name = self._extract_product_name(title)
            if not product_name:
                continue

            cid = p.get("related_company_id")
            if not cid:
                continue

            record = {
                "name": product_name,
                "company_id": cid,
                "draft": False,
                "spec_range_km": "",
                "propulsion": "Electric" if any(k in text for k in ["电动", "electric"]) else ""
            }

            try:
                self.upsert("products", record, "name")
                self.stats["products"] += 1
                print(f"  📦 {product_name} (keyword: {matched[0]})")
            except:
                pass
            time.sleep(0.1)

        print(f"  Products created: {self.stats['products']}")

    def _extract_product_name(self, title):
        """从专利标题提取产品名称"""
        patterns = [
            r'(EH\d{3}[A-Za-z]?)',  # EH216-S
            r'(V\d{4}[A-Za-z]?\d*)', # V1500M
            r'([A-Z]\d{1,2}[A-Za-z]?)', # X2
            r'([\u4e00-\u9fff]{2,4}者)', # 旅航者
            r'([\u4e00-\u9fff]{2,3}龙)', # 盛世龙
        ]
        for pat in patterns:
            m = re.search(pat, title)
            if m:
                return m.group(1)
        return None

    def _is_org(self, name):
        """判断名称是否为机构（非个人）"""
        org_suffixes = ["公司", "有限", "集团", "研究院", "大学", "学院", "实验室",
                        "中心", "所", "局", "部", "厂", "Inc", "Ltd", "Co", "GmbH"]
        return any(s in name for s in org_suffixes)

    # ─── 汇总报告 ───
    def report(self):
        print("\n" + "=" * 50)
        print("  Knowledge Pipeline Report")
        print("=" * 50)

        rp = self.db.table("patents").select("id", count="exact").execute()
        rc = self.db.table("companies").select("id", count="exact").execute()
        rpr = self.db.table("products").select("id", count="exact").execute()

        print(f"  Patents:   {rp.count}")
        print(f"  Companies: {rc.count}")
        print(f"  Products:  {rpr.count}")

        # 企业-专利关联度
        linked = self.db.table("patents").select("id", count="exact").neq("related_company_id", "null").execute()
        print(f"  Linked patents: {linked.count}/{rp.count}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--company", help="Target company name (optional)")
    args = parser.parse_args()

    pipe = KnowledgePipeline()
    pipe.extract_companies_from_patents(limit=500)
    pipe.link_company_patents()
    pipe.extract_products_from_patents(args.company)
    pipe.report()
