"""
审计 Agent 公共基类
提供：DB连接、LLM调用、日志记录、报告生成
"""
import os, sys, json, time, uuid
from datetime import datetime, timezone
from typing import Optional, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dotenv import load_dotenv; load_dotenv()
from collector_core import CollectorCore


class AuditorBase:
    """公共审计基类，所有 Agent 继承此类"""

    def __init__(self, agent_name: str, dry_run: bool = False):
        self.agent_name = agent_name
        self.dry_run = dry_run
        self.batch_id = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S') + '-' + agent_name
        self.core = CollectorCore()
        self.stats = {'scanned': 0, 'auto_fixed': 0, 'flagged': 0, 'skipped': 0, 'errors': 0}
        self.report_lines = []

    # ── 日志记录 ──────────────────────────────────────────────

    def _log(self, operation_type: str, target_table: str, target_id: Any,
             field_name: str = None, old_value: str = None, new_value: str = None,
             reason: str = '', check_item: str = ''):
        """写入 audit_log 表"""
        payload = {
            'agent_name': self.agent_name,
            'operation_type': operation_type,
            'target_table': target_table,
            'target_id': str(target_id) if target_id is not None else None,
            'field_name': field_name,
            'old_value': str(old_value)[:500] if old_value is not None else None,
            'new_value': str(new_value)[:500] if new_value is not None else None,
            'reason': reason[:300],
            'check_item': check_item[:200],
            'batch_id': self.batch_id,
            'dry_run': self.dry_run,
        }
        try:
            self.core.db_write.table('audit_log').insert(payload).execute()
        except Exception:
            pass  # 日志写入失败不阻塞主流程

    def _report(self, line: str):
        """添加到最终报告"""
        self.report_lines.append(line)

    def _save_report(self):
        """保存报告到 agent-workspace/audit-reports/"""
        today = datetime.now().strftime('%Y-%m-%d')
        report_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..',
                                  'agent-workspace', 'audit-reports', today)
        os.makedirs(report_dir, exist_ok=True)
        filepath = os.path.join(report_dir, f'{self.agent_name}.md')
        header = f"# {self.agent_name} 审计报告\n"
        header += f"批次: {self.batch_id} | 模式: {'dry-run' if self.dry_run else 'auto-fix'}\n"
        header += f"时间: {datetime.now().isoformat()}\n\n"
        header += f"## 统计\n"
        header += f"- 扫描: {self.stats['scanned']}\n"
        header += f"- 自动修复: {self.stats['auto_fixed']}\n"
        header += f"- 已标记: {self.stats['flagged']}\n"
        header += f"- 跳过: {self.stats['skipped']}\n"
        header += f"- 错误: {self.stats['errors']}\n\n"
        header += f"## 详情\n\n"
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(header + '\n'.join(self.report_lines))
        return filepath

    # ── DB 操作（安全封装）───────────────────────────────────

    def _update_field(self, table: str, pid: Any, field: str, new_val: Any,
                      old_val: Any = None, reason: str = '', check_item: str = ''):
        """安全更新单个字段，dry-run 下只记录不执行"""
        self._log('auto-fix', table, pid, field, str(old_val), str(new_val), reason, check_item)
        if self.dry_run:
            return True
        try:
            self.core.db_write.table(table).update({field: new_val}).eq('id', pid).execute()
            self.stats['auto_fixed'] += 1
            return True
        except Exception as e:
            self.stats['errors'] += 1
            self._report(f"- **错误** {table} id={pid}: {e}")
            return False

    def _flag_item(self, table: str, pid: Any, reason: str = '', check_item: str = ''):
        """标记为 draft=true 需人工复核"""
        self._log('flag', table, pid, 'draft', 'false', 'true', reason, check_item)
        if self.dry_run:
            self.stats['flagged'] += 1
            return True
        try:
            self.core.db_write.table(table).update({'draft': True}).eq('id', pid).execute()
            self.stats['flagged'] += 1
            return True
        except Exception:
            self.stats['errors'] += 1
            return False

    # ── LLM 调用 ─────────────────────────────────────────────

    def _ask_llm(self, system_prompt: str, user_text: str, retries: int = 3) -> Optional[str]:
        """调用 LLM，自动重试"""
        return self.core.call_llm(system_prompt, user_text, retries)

    def _ask_llm_json(self, system_prompt: str, user_text: str) -> Optional[dict]:
        """调用 LLM 并解析 JSON 返回"""
        raw = self._ask_llm(system_prompt, user_text)
        if not raw:
            return None
        return self.core.parse_llm_json(raw)

    # ── 子类接口 ─────────────────────────────────────────────

    def scan(self) -> dict:
        """扫描阶段：发现所有问题，返回 {check_item: [(id, detail), ...]}"""
        raise NotImplementedError

    def auto_fix(self, issues: dict) -> dict:
        """自动修复阶段：处理可自动修复的问题"""
        raise NotImplementedError

    def flag(self, issues: dict) -> dict:
        """标记阶段：标记需人工复核的条目"""
        raise NotImplementedError

    def run(self, scan_only: bool = False, auto_fix: bool = False):
        """完整运行流程"""
        print(f"\n{'='*60}")
        print(f"  {self.agent_name} | batch={self.batch_id}")
        print(f"  mode: {'dry-run' if self.dry_run else 'LIVE'}")
        print(f"{'='*60}\n")

        # Phase 1: Scan
        print("[Phase 1] 扫描...")
        issues = self.scan()
        total_issues = sum(len(v) for v in issues.values())
        self._report(f"## 扫描结果 ({total_issues} 项问题)\n")
        for check_item, items in issues.items():
            self._report(f"\n### {check_item} ({len(items)} 条)")
            for item in items[:20]:  # 报告只列前20条
                self._report(f"- id={item[0]}: {item[1][:80] if len(item)>1 else ''}")
            if len(items) > 20:
                self._report(f"- ... 还有 {len(items)-20} 条")
        print(f"  发现 {total_issues} 项问题，分布在 {len(issues)} 个检查项")

        if scan_only:
            filepath = self._save_report()
            print(f"  报告已保存: {filepath}")
            return issues

        # Phase 2: Auto-fix
        fixed = {}
        if auto_fix:
            print("\n[Phase 2] 自动修复...")
            fixed = self.auto_fix(issues)
            self._report(f"\n## 自动修复\n")
            for check_item, count in fixed.items():
                self._report(f"- {check_item}: {count} 条")
                print(f"  {check_item}: {count} 条")

        # Phase 3: Flag
        print("\n[Phase 3] 标记待审核...")
        flagged = self.flag(issues, fixed)
        self._report(f"\n## 标记待审核\n")
        for check_item, count in flagged.items():
            self._report(f"- {check_item}: {count} 条")
            print(f"  {check_item}: {count} 条")

        # Final
        filepath = self._save_report()
        print(f"\n完成。报告: {filepath}")
        print(f"统计: 扫描{self.stats['scanned']} | 修复{self.stats['auto_fixed']} | "
              f"标记{self.stats['flagged']} | 跳过{self.stats['skipped']} | 错误{self.stats['errors']}")
        return issues
