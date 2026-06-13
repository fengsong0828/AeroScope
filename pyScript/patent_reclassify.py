"""
AeroScope 专利分类回填脚本 v2.0
按固定 Skill 模板对存量专利逐条调用 LLM 重新分类，严格校验后写入。

核心流程:
  1. 从 DB 拉取待分类专利
  2. 拼装专利文本 → 调用 LLM (PATENT_PROMPT)
  3. 校验 LLM 输出是否在固定分类模板内（patent_classification_rules.py）
  4. 不在模板内的 → 归一化为 "其他-待审核"，扣减置信度
  5. 计算 classification_confidence → 写入 DB

用法:
  python pyScript/patent_reclassify.py --dry-run              # 预览模式，不写库
  python pyScript/patent_reclassify.py --max 50              # 最多处理50条
  python pyScript/patent_reclassify.py --only-unclassified   # 仅处理未分类的
  python pyScript/patent_reclassify.py --force               # 强制重分类全部
  python pyScript/patent_reclassify.py --resume              # 从上次中断处继续
  python pyScript/patent_reclassify.py --delay 1.5           # LLM调用间隔(秒)
"""
import os
import sys
import json
import time
import argparse
import re
from datetime import datetime, timezone
from typing import Optional

sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv; load_dotenv()
from collector_core import CollectorCore
from llm_prompts import PATENT_PROMPT
from patent_classification_rules import (
    TECH_CATEGORIES, INDUSTRY_CHAIN, APP_FIELDS,
    INNOVATION_LEVELS, TRL_LEVELS,
    get_all_tech_categories, get_all_tech_subcategories,
    get_all_chain_positions, get_all_app_fields,
    get_tech_category_by_sub
)

PROGRESS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
                             "agent-workspace", "data-engineer", "data-schemas",
                             "reclassify_progress.json")

# ─── 固定模板索引 ───
VALID_MAIN_CATS   = set(get_all_tech_categories())        # 11 个一级分类 (含 "其他-待审核")
VALID_SUB_CATS    = set(get_all_tech_subcategories())     # 50+ 个二级子类
VALID_CHAIN_POS   = set(get_all_chain_positions())        # 7 个产业链环节
VALID_APP_FIELDS  = set(get_all_app_fields())             # 13 个应用场景
VALID_INNOVATION  = set(INNOVATION_LEVELS.keys())         # {High, Medium, Low}
VALID_TRL         = set(range(1, 10))                     # 1-9


