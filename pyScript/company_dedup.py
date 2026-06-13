"""
AeroScope 企业名称去重 + 别名自动构建
=====================================
功能:
  1. 扫描 companies 表全部记录
  2. 四层匹配检测重复企业:
     L1: 精确名称匹配 (已有 auditor 处理)
     L2: 标准化后匹配 (去后缀/去括号/去空格)
     L3: 包含关系匹配 (A 包含 B 或 B 包含 A)
     L4: 英文名 ↔ 中文名交叉匹配
  3. 生成 company_aliases 记录
  4. 输出 JSON 报告供人工审阅
  5. --apply 参数确认后写入 DB

用法:
  python company_dedup.py                 # 预览模式，仅输出报告
  python company_dedup.py --apply         # 预览 + 写入别名表
  python company_dedup.py --apply --draft  # 预览 + 写入别名 + draft 重复记录
"""
import sys, os, re, json, time
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv; load_dotenv()
from collector_core import CollectorCore


def normalize(name: str) -> str:
    """标准化：去括号内容 + 去法人后缀 + 去空格 -> 保留核心主干"""
    if not name:
        return ""
    n = name.strip()
    n = re.sub(r'[（(].*?[）)]', '', n)                          # 去括号内容
    n = re.sub(r'股份?有限公司$|有限(责任)?公司$|有限合伙$', '', n)   # 去中文法人后缀
    n = re.sub(r'集团(有限)?公司$|企业$', '', n)
    n = re.sub(r'\s+(Inc\.?|Ltd\.?|LLC|Corp\.?|GmbH|Co\.,?\s*Ltd\.?|PLC)$', '', n, flags=re.I)  # 去英文法人后缀
    n = re.sub(r'\s+', '', n)                                     # 去所有空格
    if len(n) < 2:
        return name.strip()
    return n.lower()


def clean_en(name: str) -> str:
    """英文名清洗：去括号、去空格、统一大小写"""
    if not name:
        return ""
    n = re.sub(r'[（(].*?[）)]', '', name.strip())
    n = re.sub(r'\s+', '', n)
    return n.lower()


def fuzzy_score(a: str, b: str) -> float:
    """简单相似度评分（基于最长公共子序列比率）"""
    if not a or not b:
        return 0.0
    # 动态规划 LCS 长度
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if a[i-1] == b[j-1]:
                dp[i][j] = dp[i-1][j-1] + 1
            else:
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])
    lcs = dp[m][n]
    return (2 * lcs) / (len(a) + len(b)) if (len(a) + len(b)) > 0 else 0


def extract_chinese(name: str) -> str:
    """从名称中提取纯中文部分"""
    return ''.join(re.findall(r'[\u4e00-\u9fff]', name))


def extract_alpha(name: str) -> str:
    """从名称中提取纯英文/数字部分"""
    return ''.join(re.findall(r'[A-Za-z0-9]', name))


