"""
政策审核 Agent
检查项: 空标题/内容/部门/日期/source_url/Level/重复/格式

用法:
  python agents/policy_auditor.py --dry-run
  python agents/policy_auditor.py --auto-fix
"""
import os, sys, re, json, time
sys.path.insert(0, os.path.dirname(__file__))
from auditor_base import AuditorBase


class PolicyAuditor(AuditorBase):

    def __init__(self, dry_run=False):
        super().__init__('policy_auditor', dry_run)
        self._all_policies = []
        self._fetch_all()

    def _fetch_all(self):
        offset = 0
        while True:
            r = self.core.db.table('policies').select(
                'id,title,department,publish_date,content,summary,level,source_url,draft'
            ).eq('draft', 'false').order('id').range(offset, offset + 999).execute()
            if not r.data:
                break
            self._all_policies.extend(r.data)
            offset += 1000
        self.stats['scanned'] = len(self._all_policies)

    # ── 检查项 ──────────────────────────────────────────────

    def _check_empty_title(self):
        results = []
        for d in self._all_policies:
            t = d.get('title', '')
            if not t or t == 'null':
                results.append((d['id'], 'empty_title'))
        return results

    def _check_empty_content(self):
        results = []
        for d in self._all_policies:
            c = d.get('content', '') or ''
            s = d.get('summary', '') or ''
            if not c and not s:
                results.append((d['id'], d.get('title', '')[:60]))
        return results

    def _check_missing_department(self):
        results = []
        for d in self._all_policies:
            dept = d.get('department', '')
            if not dept:
                results.append((d['id'], d.get('title', '')[:60]))
        return results

    def _check_missing_date(self):
        results = []
        for d in self._all_policies:
            if not d.get('publish_date'):
                results.append((d['id'], d.get('title', '')[:60]))
        return results

    def _check_duplicate_title(self):
        seen = {}
        results = []
        for d in self._all_policies:
            title = d.get('title', '')
            if not title:
                continue
            if title in seen:
                results.append((d['id'], f"duplicate of {seen[title]}"))
            else:
                seen[title] = d['id']
        return results

    def _check_source_url_gov(self):
        """source_url 应为政府网站"""
        results = []
        for d in self._all_policies:
            url = d.get('source_url', '') or ''
            if url and '.gov.cn' not in url:
                results.append((d['id'], url[:80]))
        return results

    def _check_missing_level(self):
        results = []
        for d in self._all_policies:
            if not d.get('level'):
                results.append((d['id'], d.get('title', '')[:60]))
        return results

    def _check_content_has_title_heading(self):
        """content 首行是否为 Markdown 标题（与 title 重复）"""
        results = []
        for d in self._all_policies:
            content = d.get('content', '') or ''
            title = d.get('title', '')
            if not content or not title:
                continue
            first_line = content.strip().split('\n')[0]
            heading_match = re.match(r'^#{1,3}\s*(.+?)$', first_line)
            if heading_match:
                heading_text = heading_match.group(1).strip()
                if heading_text == title or title in heading_text:
                    results.append((d['id'], f"heading: {heading_text[:50]}"))
        return results

    # ── 扫描 ────────────────────────────────────────────────

    def scan(self) -> dict:
        issues = {}
        for name, fn in [
            ('empty_title', self._check_empty_title),
            ('empty_content', self._check_empty_content),
            ('missing_department', self._check_missing_department),
            ('missing_date', self._check_missing_date),
            ('duplicate_title', self._check_duplicate_title),
            ('source_url_not_gov', self._check_source_url_gov),
            ('missing_level', self._check_missing_level),
            ('content_has_title_heading', self._check_content_has_title_heading),
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

        # 1. content 首行标题 → 去掉
        headings = issues.get('content_has_title_heading', [])
        if headings:
            count = 0
            for rid, _ in headings:
                # 读取当前content，去掉首行标题
                r = self.core.db.table('policies').select('content,title').eq('id', rid).execute()
                if not r.data:
                    continue
                d = r.data[0]
                content = d.get('content', '') or ''
                title = d.get('title', '')
                # 去掉首行 heading
                new_content = re.sub(r'^#{1,3}\s*' + re.escape(title) + r'\s*\n?', '', content.strip(), count=1)
                new_content = new_content.strip()
                if new_content != content:
                    self._log('auto-fix', 'policies', rid, 'content',
                              content[:80], new_content[:80],
                              '去除重复标题', 'content_has_title_heading')
                    if not self.dry_run:
                        try:
                            self.core.db_write.table('policies').update(
                                {'content': new_content}).eq('id', rid).execute()
                            count += 1
                        except:
                            pass
            fixed['content_has_title_heading'] = count
            self.stats['auto_fixed'] += count

        # 2. 空内容 → draft=true
        empty = issues.get('empty_content', [])
        if empty:
            count = 0
            for rid, _ in empty:
                self._log('flag', 'policies', rid, 'draft', 'false', 'true',
                          '内容为空', 'empty_content')
                if not self.dry_run:
                    try:
                        self.core.db_write.table('policies').update({'draft': True}).eq('id', rid).execute()
                        count += 1
                    except:
                        pass
            fixed['empty_content'] = count
            self.stats['auto_fixed'] += count

        return fixed

    # ── 标记 ────────────────────────────────────────────────

    def flag(self, issues: dict) -> dict:
        flagged = {}

        for check in ['missing_department', 'missing_date', 'source_url_not_gov',
                       'missing_level', 'duplicate_title', 'empty_title']:
            items = issues.get(check, [])
            if items:
                flagged[check] = f"{len(items)} items (report only)"
                self.stats['flagged'] += len(items)

        return flagged


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description='政策审核 Agent')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--scan', action='store_true')
    ap.add_argument('--auto-fix', action='store_true')
    args = ap.parse_args()

    dry = args.dry_run
    agent = PolicyAuditor(dry_run=dry)
    if args.scan:
        agent.run(scan_only=True)
    elif args.auto_fix:
        agent.run(auto_fix=True)
    else:
        print("默认 dry-run 扫描。使用 --auto-fix 执行修复。")
        agent.run(scan_only=True)
