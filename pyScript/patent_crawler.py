"""
AeroScope Patent Crawler — 链式递归专利爬虫

逻辑:
  种子 URL → 提取引用/被引/相似专利 →
  ├─ 匹配低空经济 → 加入活跃队列，继续递归
  ├─ 不匹配 → 仅存储基本信息，链接存入后备池
  └─ 已访问 → 跳过

低空经济关键词库:
  eVTOL, drone, UAV, UAM, AAM, multicopter, tiltrotor, VTOL, aerial vehicle,
  无人机, 飞行器, 低空, 垂直起降, 旋翼, 倾转, 多旋翼, 复合翼, 电动航空,
  urban air mobility, flying car, air taxi, 空中的士, 物流无人机

用法:
  python pyScript/patent_crawler.py --seed "URL" --max 200 --export
  python pyScript/patent_crawler.py --seed "URL" --max 200 --resume
"""
import os, sys, time, re, json, argparse
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv; load_dotenv()
from collector_core import CollectorCore
from llm_prompts import PATENT_PROMPT
from patent_classification_rules import (
    TECH_CATEGORIES, INDUSTRY_CHAIN, APP_FIELDS,
    match_keywords_to_categories, match_keywords_to_chain,
    match_keywords_to_app
)
import requests as http_requests
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
}

# 低空经济关键词 — 从分类规则汇总，用于判断专利是否相关
LOWALT_KEYWORDS = [
    # English (from all TECH_CATEGORIES)
    "evtol", "drone", "uav", "uam", "aam", "multicopter", "tiltrotor", "vtol",
    "aerial vehicle", "urban air mobility", "flying car", "air taxi",
    "vertical takeoff", "rotorcraft", "unmanned aerial", "ducted fan",
    "composite", "carbon fiber", "airframe", "propulsion", "avionics",
    "flight control", "navigation", "data link", "vertiport",
    # Chinese
    "无人机", "飞行器", "低空", "垂直起降", "旋翼", "倾转", "多旋翼",
    "复合翼", "电动航空", "空中的士", "物流无人机", "城市空中交通",
    "倾转旋翼", "涵道风扇", "飞翼", "飞行汽车", "航电", "飞控",
    "适航", "碳纤维", "复合材料", "钛合金", "动力电池", "固态电池",
    "空管", "起降", "停机坪", "电机系统", "永磁同步", "传感器",
    "空中交通", "巡检", "植保", "应急救援"
]

WORKSPACE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                         "agent-workspace", "data-engineer", "data-schemas")