# ─── 主逻辑 ───
class CompanyDeduplicator:
    def __init__(self, apply_mode=False, draft_duplicates=False):
        self.core = CollectorCore()
        self.apply = apply_mode
        self.draft_duplicates = draft_duplicates
        self.companies = []
        self.groups = []       # 去重组: [{canonical: {}, duplicates: [], method: str}]
        self.aliases = []      # 待写入的别名记录

    def load_companies(self):
        """从 DB 加载所有非 draft 企业"""
        print("加载企业数据...")
        offset, batch = 0, 500
        while True:
            r = self.core.db.table("companies").select("*").eq("draft", False) \
                .order("id").range(offset, offset + batch - 1).execute()
            if not r.data:
                break
            self.companies.extend(r.data)
            offset += batch
            if len(r.data) < batch:
                break
        print(f"  加载 {len(self.companies)} 家企业")

    def _find_group(self, idx_to_group: dict):
        """将索引映射到分组"""
        for cid, g in enumerate(self.groups):
            for dup in g["duplicates"]:
                if dup["id"] in idx_to_group:
                    return cid
        return -1

    def detect_level2_normalized(self):
        """L2: 标准化名称匹配 —— 去后缀后完全一致的即视为同一企业"""
        print("\n[L2] 标准化名称匹配...")
        norm_map = {}  # norm_name -> [company dict, ...]
        for c in self.companies:
            n = normalize(c.get("name", ""))
            if not n or len(n) < 3:
                continue
            norm_map.setdefault(n, []).append(c)

        found = 0
        for norm, items in norm_map.items():
            if len(items) < 2:
                continue
            if len({c.get("name", "").strip().lower() for c in items}) < 2:
                continue  # 名字完全一样的不算(已由 auditor 处理)

            canonical = max(items, key=lambda c: len(c.get("description") or ""))
            duplicates = [c for c in items if c["id"] != canonical["id"]]
            self.groups.append({
                "canonical": canonical,
                "duplicates": duplicates,
                "method": "L2_normalized",
                "norm_name": norm,
            })
            found += 1

        print(f"  发现 {found} 组标准化匹配 (共 {sum(len(g['duplicates']) for g in self.groups) - found + len(self.groups)} 条记录)")

    def detect_level3_containment(self):
        """L3: 包含关系匹配 —— A 的核心名包含在 B 的核心名中"""
        print("\n[L3] 包含关系匹配...")
        # 按名称长度升序排列，短名包含在长名中的优先合并
        sorted_cos = sorted(self.companies, key=lambda c: len(c.get("name", "")))

        already = set()
        for g in self.groups:
            already.add(g["canonical"]["id"])
            for d in g["duplicates"]:
                already.add(d["id"])

        found = 0
        for i, short in enumerate(sorted_cos):
            if short["id"] in already:
                continue
            s_name = normalize(short.get("name", ""))
            if len(s_name) < 4:
                continue
            for j, long in enumerate(sorted_cos):
                if i == j or long["id"] in already:
                    continue
                l_name = normalize(long.get("name", ""))
                # 短名完整出现在长名中
                if s_name in l_name and l_name != s_name:
                    canonical = long if len(long.get("description") or "") > len(short.get("description") or "") else short
                    dup = short if canonical["id"] == long["id"] else long
                    self.groups.append({
                        "canonical": canonical,
                        "duplicates": [dup],
                        "method": "L3_containment",
                    })
                    already.add(canonical["id"])
                    already.add(dup["id"])
                    found += 1
                    break

        print(f"  发现 {found} 组包含匹配")

    def detect_level4_cross_lang(self):
        """L4: 英文名与中文名交叉匹配 —— name_en 模糊匹配其他企业的 name"""
        print("\n[L4] 中英文交叉匹配...")
        # 构建英文名索引
        en_companies = [c for c in self.companies if c.get("name_en") and len(c["name_en"].strip()) > 3]

        already = set()
        for g in self.groups:
            already.add(g["canonical"]["id"])
            for d in g["duplicates"]:
                already.add(d["id"])

        found = 0
        for c_en in en_companies:
            if c_en["id"] in already:
                continue
            en_name = clean_en(c_en["name_en"])
            en_core = ''.join(re.findall(r'[A-Za-z]+', en_name))[:30]

            for c_cn in self.companies:
                if c_cn["id"] == c_en["id"] or c_cn["id"] in already:
                    continue
                cn_name = c_cn.get("name", "")
                cn_core = extract_chinese(cn_name)

                # 简单规则: 英文名核心部分被包含在中文名拼音中
                # 这里用模糊相似度做兜底
                if fuzzy_score(en_core.lower(), cn_name.lower()) > 0.5:
                    self.groups.append({
                        "canonical": c_cn,
                        "duplicates": [c_en],
                        "method": "L4_cross_lang",
                    })
                    already.add(c_cn["id"])
                    already.add(c_en["id"])
                    found += 1
                    break

                # 常见场景: 中文名是英文名的翻译
                # "EHang Intelligent Equipment" <-> "亿航智能设备(广州)有限公司"
                alpha_from_cn = extract_alpha(cn_name).lower()
                alpha_from_en = extract_alpha(c_en.get("name_en", "")).lower()
                if len(alpha_from_cn) > 2 and len(alpha_from_en) > 2:
                    if alpha_from_cn in alpha_from_en or alpha_from_en in alpha_from_cn:
                        self.groups.append({
                            "canonical": c_cn,
                            "duplicates": [c_en],
                            "method": "L4_alpha_match",
                        })
                        already.add(c_cn["id"])
                        already.add(c_en["id"])
                        found += 1
                        break

        print(f"  发现 {found} 组中英文交叉匹配")

    def build_aliases(self):
        """根据去重组生成别名记录"""
        print("\n构建别名记录...")
        for g in self.groups:
            canonical_id = g["canonical"]["id"]
            canonical_name = g["canonical"]["name"]
            for dup in g["duplicates"]:
                dup_name = dup.get("name", "")
                if dup_name and dup_name.strip().lower() != canonical_name.strip().lower():
                    self.aliases.append({
                        "company_id": canonical_id,
                        "alias_name": dup_name.strip(),
                        "source": g["method"],
                    })
                # 英文名也加入别名
                dup_en = dup.get("name_en", "")
                if dup_en and dup_en.strip():
                    self.aliases.append({
                        "company_id": canonical_id,
                        "alias_name": dup_en.strip(),
                        "source": f"{g['method']}_name_en",
                    })

    def generate_report(self) -> dict:
        """生成去重报告"""
        report = {
            "total_companies": len(self.companies),
            "total_groups": len(self.groups),
            "total_duplicates": sum(len(g["duplicates"]) for g in self.groups),
            "total_aliases": len(self.aliases),
            "groups": [],
        }

        for g in self.groups:
            report["groups"].append({
                "method": g["method"],
                "canonical": {
                    "id": g["canonical"]["id"],
                    "name": g["canonical"]["name"],
                    "name_en": g["canonical"].get("name_en", ""),
                },
                "duplicates": [
                    {"id": d["id"], "name": d["name"], "name_en": d.get("name_en", "")}
                    for d in g["duplicates"]
                ],
            })

        return report

    def apply(self):
        """写入别名表 + 标记重复企业为 draft"""
        if not self.apply:
            print("\n[预览模式] 以下为将要执行的变更 (加 --apply 执行):")
            return

        print("\n写入别名表...")
        alias_count = 0
        for a in self.aliases:
            try:
                # 检查别名是否已存在
                ex = self.core.db.table("company_aliases") \
                    .select("id").eq("company_id", a["company_id"]) \
                    .eq("alias_name", a["alias_name"]).execute()
                if ex.data:
                    continue
                self.core.db_write.table("company_aliases").insert(a).execute()
                alias_count += 1
            except Exception as e:
                print(f"  [ERR] 别名写入失败: {a['alias_name'][:30]} → {e}")

        print(f"  写入 {alias_count} 条别名")

        if self.draft_duplicates:
            print("\n标记重复企业为 draft...")
            draft_count = 0
            marked = set()
            for g in self.groups:
                for dup in g["duplicates"]:
                    dup_id = dup["id"]
                    if dup_id in marked:
                        continue
                    try:
                        self.core.db_write.table("companies") \
                            .update({"draft": True}).eq("id", dup_id).execute()
                        draft_count += 1
                        marked.add(dup_id)
                    except Exception as e:
                        print(f"  [ERR] draft 标记失败: id={dup_id} → {e}")
            print(f"  标记 {draft_count} 条为 draft")

    def run(self):
        self.load_companies()
        self.detect_level2_normalized()
        self.detect_level3_containment()
        self.detect_level4_cross_lang()
        self.build_aliases()

        report = self.generate_report()

        # 输出报告
        print("\n" + "=" * 70)
        print(f"  去重报告")
        print("=" * 70)
        print(f"  总企业数:      {report['total_companies']}")
        print(f"  发现重复组:    {report['total_groups']}")
        print(f"  重复记录数:    {report['total_duplicates']}")
        print(f"  待写别名数:    {report['total_aliases']}")
        print("-" * 70)

        for g in report["groups"]:
            print(f"\n  [{g['method']}]")
            print(f"    主体: {g['canonical']['name']}")
            for d in g['duplicates']:
                print(f"    重复: {d['name']}")

        print("\n" + "=" * 70)

        # 保存 JSON 报告
        report_path = os.path.join(os.path.dirname(__file__), "company_dedup_report.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"  报告已保存: {report_path}")

        # 执行写入
        if self.apply:
            self.apply()
            print("\n  写入完成!")
        else:
            print("\n  [预览模式] 加 --apply 确认写入, 加 --apply --draft 同时标记重复")
            print(f"  python company_dedup.py --apply              # 仅写别名")
            print(f"  python company_dedup.py --apply --draft       # 写别名 + 标记重复为draft")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="AeroScope 企业名称去重")
    p.add_argument("--apply", action="store_true", help="写入数据库 (默认仅预览)")
    p.add_argument("--draft", action="store_true", help="将重复企业标记为 draft (需配合 --apply)")
    args = p.parse_args()

    dedup = CompanyDeduplicator(
        apply_mode=args.apply,
        draft_duplicates=args.draft
    )
    dedup.run()
