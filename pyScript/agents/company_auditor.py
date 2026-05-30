"""
企业审核 Agent
检查项: 空名称/纯英文名/非企业混入/国籍错误/描述缺失/重复/缺产业链/无效URL

用法:
  python agents/company_auditor.py --dry-run        # 仅扫描
  python agents/company_auditor.py --auto-fix        # 扫描+自动修复
  python agents/company_auditor.py --full             # 扫描+修复+标记
"""
import os, sys, re, json, time, requests
sys.path.insert(0, os.path.dirname(__file__))
from auditor_base import AuditorBase


class CompanyAuditor(AuditorBase):

    def __init__(self, dry_run=False):
        super().__init__('company_auditor', dry_run)
        # 非企业关键词
        self.NON_COMPANY_KW = [
            '大学', 'University', '学院', 'College', 'School', '学校', '中学', '小学',
            '研究所', '研究院', '科学院', '学会', '协会', '实验室', 'Laboratory',
            '政府', '厅', '办公室', '委员会', '管理局', '监管局', '总队', '支队',
            '军区', '部队', '解放军', '空军', '海军', '国防', '军事',
            '医院', '卫生院', 'Hospital',
        ]
        # 企业关键词（含这些的不标记为非企业）
        self.COMPANY_KW = [
            '有限公司', '有限责任公司', '股份', '集团',
            'Inc', 'Corp', 'Ltd', 'LLC', 'GmbH', 'SpA', 'SAS', 'AG', 'Co.', 'Srl',
        ]
        # 统一用 anon key（读）+ service_role（写，如无则用 anon）
        self._all_companies = []
        self._fetch_all()

    def _fetch_all(self):
        """拉取全部可见企业"""
        offset = 0
        while True:
            r = self.core.db.table('companies').select(
                'id,name,name_en,country_code,description,website_url,industry_chain,draft'
            ).eq('draft', 'false').order('id').range(offset, offset + 999).execute()
            if not r.data:
                break
            self._all_companies.extend(r.data)
            offset += 1000
        self.stats['scanned'] = len(self._all_companies)

    # ── 检查项 ──────────────────────────────────────────────

    def _check_empty_name(self):
        """空名称 / 字符串 "null" """
        results = []
        for d in self._all_companies:
            name = d.get('name', '')
            if not name or name == 'null':
                results.append((d['id'], f"name='{name}'"))
        return results

    def _check_english_name(self):
        """CN企业纯英文名（需翻译）"""
        results = []
        for d in self._all_companies:
            name = d.get('name', '')
            cc = d.get('country_code', 'CN')
            if cc != 'CN':
                continue
            if not name or name == 'null':
                continue
            # 有中文则跳过
            if re.search(r'[\u4e00-\u9fff]', name):
                continue
            # 有英文才处理
            if re.search(r'[A-Za-z]{3,}', name):
                results.append((d['id'], name[:80]))
        return results

    def _check_foreign_country_code(self):
        """外国企业但标记为 CN"""
        results = []
        for d in self._all_companies:
            name = d.get('name', '')
            cc = d.get('country_code', 'CN')
            if cc != 'CN':
                continue
            if not name:
                continue
            # 含中文 → 中国公司，跳过
            if re.search(r'[\u4e00-\u9fff]', name):
                continue
            # 含有限公司 → 中国公司
            if any(kw in name for kw in ['有限公司', '有限责任公司', '股份', '集团']):
                continue
            # 含中国城市 → 中国公司
            cn_cities = ['Beijing', 'Shanghai', 'Shenzhen', 'Guangzhou', 'Chengdu',
                         'Nanjing', 'Wuhan', 'Tianjin', 'Hangzhou', 'Suzhou', 'Xi']
            if any(c in name for c in cn_cities):
                continue
            # 纯英文名且不含中国标识 → 可能外国公司
            if re.search(r'[A-Za-z]{3,}', name):
                results.append((d['id'], name[:80]))
        return results

    def _check_non_company(self):
        """非企业混入（大学/政府/医院/个人）"""
        results = []
        for d in self._all_companies:
            name = d.get('name', '')
            if not name or name == 'null':
                continue
            # 有公司关键词 → 是企业
            if any(kw.lower() in name.lower() for kw in self.COMPANY_KW):
                continue
            # 检查非企业关键词
            reasons = []
            for kw in self.NON_COMPANY_KW:
                if kw.lower() in name.lower():
                    reasons.append(kw)
            if reasons:
                results.append((d['id'], f"{name[:50]} | {'+'.join(reasons)}"))
                continue
            # 2-3字中文名 + 无描述 → 疑似个人
            if re.match(r'^[\u4e00-\u9fff]{2,3}$', name.strip()):
                desc = d.get('description', '') or ''
                if len(desc) < 20:
                    results.append((d['id'], f"{name} | person"))
        return results

    def _check_empty_description(self):
        """描述为空或默认值"""
        results = []
        for d in self._all_companies:
            desc = d.get('description', '') or ''
            if not desc or desc == '系统自动录入 - 专利申请人':
                results.append((d['id'], d.get('name', '')[:50]))
        return results

    def _check_duplicates(self):
        """同名企业"""
        seen = {}
        results = []
        for d in self._all_companies:
            name = d.get('name', '')
            if not name or name == 'null':
                continue
            if name in seen:
                results.append((d['id'], f"duplicate of {seen[name]}"))
            else:
                seen[name] = d['id']
        return results

    def _check_missing_industry_chain(self):
        """缺产业链位置"""
        results = []
        for d in self._all_companies:
            if not d.get('industry_chain'):
                results.append((d['id'], d.get('name', '')[:50]))
        return results

    def _check_invalid_url(self):
        """网站URL无效或为字符串null"""
        results = []
        for d in self._all_companies:
            url = d.get('website_url', '') or ''
            if url and (url == 'null' or not url.startswith('http')):
                results.append((d['id'], url[:50]))
        return results

    # ── 扫描 ────────────────────────────────────────────────

    def scan(self) -> dict:
        issues = {}
        for check_name, check_fn in [
            ('empty_name', self._check_empty_name),
            ('english_name', self._check_english_name),
            ('foreign_country_code', self._check_foreign_country_code),
            ('non_company', self._check_non_company),
            ('empty_description', self._check_empty_description),
            ('duplicates', self._check_duplicates),
            ('missing_industry_chain', self._check_missing_industry_chain),
            ('invalid_url', self._check_invalid_url),
        ]:
            result = check_fn()
            if result:
                issues[check_name] = result
                self._report(f"\n### {check_name} ({len(result)} 条)")
                for rid, detail in result[:10]:
                    self._report(f"- [{rid}] {detail}")
                if len(result) > 10:
                    self._report(f"- ... 还有 {len(result)-10} 条")
        return issues

    # ── 自动修复 ──────────────────────────────────────────────

    def auto_fix(self, issues: dict) -> dict:
        fixed = {}

        # 1. 无效 URL → 清空
        urls = issues.get('invalid_url', [])
        if urls:
            count = 0
            for rid, _ in urls:
                self._log('auto-fix', 'companies', rid, 'website_url', _, 'NULL', '无效URL清空', 'invalid_url')
                if not self.dry_run:
                    try:
                        self.core.db_write.table('companies').update({'website_url': None}).eq('id', rid).execute()
                        count += 1
                    except:
                        pass
            fixed['invalid_url'] = count
            self.stats['auto_fixed'] += count

        # 2. 纯英文名 → LLM 翻译
        eng = issues.get('english_name', [])
        if eng:
            count = self._auto_translate_names([(rid, name) for rid, name in eng])
            fixed['english_name'] = count
            self.stats['auto_fixed'] += count

        # 3. 国籍错误 → LLM 修正
        foreign = issues.get('foreign_country_code', [])
        if foreign:
            count = self._auto_fix_country([(rid, name) for rid, name in foreign])
            fixed['foreign_country_code'] = count
            self.stats['auto_fixed'] += count

        return fixed

    def _auto_translate_names(self, items):
        """LLM 批量翻译公司英文名 → 中文，写入 name，英文移入 name_en"""
        if not items:
            return 0
        BATCH = 8
        done = 0
        for i in range(0, len(items), BATCH):
            batch = items[i:i + BATCH]
            names = [name for _, name in batch]
            prompt = (
                "将以下中国公司英文名翻译为规范中文名。返回纯JSON对象，key=英文名，value=中文名。\n"
                "规则: 保留城市名(Beijing→北京,Shenzhen→深圳); 保留有限公司/股份有限公司后缀; "
                "品牌名用常见音译或意译。\n"
                f"公司名列表: {json.dumps(names, ensure_ascii=False)}"
            )
            raw = self._ask_llm(
                "你是中国公司名称翻译专家，只输出JSON。",
                prompt
            )
            translations = self.core.parse_llm_json(raw) if raw else None
            if not translations or not isinstance(translations, dict):
                continue
            for rid, en_name in zip([p[0] for p in batch], names):
                cn_name = translations.get(en_name)
                if cn_name and cn_name != en_name and re.search(r'[\u4e00-\u9fff]', cn_name):
                    old_name = en_name
                    self._log('auto-fix', 'companies', rid, 'name', old_name, cn_name,
                              'LLM翻译', 'english_name')
                    if not self.dry_run:
                        try:
                            self.core.db_write.table('companies').update({
                                'name': cn_name, 'name_en': en_name
                            }).eq('id', rid).execute()
                            done += 1
                        except:
                            pass
            time.sleep(0.5)
        return done

    def _auto_fix_country(self, items):
        """LLM 判定外国公司国籍"""
        if not items:
            return 0
        BATCH = 10
        done = 0
        for i in range(0, len(items), BATCH):
            batch = items[i:i + BATCH]
            names = [name for _, name in batch]
            prompt = (
                "判定以下公司总部所在国家/地区，返回ISO 3166-1 alpha-2代码。\n"
                "已知的外国公司用正确代码(US/DE/FR/JP/KR等)。中国公司用CN。\n"
                "返回纯JSON对象，key=公司名，value=国家代码。\n"
                f"公司列表: {json.dumps(names, ensure_ascii=False)}"
            )
            raw = self._ask_llm(
                "你是公司国籍判定专家，只输出JSON，key为公司名，value为ISO国家代码。",
                prompt
            )
            result = self.core.parse_llm_json(raw) if raw else None
            if not result or not isinstance(result, dict):
                continue
            for rid, en_name in zip([p[0] for p in batch], names):
                cc = result.get(en_name)
                if cc and cc != 'CN' and len(cc) == 2:
                    self._log('auto-fix', 'companies', rid, 'country_code', 'CN', cc,
                              f'LLM国籍判定→{cc}', 'foreign_country_code')
                    if not self.dry_run:
                        try:
                            self.core.db_write.table('companies').update({'country_code': cc}).eq('id', rid).execute()
                            done += 1
                        except:
                            pass
            time.sleep(0.5)
        return done

    # ── 标记 ────────────────────────────────────────────────

    def flag(self, issues: dict) -> dict:
        flagged = {}

        # 空名称 → draft=true
        empty = issues.get('empty_name', [])
        if empty:
            count = 0
            for rid, _ in empty:
                self._log('flag', 'companies', rid, 'draft', 'false', 'true',
                          '空名称', 'empty_name')
                if not self.dry_run:
                    try:
                        self.core.db_write.table('companies').update({'draft': True}).eq('id', rid).execute()
                        count += 1
                    except:
                        pass
            flagged['empty_name'] = count

        # 非企业 → draft=true
        non_co = issues.get('non_company', [])
        if non_co:
            count = 0
            for rid, _ in non_co:
                self._log('flag', 'companies', rid, 'draft', 'false', 'true',
                          '非企业实体', 'non_company')
                if not self.dry_run:
                    try:
                        self.core.db_write.table('companies').update({'draft': True}).eq('id', rid).execute()
                        count += 1
                    except:
                        pass
            flagged['non_company'] = count

        # 重复名 → 保留首条，其余 draft=true
        dups = issues.get('duplicates', [])
        if dups:
            count = 0
            for rid, _ in dups:
                self._log('flag', 'companies', rid, 'draft', 'false', 'true',
                          '同名企业重复', 'duplicates')
                if not self.dry_run:
                    try:
                        self.core.db_write.table('companies').update({'draft': True}).eq('id', rid).execute()
                        count += 1
                    except:
                        pass
            flagged['duplicates'] = count

        # 其余标记项不自动标记，只在报告中列出
        for check in ['empty_description', 'missing_industry_chain']:
            items = issues.get(check, [])
            if items:
                flagged[check] = f"{len(items)} items (report only)"
                self.stats['flagged'] += len(items)

        return flagged


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description='企业审核 Agent')
    ap.add_argument('--dry-run', action='store_true', help='仅扫描不修改')
    ap.add_argument('--scan', action='store_true', help='仅扫描+出报告')
    ap.add_argument('--auto-fix', action='store_true', help='扫描+自动修复')
    ap.add_argument('--full', action='store_true', help='扫描+修复+标记')
    args = ap.parse_args()

    dry = args.dry_run
    agent = CompanyAuditor(dry_run=dry)

    if args.scan:
        agent.run(scan_only=True)
    elif args.auto_fix:
        agent.run(auto_fix=True)
    elif args.full:
        agent.run(auto_fix=True, scan_only=False)
        # full mode triggers flag too
        agent.flag(agent.scan())
        print(f"\n标记完成: {agent.stats['flagged']} 项")
    else:
        # 默认 dry-run + scan only
        print("默认 dry-run 扫描模式。使用 --auto-fix 执行修复。")
        agent.run(scan_only=True)