class PatentCrawler(CollectorCore):
    """链式递归专利爬虫"""

    def __init__(self, gui_callback=None):
        super().__init__()
        self.gui_callback = gui_callback
        self.visited = set()
        self.visited_records = []  # 已访问专利详情列表
        self.patents_store = []
        self.backlog = []
        self.lowalt_records = []   # 低空相关专利详情列表
        self.saved_records = []    # 已入库专利详情列表
        self.matching_count = 0
        self.saved_count = 0
        self.running = True

    def _extract_id(self, url):
        parts = [p for p in url.split('/') if p]
        if 'patent' in parts:
            idx = parts.index('patent')
            return parts[idx + 1] if idx + 1 < len(parts) else parts[-1]
        return url.split('/')[-1]

    def _make_backlog_item(self, url, relation):
        """创建后备池条目，提取专利号和 URL"""
        pid = self._extract_id(url)
        return {
            "patent_number": pid,
            "title": "",
            "applicant": "",
            "google_url": url,
            "relation": relation,
        }

    # ─── 低空经济相关性判断 ───
    def _is_lowalt(self, title, abstract, assignee, ipc=""):
        """判断专利是否与低空经济相关（IPC + 关键词双层过滤）"""
        # 第一层：IPC 分类命中（最精确）
        if ipc:
            for prefix in ["B64", "B60F", "G05D", "G08G", "H01M", "H02K", "G01S", "H04W", "B64C", "B64D"]:
                if prefix in ipc:
                    return True
        # 第二层：关键词
        text = f"{title} {abstract} {assignee}".lower()
        for kw in LOWALT_KEYWORDS:
            if kw in text:
                return True
        return False

    # ─── 核心递归 ───
    def crawl(self, seed_url, max_visit=200, resume_file=None):
        """从种子开始递归爬取"""
        print(f"\n{'='*60}")
        print(f"  Patent Crawler - Chain Reaction")
        print(f"  Seed: {seed_url}")
        print(f"  Max visits: {max_visit}")
        print(f"{'='*60}")

        # 恢复上次进度
        if resume_file and os.path.exists(resume_file):
            with open(resume_file, 'r', encoding='utf-8') as f:
                saved = json.load(f)
                self.visited = set(saved.get("visited", []))
                raw_backlog = saved.get("backlog", [])
                self.backlog = []
                for b in raw_backlog:
                    if isinstance(b, dict):
                        self.backlog.append(b)
                    elif isinstance(b, (list, tuple)) and len(b) >= 2:
                        self.backlog.append(self._make_backlog_item(b[0], b[1]))
                self.patents_store = saved.get("stored", [])
                print(f"  Resumed: {len(self.visited)} visited, {len(self.backlog)} in backlog")

        # 立即保存初始进度
        self._save_progress(resume_file or os.path.join(WORKSPACE, "crawler_progress.json"))

        # 活跃队列: 低空相关的专利，继续递归
        active_queue = [(seed_url, 'seed', 0)]  # (url, relation, depth)

        while active_queue and len(self.visited) < max_visit and self.running:
            url, rel, depth = active_queue.pop(0)
            patent_id = self._extract_id(url)

            if patent_id in self.visited:
                continue
            self.visited.add(patent_id)

            indent = "  " * min(depth, 3)
            print(f"{indent}[{len(self.visited)}] {patent_id} ({rel}, depth={depth})")

            # 抓取页面
            try:
                resp = http_requests.get(url, headers=HEADERS, timeout=30)
                resp.encoding = 'utf-8'
                if resp.status_code != 200:
                    self.backlog.append(self._make_backlog_item(url, rel))
                    continue
            except:
                self.backlog.append(self._make_backlog_item(url, rel))
                time.sleep(2)
                continue

            soup = BeautifulSoup(resp.text, 'html.parser')

            # 提取基本信息
            title = (soup.find('title').text or '').replace(' - Google Patents', '').strip() if soup.find('title') else ''
            assignee_meta = soup.find('meta', {'scheme': 'assignee'})
            assignee = assignee_meta.get('content', '') if assignee_meta else ''

            # 提取摘要
            abstract = ''
            abs_section = soup.find('section', {'itemprop': 'abstract'})
            if abs_section:
                abstract = abs_section.get_text(separator=' ', strip=True)[:500]

            # 提取法律状态
            status = 'Unknown'
            for elem in soup.find_all(string=re.compile(r'^Status')):
                text = elem.find_parent().get_text().replace('Status', '').strip()
                if text:
                    status = text[:100]
                    break

            # 提取 IPC 分类
            ipc = ''
            for meta in soup.find_all('meta', {'scheme': re.compile(r'IPC', re.I)}):
                ipc = meta.get('content', '')
                break

            # 存储基本信息
            record = {
                "patent_number": patent_id,
                "title": title[:300],
                "applicant": assignee[:200],
                "abstract": abstract[:500],
                "legal_status": status[:100],
                "google_url": url,
                "draft": False
            }
            self.patents_store.append(record)
            visited_info = {
                "patent_number": patent_id,
                "title": title[:80],
                "applicant": assignee[:60],
                "google_url": url,
            }
            self.visited_records.append(visited_info)

            # 判断是否低空经济相关
            is_lowalt = self._is_lowalt(title, abstract, assignee, ipc)

            if is_lowalt:
                self.matching_count += 1
                self.upsert("patents", record, "patent_number")
                self.saved_count += 1
                self.lowalt_records.append(visited_info)
                self.saved_records.append(visited_info)
                # 实时写入 JSON（每 10 条低空专利存一次）
                if self.matching_count % 10 == 0:
                    self.export_json()
                print(f"{indent}  🟢 LOW-ALT | {title[:50]}")
            else:
                print(f"{indent}  ⚪ skip recurse | {title[:40]}")

            self._gui_update({
                "visited": len(self.visited),
                "matched": self.matching_count,
                "backlog": len(self.backlog),
                "saved": self.saved_count,
                "active": len(active_queue),
                "active_next": [pid for pid, _, _ in active_queue[:5]],
                "is_lowalt": is_lowalt,
                "relation": rel,
                "latest_record": record,
                "visited_records": self.visited_records,
                "lowalt_records": self.lowalt_records,
                "backlog_records": self.backlog,
                "saved_records": self.saved_records,
            })

            # 提取关联链接

            # 提取关联链接
            linked = self._extract_linked_patents(soup, resp.text)

            if is_lowalt:
                # 低空相关 → 加入活跃队列继续递归
                for pid, link_url, link_rel in linked:
                    if pid not in self.visited:
                        active_queue.append((link_url, link_rel, depth + 1))
            else:
                # 不相关 → 只存后备池，不继续递归
                for pid, link_url, link_rel in linked:
                    if pid not in self.visited:
                        self.backlog.append(self._make_backlog_item(link_url, link_rel))

            # 进度报告
            if len(self.visited) % 20 == 0:
                print(f"  [Progress] visited={len(self.visited)} | active={len(active_queue)} | "
                      f"backlog={len(self.backlog)} | lowalt={self.matching_count}")

            # 定期保存进度（每 3 条存一次）
            if len(self.visited) % 3 == 0:
                self._save_progress(resume_file or os.path.join(WORKSPACE, "crawler_progress.json"))
                print(f"    💾 saved ({len(self.visited)} visited, {self.matching_count} matched)")

            time.sleep(0.5)

        # 完成
        self._save_progress(resume_file or os.path.join(WORKSPACE, "crawler_progress.json"))
        self.export_json()
        print(f"\n{'='*40}")
        print(f"  CRAWL COMPLETE")
        print(f"  Visited: {len(self.visited)}")
        print(f"  Low-alt matched: {self.matching_count}")
        print(f"  Saved to DB: {self.saved_count}")
        print(f"  Backlog (pending): {len(self.backlog)}")
        print(f"{'='*40}")

        # 保存进度（支持后续恢复）
        self._save_progress(resume_file or os.path.join(WORKSPACE, "crawler_progress.json"))

        return {
            "visited": len(self.visited),
            "lowalt": self.matching_count,
            "saved": self.saved_count,
            "backlog": len(self.backlog)
        }

    def _extract_linked_patents(self, soup, html):
        """从页面提取所有关联专利"""
        linked = []
        seen = set()

        # 引用专利
        for row in soup.find_all('tr', {'itemprop': 'backwardReferences'}):
            for m in re.finditer(r'([A-Z]{2}\d{7,}[A-Za-z]?)', row.get_text()):
                pid = m.group(1).upper()
                if pid not in seen and len(pid) >= 12:
                    seen.add(pid)
                    linked.append((pid, f"https://patents.google.com/patent/{pid}/zh", 'cites'))

        # 被引用
        for row in soup.find_all('tr', {'itemprop': 'forwardReferences'}):
            for m in re.finditer(r'([A-Z]{2}\d{7,}[A-Za-z]?)', row.get_text()):
                pid = m.group(1).upper()
                if pid not in seen and len(pid) >= 12:
                    seen.add(pid)
                    linked.append((pid, f"https://patents.google.com/patent/{pid}/zh", 'cited_by'))

        # 相似文档
        section = soup.find('section', {'id': 'similarDocuments'})
        if section:
            for m in re.finditer(r'([A-Z]{2}\d{7,}[A-Za-z]?)', section.get_text()):
                pid = m.group(1).upper()
                if pid not in seen and len(pid) >= 12:
                    seen.add(pid)
                    linked.append((pid, f"https://patents.google.com/patent/{pid}/zh", 'similar'))

        # 页面其他专利链接
        for match in re.finditer(r'/patent/([A-Z]{2}\d{7,}[A-Za-z]?)/[a-z]{2}', html):
            pid = match.group(1).upper()
            if pid not in seen and len(pid) >= 12:
                seen.add(pid)
                linked.append((pid, f"https://patents.google.com/patent/{pid}/zh", 'related'))

        return linked

    def _gui_update(self, data):
        """通知 GUI 刷新进度"""
        if self.gui_callback:
            self.gui_callback(data)

    def export_json(self):
        """导出/合并 JSON — 已有文件不覆盖，增量追加去重"""
        path = os.path.join(WORKSPACE, "lowalt_patents.json")
        os.makedirs(WORKSPACE, exist_ok=True)

        # 加载已有数据
        existing = {}
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    old = json.load(f)
                for p in old.get("patents", []):
                    existing[p.get("patent_number", "")] = p
            except:
                pass

        # 合并新数据（patent_number 去重）
        new_count = 0
        for p in self.patents_store:
            pn = p.get("patent_number", "")
            if not pn:
                continue
            if self._is_lowalt(p.get("title",""), p.get("abstract",""), p.get("applicant",""), ""):
                if pn not in existing:
                    existing[pn] = p
                    new_count += 1
                else:
                    # 更新已有记录（标题等可能更完整）
                    existing[pn].update(p)

        # 写回
        patents_list = sorted(existing.values(), key=lambda x: x.get("patent_number", ""))
        data = {
            "total": len(patents_list),
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "patents": patents_list
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n  📄 JSON merged: {path} (total {len(patents_list)}, +{new_count} new)")
        return path
        parts = [p for p in url.split('/') if p]
        if 'patent' in parts:
            idx = parts.index('patent')
            return parts[idx + 1] if idx + 1 < len(parts) else parts[-1]
        return url.split('/')[-1]

    def _save_progress(self, filepath):
        data = {
            "visited": list(self.visited),
            "backlog": [{"patent_number": b.get("patent_number", ""), "google_url": b.get("google_url", ""),
                          "relation": b.get("relation", ""), "title": b.get("title", ""),
                          "applicant": b.get("applicant", "")}
                         for b in self.backlog[-1000:]],  # 只保留最近1000条后备
            "stored": [{"patent_number": p.get("patent_number",""), "title": p.get("title","")[:60]} 
                       for p in self.patents_store],
            "stats": {
                "visited": len(self.visited),
                "matched": self.matching_count,
                "saved": self.saved_count,
                "backlog": len(self.backlog)
            }
        }
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ─── 导出 ───
    def export_csv(self):
        """导出低空专利到 CSV（兼容旧名）"""
        return self.export_json()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Patent Chain Crawler")
    parser.add_argument("--seed", help="Seed patent URL")
    parser.add_argument("--max", type=int, default=200)
    parser.add_argument("--export", action="store_true")
    args = parser.parse_args()

    if not args.seed:
        args.seed = "https://patents.google.com/patent/CN110267876B/zh"

    import tkinter as tk
    from tkinter import ttk, messagebox
    import threading

    root = tk.Tk()
    root.title("AeroScope 低空经济专利爬虫")
    root.geometry("680x620")
    root.configure(bg="#f0f2f5")

    # ═══════════════ 顶部输入区 ═══════════════
    top = tk.Frame(root, bg="white", relief="solid", bd=0, highlightbackground="#e2e8f0", highlightthickness=1)
    top.pack(fill=tk.X, padx=10, pady=(10, 5))

    tk.Label(top, text="种子 URL", font=("Microsoft YaHei", 9, "bold"), fg="#0f172a", bg="white").pack(anchor="w", padx=12, pady=(10, 0))
    seed_entry = tk.Entry(top, font=("Consolas", 9), relief="solid", bd=1)
    seed_entry.insert(0, args.seed)
    seed_entry.pack(fill=tk.X, padx=12, pady=(2, 8))

    ctrl = tk.Frame(top, bg="white")
    ctrl.pack(fill=tk.X, padx=12, pady=(0, 12))
    tk.Label(ctrl, text="最大访问", font=("Microsoft YaHei", 9), fg="#64748b", bg="white").pack(side=tk.LEFT)
    max_var = tk.StringVar(value=str(args.max))
    tk.Spinbox(ctrl, from_=10, to=5000, increment=100, textvariable=max_var, width=6, font=("Consolas", 10)).pack(side=tk.LEFT, padx=6)
    export_var = tk.BooleanVar(value=True)
    tk.Checkbutton(ctrl, text="导出JSON", variable=export_var, font=("Microsoft YaHei", 9), bg="white").pack(side=tk.LEFT, padx=15)
    start_btn = tk.Button(ctrl, text="🚀 开始爬取", bg="#059669", fg="white", font=("Microsoft YaHei", 11, "bold"), relief="flat", padx=25, pady=4, cursor="hand2")
    start_btn.pack(side=tk.RIGHT)
    stop_btn = tk.Button(ctrl, text="⏹ 停止", bg="#ef4444", fg="white", font=("Microsoft YaHei", 10), relief="flat", padx=18, pady=4, state="disabled", cursor="hand2")
    stop_btn.pack(side=tk.RIGHT, padx=8)

    # ═══════════════ 统计卡片 ═══════════════
    cards = tk.Frame(root, bg="#f0f2f5")
    cards.pack(fill=tk.X, padx=10, pady=5)
    stat_widgets = {}
    card_frames = {}
    stored_data = {"visited_records": [], "lowalt_records": [], "backlog_records": [], "saved_records": []}

    def show_popup(title, items, columns):
        """弹出详情列表窗口（支持 Ctrl+C 复制）"""
        popup = tk.Toplevel(root)
        popup.title(title)
        popup.geometry("950x550")
        popup.configure(bg="white")
        
        # 标题栏
        header = tk.Frame(popup, bg="#0f172a")
        header.pack(fill=tk.X)
        tk.Label(header, text=title, font=("Microsoft YaHei", 12, "bold"), fg="white", bg="#0f172a").pack(padx=16, pady=8, anchor="w")
        tk.Label(header, text=f"共 {len(items)} 条  |  选中行后 Ctrl+C 可复制", font=("Microsoft YaHei", 10), fg="#94a3b8", bg="#0f172a").pack(padx=16, pady=(0, 8), anchor="w")
        
        # 列表区域（Treeview）
        frame = tk.Frame(popup, bg="white")
        frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        tree = ttk.Treeview(frame, columns=columns, show="headings", yscrollcommand=scrollbar.set, selectmode="extended")
        scrollbar.config(command=tree.yview)
        
        col_widths = {
            "专利号": 145, "名称": 320, "申请单位": 240, "URL": 300, "关系": 65
        }
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=col_widths.get(col, 150))
        
        # 填充数据
        for i, item in enumerate(items):
            if isinstance(item, dict):
                title = item.get("title", "") or "待抓取"
                applicant = item.get("applicant", "") or "---"
                rel = item.get("relation", "")
                if rel:
                    applicant = f"[{rel}] {applicant}"
                values = [item.get("patent_number", ""),
                          title,
                          applicant,
                          item.get("google_url", "")]
                tree.insert("", tk.END, values=values, tags=("row",))
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                url = item[0] if len(item) > 0 else ""
                tree.insert("", tk.END, values=("", "", "", url), tags=("row",))
        
        tree.tag_configure("row", font=("Consolas", 9))
        tree.pack(fill=tk.BOTH, expand=True)
        
        # 导出按钮
        def export_csv():
            from tkinter import filedialog
            import csv
            fp = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
            if fp:
                with open(fp, "w", encoding="utf-8-sig", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(columns)
                    for item in items:
                        if isinstance(item, dict):
                            writer.writerow([item.get("patent_number", ""),
                                             item.get("title", ""),
                                             item.get("applicant", ""),
                                             item.get("google_url", "")])
                        elif isinstance(item, (list, tuple)):
                            writer.writerow(["", "", "", item[0]])
                popup.title(f"{title} - 已导出")
        
        btn_frame = tk.Frame(popup, bg="white")
        btn_frame.pack(fill=tk.X, padx=8, pady=(0, 8))
        tk.Button(btn_frame, text="导出 CSV", command=export_csv,
                  bg="#059669", fg="white", font=("Microsoft YaHei", 9), relief="flat", padx=15, pady=4, cursor="hand2").pack(side=tk.LEFT)
    
    def make_card_clickable(frame, label, data_key, columns):
        """让统计卡片可点击"""
        def on_enter(e):
            frame.config(bg="#f1f5f9")
            for child in frame.winfo_children():
                try: child.config(bg="#f1f5f9")
                except: pass
        def on_leave(e):
            frame.config(bg="white")
            for child in frame.winfo_children():
                try: child.config(bg="white")
                except: pass
        def on_click(e):
            items = stored_data.get(data_key, [])
            if not items:
                messagebox.showinfo("提示", f"暂无{label}数据")
                return
            show_popup(f"{label} 列表 ({len(items)} 条)", items, columns)
        
        frame.bind("<Enter>", on_enter)
        frame.bind("<Leave>", on_leave)
        frame.bind("<Button-1>", on_click)
        for child in frame.winfo_children():
            child.bind("<Button-1>", on_click)
            child.bind("<Enter>", on_enter)
            child.bind("<Leave>", on_leave)
        frame.config(cursor="hand2")
        for child in frame.winfo_children():
            child.config(cursor="hand2")
        card_frames[label] = frame

    card_configs = [
        ("已访问", "#3b82f6", "🔍", "visited_records", ["专利号", "名称", "申请单位", "URL"]),
        ("低空相关", "#059669", "🟢", "lowalt_records", ["专利号", "名称", "申请单位", "URL"]),
        ("后备池", "#d97706", "📋", "backlog_records", ["专利号", "名称", "申请单位", "URL"]),
        ("已入库", "#8b5cf6", "💾", "saved_records", ["专利号", "名称", "申请单位", "URL"]),
    ]
    for label, color, icon, data_key, cols in card_configs:
        f = tk.Frame(cards, bg="white", relief="solid", bd=0, highlightbackground="#e2e8f0", highlightthickness=1)
        f.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=3)
        tk.Label(f, text=icon, font=("", 16), bg="white").pack(pady=(8, 0))
        n = tk.Label(f, text="0", font=("Consolas", 22, "bold"), fg=color, bg="white")
        n.pack()
        tk.Label(f, text=label, font=("Microsoft YaHei", 9), fg="#64748b", bg="white").pack(pady=(0, 8))
        tk.Label(f, text="点击查看详情", font=("Microsoft YaHei", 7), fg="#94a3b8", bg="white").pack(pady=(0, 4))
        stat_widgets[label] = n
        make_card_clickable(f, label, data_key, cols)

    # 待处理队列
    queue_frame = tk.Frame(root, bg="white", relief="solid", bd=0, highlightbackground="#e2e8f0", highlightthickness=1)
    queue_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
    tk.Label(queue_frame, text="⏳ 待链式检索", font=("Microsoft YaHei", 10, "bold"), fg="#0f172a", bg="white").pack(anchor="w", padx=10, pady=(8, 0))
    queue_text = tk.Text(queue_frame, height=3, font=("Consolas", 8), bg="#fffbeb", fg="#92400e", relief="flat", state="disabled")
    queue_text.pack(fill=tk.X, padx=8, pady=(2, 8))

    # ═══════════════ 中间两栏 ═══════════════
    mid = tk.Frame(root, bg="#f0f2f5")
    mid.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    # 左: 处理日志
    left = tk.Frame(mid, bg="white", relief="solid", bd=0, highlightbackground="#e2e8f0", highlightthickness=1)
    left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
    tk.Label(left, text="📡 实时处理日志", font=("Microsoft YaHei", 10, "bold"), fg="#0f172a", bg="white").pack(anchor="w", padx=10, pady=(8, 2))
    log_text = tk.Text(left, font=("Consolas", 9), bg="#f8fafc", fg="#334155", relief="flat", state="disabled", wrap="word")
    log_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

    # 右: 低空发现
    right = tk.Frame(mid, bg="white", relief="solid", bd=0, highlightbackground="#e2e8f0", highlightthickness=1)
    right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
    tk.Label(right, text="🎯 低空经济专利发现", font=("Microsoft YaHei", 10, "bold"), fg="#059669", bg="white").pack(anchor="w", padx=10, pady=(8, 2))
    found_text = tk.Text(right, font=("Consolas", 9), bg="#f0fdf4", fg="#166534", relief="flat", state="disabled", wrap="word")
    found_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

    # ═══════════════ 底部状态栏 ═══════════════
    status_bar = tk.Frame(root, bg="#f0f2f5")
    status_bar.pack(fill=tk.X, padx=10, pady=(0, 5))
    progress = ttk.Progressbar(status_bar, mode="determinate")
    progress.pack(fill=tk.X, side=tk.LEFT, expand=True)
    status_label = tk.Label(status_bar, text="就绪", font=("Microsoft YaHei", 9), fg="#64748b", bg="#f0f2f5", width=30, anchor="e")
    status_label.pack(side=tk.RIGHT)

    crawler_ref = [None]

    def log(text, color="#334155", tag=None):
        root.after(0, lambda: _log(text, color, tag))

    def _log(text, color, tag):
        log_text.config(state="normal")
        log_text.insert(tk.END, text + "\n", tag)
        if tag:
            log_text.tag_config(tag, foreground=color)
        log_text.see(tk.END)
        log_text.config(state="disabled")

    def found(text, color="#166534"):
        root.after(0, lambda: _found(text, color))

    def _found(text, color):
        found_text.config(state="normal")
        found_text.insert(tk.END, text + "\n")
        found_text.see(tk.END)
        found_text.config(state="disabled")

    def update_gui(data):
        def _update(data):
            stat_widgets["已访问"].config(text=str(data["visited"]))
            stat_widgets["低空相关"].config(text=str(data["matched"]))
            stat_widgets["后备池"].config(text=str(data["backlog"]))
            stat_widgets["已入库"].config(text=str(data["saved"]))
            progress["maximum"] = int(max_var.get())
            progress["value"] = min(data["visited"], int(max_var.get()))
            status_label.config(text=f"活跃队列: {data.get('active', '?')} | 已访问 {data['visited']}/{max_var.get()}")

            # 更新详情数据
            for key in ["visited_records", "lowalt_records", "backlog_records", "saved_records"]:
                if key in data:
                    stored_data[key] = data[key]

            next_up = data.get("active_next", [])
            if next_up:
                queue_text.config(state="normal")
                queue_text.delete(1.0, tk.END)
                queue_text.insert(tk.END, ", ".join(next_up))
                queue_text.config(state="disabled")

            rec = data.get("latest_record")
            if rec:
                pn = rec.get("patent_number", "")
                title = rec.get("title", "")[:55]
                applicant = rec.get("applicant", "")[:30]
                is_lowalt = data.get("is_lowalt", False)
                rel = data.get("relation", "")
                log(f"{pn} [{rel}] {applicant}", color="#059669" if is_lowalt else "#94a3b8")
                if is_lowalt:
                    found(f"✅ {pn}\n   {title}\n   {applicant}", "#166534")

        root.after(0, _update, data)

    def start():
        seed = seed_entry.get().strip()
        if not seed:
            messagebox.showwarning("提示", "请输入种子 URL")
            return
        maxv = int(max_var.get())
        start_btn.config(state="disabled")
        stop_btn.config(state="normal")
        seed_entry.config(state="readonly")

        log_text.config(state="normal"); log_text.delete(1.0, tk.END); log_text.config(state="disabled")
        found_text.config(state="normal"); found_text.delete(1.0, tk.END); found_text.config(state="disabled")

        crawler_ref[0] = PatentCrawler(gui_callback=update_gui)

        def run():
            result = crawler_ref[0].crawl(seed, maxv)
            if export_var.get():
                path = crawler_ref[0].export_json()
                log(f"\n📄 JSON 已导出: {path}", "#059669")
            root.after(0, lambda: [
                start_btn.config(state="normal", text="✅ 完成"),
                stop_btn.config(state="disabled"),
                seed_entry.config(state="normal"),
                status_label.config(text=f"已完成: 访问{result['visited']} | 低空{result['lowalt']} | 入库{result['saved']} | 后备{result['backlog']}")
            ])

        threading.Thread(target=run, daemon=True).start()

    def stop():
        if crawler_ref[0]:
            crawler_ref[0].running = False
        stop_btn.config(state="disabled")
        start_btn.config(state="normal", text="🚀 开始爬取")
        seed_entry.config(state="normal")
        status_label.config(text="已停止")

    start_btn.config(command=start)
    stop_btn.config(command=stop)
    root.mainloop()
