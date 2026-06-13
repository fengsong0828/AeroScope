"""
专利审核 Agent
检查项: 缺技术分类/子分类/产业链/法律状态/申请人/日期异常/重复/信心度

用法:
  python agents/patent_auditor.py --dry-run
  python agents/patent_auditor.py --auto-fix
"""
import os, sys, re, json, time
sys.path.insert(0, os.path.dirname(__file__))
from auditor_base import AuditorBase


class PatentAuditor(AuditorBase):

    def __init__(self, dry_run=False):
        super().__init__('patent_auditor', dry_run)
        self._sample_size = 500  # 专利量大，默认抽样检查
        self._all_patents = []
        self._fetch_sample()

    def _fetch_sample(self):
        """抽样拉取（全量太慢，默认取最近500条+随机500条）"""
        # 最新500
        r = self.core.db.table('patents').select(
            'id,title,patent_number,applicant,abstract,technical_categories,'
            'technical_subcategory,industry_chain_position,legal_status,'
            'application_date,publication_date,classification_confidence,'
            'application_fields,related_company_id,draft'
        ).eq('draft', 'false').order('created_at', desc=True).limit(self._sample_size).execute()
        self._all_patents = r.data or []
        self.stats['scanned'] = len(self._all_patents)

    # ── 检查项 ──────────────────────────────────────────────

    def _check_missing_tech_category(self):
        """缺技术分类"""
        results = []
        for d in self._all_patents:
            tc = d.get('technical_categories')
            if not tc or tc == [] or tc == '[]':
                results.append((d['id'], d.get('title', '')[:60]))
        return results

    def _check_missing_subcategory(self):
        """缺技术子分类"""
        results = []
        for d in self._all_patents:
            if not d.get('technical_subcategory'):
                results.append((d['id'], d.get('title', '')[:60]))
        return results

    def _check_missing_industry_chain(self):
        """缺产业链位置"""
        results = []
        for d in self._all_patents:
            if not d.get('industry_chain_position'):
                results.append((d['id'], d.get('title', '')[:60]))
        return results

    def _check_low_confidence(self):
        """分类置信度 < 0.6 或 None"""
        results = []
        for d in self._all_patents:
            conf = d.get('classification_confidence')
            if conf is None or float(conf) < 0.6:
                results.append((d['id'], f"conf={conf} | {d.get('title', '')[:50]}"))
        return results

    def _check_date_anomaly(self):
        """公告日早于申请日"""
        results = []
        for d in self._all_patents:
            app_date = d.get('application_date')
            pub_date = d.get('publication_date')
            if app_date and pub_date and pub_date < app_date:
                results.append((d['id'], f"app={app_date} > pub={pub_date}"))
        return results

    def _check_missing_applicant(self):
        """缺申请人"""
        results = []
        for d in self._all_patents:
            if not d.get('applicant'):
                results.append((d['id'], d.get('title', '')[:60]))
        return results

    def _check_duplicate_patent_number(self):
        """重复专利号"""
        seen = {}
        results = []
        for d in self._all_patents:
            pn = d.get('patent_number', '')
            if not pn:
                continue
            if pn in seen:
                results.append((d['id'], f"dup of {seen[pn]}"))
            else:
                seen[pn] = d['id']
        return results

    def _check_missing_application_fields(self):
        """缺应用领域"""
        results = []
        for d in self._all_patents:
            af = d.get('application_fields')
            if not af or af == [] or af == '[]':
                results.append((d['id'], d.get('title', '')[:60]))
        return results

    def _check_empty_abstract(self):
        """摘要为空"""
        results = []
        for d in self._all_patents:
            if not d.get('abstract'):
                results.append((d['id'], d.get('title', '')[:60]))
        return results

    # ── 扫描 ────────────────────────────────────────────────

    def scan(self) -> dict:
        issues = {}
        for name, fn in [
            ('missing_tech_category', self._check_missing_tech_category),
            ('missing_subcategory', self._check_missing_subcategory),
            ('missing_industry_chain', self._check_missing_industry_chain),
            ('low_confidence', self._check_low_confidence),
            ('date_anomaly', self._check_date_anomaly),
            ('missing_applicant', self._check_missing_applicant),
            ('duplicate_patent_number', self._check_duplicate_patent_number),
            ('missing_application_fields', self._check_missing_application_fields),
            ('empty_abstract', self._check_empty_abstract),
        ]:
            result = fn()
            if result:
                issues[name] = result
                self._report(f"\n### {name} ({len(result)} 条)")
                for rid, detail in result[:10]:
                    self._report(f"- [{rid}] {detail}")
                if len(result) > 10:
                    self._report(f"- ... 还有 {len(result)-10} 条")
        return issues

    # ── 自动修复 ──────────────────────────────────────────────

    def auto_fix(self, issues: dict) -> dict:
        fixed = {}

        # 缺技术分类 → LLM根据abstract补充（仅对有abstract的）
        missing_tc = issues.get('missing_tech_category', [])
        if missing_tc:
            count = self._auto_classify(missing_tc, ['technical_categories', 'technical_subcategory',
                                                       'industry_chain_position', 'application_fields'])
            fixed['missing_tech_category'] = count
            self.stats['auto_fixed'] += count

        # 缺技术子分类 → LLM补充
        missing_sub = issues.get('missing_subcategory', [])
        if missing_sub:
            count = self._auto_classify(missing_sub, ['technical_subcategory'])
            fixed['missing_subcategory'] = count
            self.stats['auto_fixed'] += count

        # 缺产业链位置 → LLM补充
        missing_chain = issues.get('missing_industry_chain', [])
        if missing_chain:
            count = self._auto_classify(missing_chain, ['industry_chain_position'])
            fixed['missing_industry_chain'] = count
            self.stats['auto_fixed'] += count

        # 缺应用领域 → LLM补充
        missing_app = issues.get('missing_application_fields', [])
        if missing_app:
            count = self._auto_classify(missing_app, ['application_fields'])
            fixed['missing_application_fields'] = count
            self.stats['auto_fixed'] += count

        # 日期异常 → 标记
        dates = issues.get('date_anomaly', [])
        if dates:
            for rid, _ in dates:
                self._log('flag', 'patents', rid, 'draft', 'false', 'true', '日期异常', 'date_anomaly')
                if not self.dry_run:
                    self.core.db_write.table('patents').update({'draft': True}).eq('id', rid).execute()
            fixed['date_anomaly'] = len(dates)
            self.stats['auto_fixed'] += len(dates)

        return fixed

    def _auto_classify(self, items, fields):
        """LLM 根据 abstract 批量补充分类信息"""
        if not items:
            return 0
        from patent_classification_rules import (
            get_all_tech_categories, get_all_tech_subcategories,
            get_all_chain_positions, get_all_app_fields
        )
        VALID_CATS = set(get_all_tech_categories())
        VALID_SUBS = set(get_all_tech_subcategories())
        VALID_CHAIN = set(get_all_chain_positions())
        VALID_APPS = set(get_all_app_fields())

        BATCH = 5
        done = 0
        for i in range(0, len(items), BATCH):
            batch = items[i:i + BATCH]
            batch_ids = [p[0] for p in batch]
            r = self.core.db.table('patents').select('id,title,abstract').in_('id', batch_ids).execute()
            if not r.data:
                continue
            for d in r.data:
                abstract = d.get('abstract', '') or ''
                title = d.get('title', '')
                if not abstract:
                    continue
                prompt = (
                    "根据以下专利信息，输出JSON: {\"technical_categories\": [\"一级分类\"], "
                    "\"technical_subcategory\": \"二级子类\", "
                    "\"industry_chain_position\": \"产业链位置\", "
                    "\"application_fields\": [\"应用领域\"]}\n"
                    f"标题: {title}\n"
                    f"摘要: {abstract[:2000]}"
                )
                system = ("你是低空经济专利分类专家。技术分类从[飞行器构型设计,动力系统,飞行控制与导航,"
                          "通信与数据链,材料与制造工艺,航电系统,空中交通管理,适航与检测,运营与应用技术,"
                          "基础设施]中选择。产业链从[上游-原材料,上游-核心零部件,中游-分系统,"
                          "中游-整机制造,下游-运营服务,下游-飞行保障]中选择。只输出JSON。")
                raw = self._ask_llm(system, prompt)
                result = self.core.parse_llm_json(raw) if raw else None
                if not result or not isinstance(result, dict):
                    continue

                updates = {}
                for field in fields:
                    if not result.get(field):
                        continue
                    val = result[field]
                    if field == 'technical_categories' and isinstance(val, list):
                        valid_vals = [v for v in val if v in VALID_CATS]
                        if valid_vals:
                            updates[field] = json.dumps(valid_vals, ensure_ascii=False)
                    elif field == 'technical_subcategory' and isinstance(val, str):
                        if val in VALID_SUBS:
                            updates[field] = val
                    elif field == 'industry_chain_position' and isinstance(val, str):
                        if val in VALID_CHAIN:
                            updates[field] = val
                    elif field == 'application_fields':
                        vals = val if isinstance(val, list) else [val]
                        valid_vals = [v for v in vals if v in VALID_APPS]
                        if valid_vals:
                            updates[field] = json.dumps(valid_vals, ensure_ascii=False)
                if updates:
                    self._log('auto-fix', 'patents', d['id'], str(list(updates.keys())),
                              '', str(updates), 'LLM自动分类', 'missing_tech_category')
                    if not self.dry_run:
                        try:
                            self.core.db_write.table('patents').update(updates).eq('id', d['id']).execute()
                            done += 1
                        except Exception:
                            pass
                time.sleep(0.3)
        return done

    # ── 标记 ────────────────────────────────────────────────

    def flag(self, issues: dict, fixed: dict = None) -> dict:
        flagged = {}
        for check in ['missing_subcategory', 'missing_industry_chain', 'low_confidence',
                       'missing_applicant', 'duplicate_patent_number',
                       'missing_application_fields', 'empty_abstract']:
            items = issues.get(check, [])
            if items:
                auto_fixed_count = fixed.get(check, 0) if fixed else 0
                remaining = len(items) - auto_fixed_count
                if remaining > 0:
                    flagged[check] = f"{remaining}/{len(items)} items (report only)"
                    self.stats['flagged'] += remaining
        return flagged


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description='专利审核 Agent')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--scan', action='store_true')
    ap.add_argument('--auto-fix', action='store_true')
    args = ap.parse_args()

    dry = args.dry_run
    agent = PatentAuditor(dry_run=dry)
    if args.scan:
        agent.run(scan_only=True)
    elif args.auto_fix:
        agent.run(auto_fix=True)
    else:
        print("默认 dry-run 扫描。使用 --auto-fix 执行修复。")
        agent.run(scan_only=True)