class PatentReclassify(CollectorCore):
    """专利分类回填执行器"""

    def __init__(self, dry_run=False, delay=1.0, skip_design=True):
        super().__init__()
        self.dry_run = dry_run
        self.delay = delay
        self.skip_design = skip_design
        self.stats = {"success": 0, "skipped": 0, "failed": 0, "unverified": 0}
        self.processed_ids = set()

    # ─── 1. 获取待分类专利 ───
    def fetch_patents(self, max_count=0, only_unclassified=False, force=False):
        """从 DB 拉取待处理的专利列表（默认排除外观设计）"""
        query = self.db.table("patents").select(
            "id,title,abstract,claims,description_summary,applicant,"
            "patent_number,patent_type,application_date,publication_date,"
            "technical_categories,technical_subcategory,industry_chain_position,"
            "application_fields,innovation_level,technology_maturity_level,"
            "is_verified"
        ).order("application_date", desc=True)

        # 排除外观设计（无技术文本，分类无意义）
        if self.skip_design:
            query = query.not_.ilike("patent_number", "%S")  # 设计专利号以S结尾

        if only_unclassified and not force:
            query = query.is_("technical_categories", "null")

        # 默认跳过已回填的专利（有 classification_confidence 说明 v2.0 已处理）
        if not force:
            query = query.is_("classification_confidence", "null")

        if max_count > 0:
            query = query.limit(max_count)

        r = query.execute()
        if not r.data:
            print("无待处理专利")
            return []

        print(f"获取到 {len(r.data)} 条专利")
        return r.data

    # ─── 2. 校验并归一化 LLM 输出 ───
    def validate_and_normalize(self, llm_data: dict, patent_text: str) -> dict:
        """
        严格校验 LLM 输出的每个字段是否在固定 Skill 模板内。
        不在模板 → 归一化为 "其他-待审核"，并扣减置信度。
        返回: {field: value, ..., classification_confidence: float}
        """
        confidence = 1.0
        result = {}

        # --- technical_categories (一级大类) ---
        raw_cats = llm_data.get("technical_categories", [])
        if isinstance(raw_cats, str):
            raw_cats = [raw_cats]
        normalized_cats = []
        for cat in raw_cats:
            cat = str(cat).strip()
            if not cat or cat in ("null", "None", ""):
                continue
            if cat in VALID_MAIN_CATS:
                normalized_cats.append(cat)
            else:
                # 尝试模糊匹配（子类反查、包含匹配）
                mapped = self._fuzzy_match_category(cat, VALID_MAIN_CATS)
                if mapped:
                    normalized_cats.append(mapped)
                    confidence -= 0.08
                else:
                    confidence -= 0.15
        if not normalized_cats:
            normalized_cats = ["其他-待审核"]
            confidence -= 0.25
        result["technical_categories"] = normalized_cats[:5]

        # --- technical_subcategory (二级子类) ---
        raw_sub = llm_data.get("technical_subcategory", "")
        if isinstance(raw_sub, list):
            raw_sub = raw_sub[0] if raw_sub else ""
        raw_sub = str(raw_sub).strip()
        if raw_sub and raw_sub not in ("null", "None", ""):
            if raw_sub in VALID_SUB_CATS:
                result["technical_subcategory"] = raw_sub
                # 如果一级分类未覆盖此子类所属大类，自动补充
                parent = get_tech_category_by_sub(raw_sub)
                if parent and parent not in result["technical_categories"]:
                    result["technical_categories"].append(parent)
            else:
                mapped = self._fuzzy_match_category(raw_sub, VALID_SUB_CATS)
                if mapped:
                    result["technical_subcategory"] = mapped
                    confidence -= 0.08
                    parent = get_tech_category_by_sub(mapped)
                    if parent and parent not in result["technical_categories"]:
                        result["technical_categories"].append(parent)
                else:
                    result["technical_subcategory"] = "待分类"
                    confidence -= 0.15
        else:
            result["technical_subcategory"] = "待分类"
            confidence -= 0.10

        # --- industry_chain_position ---
        raw_chain = llm_data.get("industry_chain_position", "")
        raw_chain = str(raw_chain).strip()
        if raw_chain in VALID_CHAIN_POS:
            result["industry_chain_position"] = raw_chain
        else:
            mapped = self._fuzzy_match_category(raw_chain, VALID_CHAIN_POS)
            if mapped:
                result["industry_chain_position"] = mapped
                confidence -= 0.08
            else:
                result["industry_chain_position"] = "其他-待审核"
                confidence -= 0.20

        # --- application_fields ---
        raw_apps = llm_data.get("application_fields", [])
        if isinstance(raw_apps, str):
            raw_apps = [raw_apps]
        normalized_apps = []
        for app in raw_apps:
            app = str(app).strip()
            if not app or app in ("null", "None", ""):
                continue
            if app in VALID_APP_FIELDS:
                normalized_apps.append(app)
            else:
                mapped = self._fuzzy_match_category(app, VALID_APP_FIELDS)
                if mapped:
                    normalized_apps.append(mapped)
                    confidence -= 0.08
                else:
                    confidence -= 0.12
        if not normalized_apps:
            normalized_apps = ["其他-待审核"]
            confidence -= 0.20
        result["application_fields"] = normalized_apps[:5]

        # --- innovation_level ---
        raw_inno = llm_data.get("innovation_level", "")
        raw_inno = str(raw_inno).strip()
        if raw_inno in VALID_INNOVATION:
            result["innovation_level"] = raw_inno
        elif raw_inno.lower() in ("high", "中高", "原创", "突破"):
            result["innovation_level"] = "High"
            confidence -= 0.05
        elif raw_inno.lower() in ("medium", "中", "改进", "优化"):
            result["innovation_level"] = "Medium"
            confidence -= 0.05
        elif raw_inno.lower() in ("low", "中低", "应用", "改造"):
            result["innovation_level"] = "Low"
            confidence -= 0.05
        else:
            confidence -= 0.15

        # --- technology_maturity_level ---
        raw_trl = llm_data.get("technology_maturity_level", 0)
        try:
            trl = int(raw_trl)
            if trl in VALID_TRL:
                result["technology_maturity_level"] = trl
            else:
                confidence -= 0.10
        except (ValueError, TypeError):
            confidence -= 0.15

        # clamp confidence
        result["classification_confidence"] = round(max(0.0, min(1.0, confidence)), 2)
        return result

    def _fuzzy_match_category(self, value: str, valid_set: set) -> Optional[str]:
        """模糊匹配：子串包含"""
        if not value:
            return None
        # 精确匹配
        if value in valid_set:
            return value
        # 包含匹配
        for valid in valid_set:
            if value in valid or valid in value:
                return valid
        return None

    # ─── 3. 单条处理 ───
    def process_one(self, patent: dict) -> Optional[dict]:
        """对单条专利执行 LLM 分类 + 模板校验"""
        # 已人工校验的跳过
        if patent.get("is_verified") and not self.dry_run:
            return None

        # 拼装专利文本
        text_parts = []
        if patent.get("title"):
            text_parts.append(f"【专利标题】{patent['title']}")
        if patent.get("abstract"):
            text_parts.append(f"【摘要】{patent['abstract']}")
        if patent.get("claims"):
            text_parts.append(f"【权利要求】{patent['claims'][:800]}")
        if patent.get("description_summary"):
            text_parts.append(f"【说明摘要】{patent['description_summary'][:800]}")

        patent_text = "\n".join(text_parts)
        if len(patent_text) < 20:
            return None

        # 调用 LLM
        llm_raw = self.call_llm(PATENT_PROMPT, patent_text)
        if not llm_raw:
            return None

        llm_data = self.parse_llm_json(llm_raw)
        if not llm_data:
            return None

        # 校验 → 归一化
        validated = self.validate_and_normalize(llm_data, patent_text)

        # 组装写入数据
        update_data = {
            "id": patent["id"],
            "technical_categories": validated.get("technical_categories"),
            "technical_subcategory": validated.get("technical_subcategory"),
            "industry_chain_position": validated.get("industry_chain_position"),
            "application_fields": validated.get("application_fields"),
            "classification_confidence": validated.get("classification_confidence"),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if validated.get("innovation_level"):
            update_data["innovation_level"] = validated["innovation_level"]
        if validated.get("technology_maturity_level"):
            update_data["technology_maturity_level"] = validated["technology_maturity_level"]

        return update_data

    # ─── 4. 写入 DB ───
    def write_back(self, update_data: dict):
        """单条 UPDATE 写入数据库"""
        pid = update_data.pop("id")
        try:
            if not self.dry_run:
                self.db_write.table("patents").update(update_data).eq("id", pid).execute()
            return True
        except Exception as e:
            print(f"  !! 写入失败 [{pid[:8]}]: {e}")
            return False

    # ─── 5. 主流程 ───
    def run(self, max_count=0, only_unclassified=False, force=False, resume=False):
        if resume:
            self._load_progress()

        patents = self.fetch_patents(max_count, only_unclassified, force)
        if not patents:
            return

        total = len(patents)
        print(f"\n{'=' * 60}")
        print(f"  专利分类回填 v2.0")
        print(f"  总量: {total}  |  模式: {'预览' if self.dry_run else '写入'}")
        print(f"  LLM 间隔: {self.delay}s")
        print(f"{'=' * 60}\n")

        for i, patent in enumerate(patents):
            pid = patent["id"]
            pn = patent.get("patent_number", "")[:16]
            title = (patent.get("title") or "")[:40]

            # 跳过已处理
            if pid in self.processed_ids:
                self.stats["skipped"] += 1
                continue

            safe_title = (str(title)[:40] if title else '')
            try:
                print(f"[{i+1}/{total}] {pn} | {safe_title}")
            except (UnicodeEncodeError, UnicodeDecodeError):
                print(f"[{i+1}/{total}] {pn}")

            # 已人工校验标记的跳过
            if patent.get("is_verified"):
                label = "人工校验" if str(patent.get("is_verified")).lower() == "true" else ""
                if label:
                    print(f"  ✓ 跳过 ({label})")
                    self.stats["skipped"] += 1
                    continue

            try:
                update_data = self.process_one(patent)
            except Exception as e:
                print(f"  !! 处理异常: {e}")
                self.stats["failed"] += 1
                self._save_progress(pid)
                time.sleep(self.delay)
                continue

            if not update_data:
                print(f"  - 无有效分类结果")
                self.stats["failed"] += 1
                self._save_progress(pid)
                time.sleep(self.delay)
                continue

            # 打印分类结果
            cats = update_data.get("technical_categories", [])
            sub = update_data.get("technical_subcategory", "")
            chain = update_data.get("industry_chain_position", "")
            conf = update_data.get("classification_confidence", 1.0)
            flag_str = " !" if conf < 0.6 else ""
            try:
                print(f"  -> {cats} | {sub} | {chain} | conf:{conf}{flag_str}")
            except (UnicodeEncodeError, UnicodeDecodeError):
                print(f"  -> [ok] | conf:{conf}")

            if conf < 0.6:
                self.stats["unverified"] += 1

            if self.write_back(update_data):
                self.stats["success"] += 1
                self.processed_ids.add(pid)
            else:
                self.stats["failed"] += 1

            self._save_progress(pid)
            time.sleep(self.delay)

        self._print_summary(total)

    # ─── 6. 进度持久化 ───
    def _save_progress(self, last_id):
        try:
            os.makedirs(os.path.dirname(PROGRESS_FILE), exist_ok=True)
            with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "last_id": last_id,
                    "processed_ids": list(self.processed_ids),
                    "processed_count": len(self.processed_ids),
                    "stats": self.stats,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }, f, ensure_ascii=False, indent=2)
        except:
            pass

    def _load_progress(self):
        if not os.path.exists(PROGRESS_FILE):
            return
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.processed_ids = set(data.get("processed_ids", []))
            self.stats = data.get("stats", self.stats)
            print(f"恢复进度: 已处理 {len(self.processed_ids)} 条")
        except:
            pass

    def _print_summary(self, total):
        print(f"\n{'=' * 60}")
        print(f"  回填完成")
        print(f"  总计: {total}")
        print(f"  成功: {self.stats['success']}")
        print(f"  跳过: {self.stats['skipped']}")
        print(f"  失败: {self.stats['failed']}")
        print(f"  需人工审核(置信度<0.6): {self.stats['unverified']}")
        print(f"{'=' * 60}")


# ─── 入口 ───
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AeroScope 专利分类回填 v2.0")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不写入数据库")
    parser.add_argument("--max", type=int, default=0, help="最大处理条数（0=全部）")
    parser.add_argument("--only-unclassified", action="store_true", help="仅处理 technical_categories 为空的专利")
    parser.add_argument("--force", action="store_true", help="强制重分类全部专利（含已分类）")
    parser.add_argument("--resume", action="store_true", help="从上次中断处继续")
    parser.add_argument("--delay", type=float, default=1.0, help="LLM 调用间隔秒数（默认1.0）")
    parser.add_argument("--include-design", action="store_true", help="包含外观设计专利（默认排除）")
    args = parser.parse_args()

    reclass = PatentReclassify(dry_run=args.dry_run, delay=args.delay,
                               skip_design=not args.include_design)
    reclass.run(
        max_count=args.max,
        only_unclassified=args.only_unclassified,
        force=args.force,
        resume=args.resume
    )
