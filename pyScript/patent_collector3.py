import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import requests
from bs4 import BeautifulSoup
import os
import re
import json
import threading
import queue
import time
import pandas as pd
from urllib.parse import urljoin

# ================= 配置与全局常量 =================
BASE_REPO_DIR = "./Patents"
SKIPPED_FILE = os.path.join(BASE_REPO_DIR, "skipped_patents.json")
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
}

# 确保基础目录存在
if not os.path.exists(BASE_REPO_DIR):
    os.makedirs(BASE_REPO_DIR)

# ================= 核心逻辑：爬虫类 =================
class PatentScraper:
    def __init__(self, update_callback=None):
        self.update_callback = update_callback

    def log(self, msg):
        if self.update_callback:
            self.update_callback(msg)
        print(msg)

    def clean_text(self, text):
        if not text: return ""
        return re.sub(r'\s+', ' ', text).strip()

    def download_file(self, url, save_path):
        """通用文件下载，支持断点跳过"""
        if os.path.exists(save_path):
            self.log(f"   [跳过] 文件已存在: {os.path.basename(save_path)}")
            return True
        try:
            resp = requests.get(url, headers=HEADERS, stream=True, timeout=30)
            resp.raise_for_status()
            with open(save_path, 'wb') as f:
                for chunk in resp.iter_content(8192):
                    f.write(chunk)
            return True
        except Exception as e:
            self.log(f"   [错误] 下载失败 {url}: {e}")
            return False

    def scrape_patent(self, patent_url):
        """核心采集逻辑"""
        # 1. 解析 Patent ID
        try:
            parts = [p for p in patent_url.split('/') if p]
            if 'patent' in parts:
                idx = parts.index('patent')
                patent_id = parts[idx+1] if idx + 1 < len(parts) else parts[-1]
            else:
                patent_id = parts[-1]
            # 去除语言后缀
            if patent_id.lower() in ['zh', 'en', 'de', 'jp']:
                patent_id = parts[-2]
        except Exception as e:
            self.log(f"[错误] 链接解析失败: {patent_url}")
            return False

        # 2. 创建文件夹
        save_dir = os.path.join(BASE_REPO_DIR, f"{patent_id}_data")
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        json_path = os.path.join(save_dir, "metadata.json")
        self.log(f"正在分析: {patent_id} ...")
        
        try:
            resp = requests.get(patent_url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            resp.encoding = 'utf-8'
            soup = BeautifulSoup(resp.text, 'html.parser')
        except Exception as e:
            self.log(f"[失败] 无法访问网页: {e}")
            return False

        # --- A. 提取基础元数据 ---
        title = "Unknown Title"
        h1_tag = soup.find('h1')
        if h1_tag: title = self.clean_text(h1_tag.get_text())

        # 提取 Assignee
        assignee = "Unknown"
        assignee_meta = soup.find('meta', {'scheme': 'assignee'})
        if assignee_meta:
            assignee = assignee_meta.get('content')
        else:
            for elem in soup.find_all(string=re.compile("Current Assignee")):
                parent = elem.find_parent()
                if parent:
                    assignee = self.clean_text(parent.get_text().replace("Current Assignee", "").replace(":", ""))
                    break

        # 提取 Inventor
        inventor = "Unknown"
        for elem in soup.find_all(string=re.compile("Inventor")):
            parent = elem.find_parent()
            if parent:
                full_text = self.clean_text(parent.get_text())
                if "Inventor" in full_text:
                    inventor = full_text.split("Inventor")[-1].replace(":", "").strip()
                break

        # 提取 Status
        status = "Unknown"
        status_elems = soup.find_all(string=re.compile("^Status"))
        for elem in status_elems:
            parent = elem.find_parent()
            text = self.clean_text(parent.get_text())
            if "Status" in text:
                cleaned = text.replace("Status", "").strip()
                cleaned = re.sub(r'^[•\-\:]\s*', '', cleaned)
                if cleaned:
                    status = cleaned
                    break

        # --- B. 提取引用 (Tables) ---
        citations = self.extract_table_data(soup, "backwardReferences")
        cited_by = self.extract_table_data(soup, "forwardReferences")
        similar_docs = self.extract_similar_docs(soup)

        # 构造完整元数据
        metadata = {
            "patent_id": patent_id,
            "title": title,
            "status": status,
            "assignee": assignee,
            "inventor": inventor,
            "url": patent_url,
            "citations": citations,
            "cited_by": cited_by,
            "similar_documents": similar_docs,
            "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        # 保存 JSON
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=4)
        
        # --- C. 下载文件 ---
        # 1. Abstract
        abs_path = os.path.join(save_dir, 'abstract.txt')
        if not os.path.exists(abs_path):
            abstract_text = "N/A"
            abs_section = soup.find('section', {'itemprop': 'abstract'})
            if abs_section:
                abstract_text = abs_section.get_text(separator="\n", strip=True)
                if abstract_text.lower().startswith("abstract"): abstract_text = abstract_text[8:].strip()
            with open(abs_path, 'w', encoding='utf-8') as f:
                f.write(f"URL: {patent_url}\n\n{abstract_text}")

        # 2. PDF
        pdf_path = os.path.join(save_dir, f"{patent_id}.pdf")
        if not os.path.exists(pdf_path):
            pdf_link = None
            for a in soup.find_all('a', href=re.compile(r'\.pdf$')):
                pdf_link = a['href']
                break
            if pdf_link:
                self.log(f"   [下载] PDF...")
                self.download_file(pdf_link, pdf_path)

        # 3. Description HTML + Images
        html_path = os.path.join(save_dir, 'description.html')
        if not os.path.exists(html_path):
            desc_section = soup.find('section', {'itemprop': 'description'})
            if desc_section:
                desc_img_dir = os.path.join(save_dir, 'description_images')
                if not os.path.exists(desc_img_dir): os.makedirs(desc_img_dir)
                
                # 下载内嵌图片
                for i, img in enumerate(desc_section.find_all('img')):
                    src = img.get('src')
                    if not src: continue
                    
                    img_url = src if src.startswith('http') else ('https:' + src if src.startswith('//') else 'https://patents.google.com' + src)
                    ext = 'jpg' if 'jpg' in img_url or 'jpeg' in img_url else 'png'
                    local_filename = f"desc_img_{i}.{ext}"
                    local_path = os.path.join(desc_img_dir, local_filename)
                    
                    if self.download_file(img_url, local_path):
                        img['src'] = f'./description_images/{local_filename}'
                        if 'srcset' in img.attrs: del img['srcset']
                
                # 保存HTML
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(f"<html><head><meta charset='utf-8'></head><body><h1>{patent_id}</h1>{str(desc_section)}</body></html>")

        # 4. Figures (高清附图)
        image_metas = soup.find_all('meta', {'itemprop': 'full'})
        for i, meta in enumerate(image_metas):
            img_url = meta['content']
            img_url = 'https:' + img_url if img_url.startswith('//') else img_url
            ext = 'png'
            if 'jpg' in img_url: ext = 'jpg'
            
            fig_path = os.path.join(save_dir, f"figure_{i+1}.{ext}")
            if not os.path.exists(fig_path):
                self.download_file(img_url, fig_path)

        self.log(f"[完成] {patent_id} 数据已更新")
        return True

    def extract_table_data(self, soup, itemprop):
        """提取引用表格数据 (5列)"""
        data = []
        rows = soup.find_all('tr', {'itemprop': itemprop})
        if not rows: return []
        
        for row in rows:
            cells = row.find_all('td')
            if not cells: continue
            
            # ID & Link
            link_tag = cells[0].find('a')
            pub_num = self.clean_text(cells[0].get_text())
            link = ("https://patents.google.com" + link_tag['href']) if link_tag else ""
            
            # 安全提取其他列
            priority_date = self.clean_text(cells[1].get_text()) if len(cells) > 1 else ""
            pub_date = self.clean_text(cells[2].get_text()) if len(cells) > 2 else ""
            assignee = self.clean_text(cells[3].get_text()) if len(cells) > 3 else ""
            title = self.clean_text(cells[4].get_text()) if len(cells) > 4 else ""

            data.append({
                "Publication Number": pub_num,
                "Priority Date": priority_date,
                "Publication Date": pub_date,
                "Assignee": assignee,
                "Title": title,
                "Link": link
            })
        return data

    def extract_similar_docs(self, soup):
        data = []
        section = soup.find('section', {'id': 'similarDocuments'})
        if not section: return []
        
        for row in section.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) < 3: continue
            
            pub_num = self.clean_text(cells[0].get_text())
            link_tag = cells[0].find('a')
            link = ("https://patents.google.com" + link_tag['href']) if link_tag else ""
            title = self.clean_text(cells[2].get_text())
            
            data.append({
                "Publication Number": pub_num,
                "Title": title,
                "Link": link,
                "Assignee": "N/A",
                "Priority Date": "",
                "Publication Date": self.clean_text(cells[1].get_text())
            })
        return data

# ================= GUI 主程序 =================
class PatentApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Google Patents Collector Pro - Ultimate")
        self.root.geometry("1400x850")
        
        self.scraper = PatentScraper(update_callback=self.update_log)
        self.download_queue = queue.Queue()
        self.is_downloading = False
        self.is_paused = False
        self.skip_current = False
        self.skipped_patents = self.load_skipped_list()

        self.setup_ui()
        # 启动后稍微延迟一下刷新列表，确保界面加载完成
        self.root.after(100, self.refresh_local_list)

    def load_skipped_list(self):
        if os.path.exists(SKIPPED_FILE):
            try:
                with open(SKIPPED_FILE, 'r', encoding='utf-8') as f:
                    return set(json.load(f))
            except:
                return set()
        return set()

    def save_skipped_list(self):
        with open(SKIPPED_FILE, 'w', encoding='utf-8') as f:
            json.dump(list(self.skipped_patents), f)

    def setup_ui(self):
        # 定义Treeview样式 (用于已下载行变绿)
        style = ttk.Style()
        style.map("Treeview", background=[('selected', '#0078D7')])
        
        # --- 顶部区域 ---
        top_frame = tk.Frame(self.root, pady=10)
        top_frame.pack(fill=tk.X, padx=10)
        
        tk.Label(top_frame, text="专利链接/URL:").pack(side=tk.LEFT)
        self.url_entry = tk.Entry(top_frame, width=50)
        self.url_entry.pack(side=tk.LEFT, padx=5)
        
        tk.Button(top_frame, text="单条下载", command=self.add_single_url).pack(side=tk.LEFT, padx=5)
        tk.Button(top_frame, text="导入 Excel (xlsx)", command=self.import_xlsx).pack(side=tk.LEFT, padx=20)

        # --- 中间分割区域 ---
        paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # === 左侧面板：本地库 + 统计 ===
        left_frame = tk.LabelFrame(paned, text="本地专利库 (Local Repository)")
        paned.add(left_frame, width=420)
        
        l_cols = ("ID", "Skipped", "Pending")
        self.local_tree = ttk.Treeview(left_frame, columns=l_cols, show="headings")
        self.local_tree.heading("ID", text="Patent ID")
        self.local_tree.heading("Skipped", text="不下载")
        self.local_tree.heading("Pending", text="待下载")
        
        self.local_tree.column("ID", width=160)
        self.local_tree.column("Skipped", width=80, anchor='center')
        self.local_tree.column("Pending", width=80, anchor='center')
        
        self.local_tree.pack(fill=tk.BOTH, expand=True)
        self.local_tree.bind("<<TreeviewSelect>>", self.on_local_select)
        
        tk.Button(left_frame, text="手动刷新列表", command=self.refresh_local_list).pack(fill=tk.X)

        # === 右侧面板：关联信息 ===
        right_frame = tk.LabelFrame(paned, text="关联专利信息 (Citations & Cited By)")
        paned.add(right_frame)
        
        # 增加 Status 列
        r_cols = ("ID", "Date", "Status", "Assignee", "Title", "Remark")
        self.relation_tree = ttk.Treeview(right_frame, columns=r_cols, show="headings")
        self.relation_tree.heading("ID", text="专利号")
        self.relation_tree.heading("Date", text="公开日期")
        self.relation_tree.heading("Status", text="状态")
        self.relation_tree.heading("Assignee", text="发明单位")
        self.relation_tree.heading("Title", text="名称")
        self.relation_tree.heading("Remark", text="备注/进度")
        
        self.relation_tree.column("ID", width=120)
        self.relation_tree.column("Date", width=100)
        self.relation_tree.column("Status", width=90)
        self.relation_tree.column("Assignee", width=150)
        self.relation_tree.column("Title", width=250)
        self.relation_tree.column("Remark", width=120)
        
        # 配置颜色 Tag
        self.relation_tree.tag_configure("downloaded", background="#E8F5E9") # 浅绿色：已下载
        self.relation_tree.tag_configure("skipped", foreground="#999999")   # 灰色文字：不下载

        self.relation_tree.pack(fill=tk.BOTH, expand=True)
        
        # 右侧操作栏
        action_bar = tk.Frame(right_frame)
        action_bar.pack(fill=tk.X, pady=5)
        tk.Button(action_bar, text="下载选中关联专利", command=self.download_selected_relations).pack(side=tk.LEFT, padx=5)
        tk.Button(action_bar, text="标记为[不下载]", command=self.mark_as_skipped).pack(side=tk.LEFT, padx=5)
        tk.Button(action_bar, text="取消[不下载]标记", command=self.unmark_skipped).pack(side=tk.LEFT, padx=5)

        # --- 底部：日志与控制 ---
        bottom_frame = tk.LabelFrame(self.root, text="任务控制台")
        bottom_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ctrl_frame = tk.Frame(bottom_frame)
        ctrl_frame.pack(fill=tk.X, pady=5)
        
        self.btn_start = tk.Button(ctrl_frame, text="开始处理队列", bg="#ccffcc", command=self.start_download_thread)
        self.btn_start.pack(side=tk.LEFT, padx=10)
        
        tk.Button(ctrl_frame, text="暂停", command=self.toggle_pause).pack(side=tk.LEFT, padx=5)
        tk.Button(ctrl_frame, text="跳过当前", command=self.skip_current_task).pack(side=tk.LEFT, padx=5)
        tk.Button(ctrl_frame, text="扫描未下载项 (Scan All)", command=self.load_all_undownloaded).pack(side=tk.LEFT, padx=20)
        
        self.progress_label = tk.Label(ctrl_frame, text="等待任务...")
        self.progress_label.pack(side=tk.LEFT, padx=10)
        
        self.log_text = tk.Text(bottom_frame, height=8, state='disabled')
        self.log_text.pack(fill=tk.X)

    # ================= 辅助功能 =================
    def update_log(self, msg):
        self.root.after(0, self._append_log, msg)

    def _append_log(self, msg):
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')

    def refresh_local_list(self):
        """
        [关键逻辑] 刷新左侧列表，并计算 Skipped/Pending 数量
        会被 mark_as_skipped 和 download_thread 自动调用
        """
        # 清空当前列表
        for item in self.local_tree.get_children():
            self.local_tree.delete(item)
        
        if not os.path.exists(BASE_REPO_DIR):
            return

        dirs = sorted([d for d in os.listdir(BASE_REPO_DIR) if d.endswith('_data')])
        
        for d in dirs:
            pid = d.replace('_data', '')
            json_path = os.path.join(BASE_REPO_DIR, d, "metadata.json")
            
            skipped_c = 0
            pending_c = 0
            
            if os.path.exists(json_path):
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # 合并 Citations 和 Cited By
                    all_refs = data.get('citations', []) + data.get('cited_by', [])
                    
                    # 提取所有关联的 Unique ID
                    ref_ids = set()
                    for r in all_refs:
                        rid = r.get('Publication Number')
                        if rid: ref_ids.add(rid)
                    
                    # 统计状态
                    for rid in ref_ids:
                        if rid in self.skipped_patents:
                            skipped_c += 1
                        else:
                            # 如果不在不下载名单，且本地没有文件夹，则算 Pending
                            if not os.path.exists(os.path.join(BASE_REPO_DIR, f"{rid}_data")):
                                pending_c += 1
                except Exception:
                    pass

            self.local_tree.insert("", tk.END, values=(pid, skipped_c, pending_c))

    def on_local_select(self, event):
        """左侧点击事件：加载右侧列表"""
        selected = self.local_tree.selection()
        if not selected: return
        
        pid = self.local_tree.item(selected[0])['values'][0]
        json_path = os.path.join(BASE_REPO_DIR, f"{pid}_data", "metadata.json")
        
        # 清空右侧
        for item in self.relation_tree.get_children():
            self.relation_tree.delete(item)
            
        if not os.path.exists(json_path): return
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 显示选中专利的详情日志
            self.update_log(f"=== {data.get('patent_id')} ===")
            self.update_log(f"Status: {data.get('status')} | Inventor: {data.get('inventor')}")
            
            # 加载关联列表
            all_refs = data.get('citations', []) + data.get('cited_by', [])
            
            # 去重
            seen = set()
            unique_refs = []
            for r in all_refs:
                rid = r.get('Publication Number')
                if rid and rid not in seen:
                    seen.add(rid)
                    unique_refs.append(r)
            
            for ref in unique_refs:
                rid = ref.get('Publication Number')
                status_txt = "Unknown" # 默认为表格里的未知
                remark = "未下载"
                row_tag = ""
                
                # 1. 检查是否已下载 (读取真实Status)
                local_meta = os.path.join(BASE_REPO_DIR, f"{rid}_data", "metadata.json")
                if os.path.exists(local_meta):
                    remark = "已下载"
                    row_tag = "downloaded"
                    # 尝试读取已下载的精准 Status
                    try:
                        with open(local_meta, 'r', encoding='utf-8') as lf:
                            ld = json.load(lf)
                            status_txt = ld.get('status', 'Unknown')
                            # 可选：更新其他字段为最新抓取的值
                            ref['Assignee'] = ld.get('assignee', ref.get('Assignee'))
                            ref['Title'] = ld.get('title', ref.get('Title'))
                            ref['Publication Date'] = ld.get('last_updated', ref.get('Publication Date')).split()[0]
                    except: pass
                    
                # 2. 检查是否被跳过
                elif rid in self.skipped_patents:
                    remark = "用户标记：不下载"
                    row_tag = "skipped"

                self.relation_tree.insert("", tk.END, values=(
                    rid,
                    ref.get('Publication Date', ''),
                    status_txt,
                    ref.get('Assignee', ''),
                    ref.get('Title', ''),
                    remark
                ), tags=(row_tag, ref.get('Link', '')))
                
        except Exception as e:
            self.update_log(f"加载元数据失败: {e}")

    def update_right_row_dynamic(self, downloaded_pid):
        """
        [新功能] 下载完成后，动态更新右侧对应的行状态为“已下载” (绿色)
        并填入最新的 Status 和 Assignee
        """
        for item in self.relation_tree.get_children():
            vals = self.relation_tree.item(item)['values']
            rid = vals[0]
            if rid == downloaded_pid:
                # 读取新下载的 metadata
                new_status = "Unknown"
                new_assignee = vals[3]
                new_title = vals[4]
                
                meta_path = os.path.join(BASE_REPO_DIR, f"{downloaded_pid}_data", "metadata.json")
                if os.path.exists(meta_path):
                    try:
                        with open(meta_path, 'r', encoding='utf-8') as f:
                            md = json.load(f)
                            new_status = md.get('status', 'Unknown')
                            new_assignee = md.get('assignee', new_assignee)
                            new_title = md.get('title', new_title)
                    except: pass
                
                # 更新这一行的数据
                self.relation_tree.item(item, values=(
                    rid,
                    vals[1],      # Date
                    new_status,   # Updated Status
                    new_assignee, # Updated Assignee
                    new_title,    # Updated Title
                    "已下载"       # Updated Remark
                ))
                
                # 更新颜色标签
                current_tags = list(self.relation_tree.item(item)['tags'])
                if "downloaded" not in current_tags:
                    current_tags.insert(0, "downloaded")
                # 移除 skipped 标签如果存在
                if "skipped" in current_tags:
                    current_tags.remove("skipped")
                
                self.relation_tree.item(item, tags=current_tags)
                break

    # ================= 按钮响应函数 =================
    def add_single_url(self):
        u = self.url_entry.get().strip()
        if u: 
            self.download_queue.put(u)
            self.update_log(f"加入队列: {u}")
            self.progress_label.config(text=f"队列: {self.download_queue.qsize()}")

    def import_xlsx(self):
        fp = filedialog.askopenfilename(filetypes=[("Excel Files", "*.xlsx")])
        if not fp: return
        try:
            df = pd.read_excel(fp)
            col = next((c for c in df.columns if 'link' in str(c).lower()), None)
            if not col: return messagebox.showerror("错误", "未找到包含 'link' 的列")
            c = 0
            for l in df[col]:
                if isinstance(l, str) and l.startswith('http'): 
                    self.download_queue.put(l)
                    c += 1
            self.update_log(f"导入 {c} 条链接")
            self.progress_label.config(text=f"队列: {self.download_queue.qsize()}")
        except Exception as e: messagebox.showerror("错误", str(e))

    def mark_as_skipped(self):
        selected = self.relation_tree.selection()
        if not selected: return
        for item in selected:
            pid = self.relation_tree.item(item)['values'][0]
            self.skipped_patents.add(pid)
            self.relation_tree.set(item, "Remark", "用户标记：不下载")
            self.relation_tree.item(item, tags=("skipped",))
        self.save_skipped_list()
        # [关键] 标记后立即刷新左侧统计
        self.refresh_local_list()

    def unmark_skipped(self):
        selected = self.relation_tree.selection()
        if not selected: return
        for item in selected:
            pid = self.relation_tree.item(item)['values'][0]
            if pid in self.skipped_patents:
                self.skipped_patents.remove(pid)
                self.relation_tree.set(item, "Remark", "未下载")
                self.relation_tree.item(item, tags=("",)) # 清除skipped tag
        self.save_skipped_list()
        # [关键] 取消标记后立即刷新左侧统计
        self.refresh_local_list()

    def download_selected_relations(self):
        selected = self.relation_tree.selection()
        c = 0
        for item in selected:
            v = self.relation_tree.item(item)['values']
            pid = v[0]
            tags = self.relation_tree.item(item)['tags']
            url = next((t for t in tags if t.startswith('http')), f"https://patents.google.com/patent/{pid}/zh")
            
            if pid in self.skipped_patents:
                if not messagebox.askyesno("确认", f"{pid} 在跳过列表中，是否下载？"): continue
                self.skipped_patents.remove(pid)
                self.save_skipped_list()
            
            self.download_queue.put(url)
            self.relation_tree.set(item, "Remark", "等待下载...")
            c += 1
        self.update_log(f"添加 {c} 个关联任务")

    def load_all_undownloaded(self):
        """扫描所有本地文件，找出所有未下载的关联专利"""
        self.update_log("正在全盘扫描未下载项...")
        all_refs = {}
        if os.path.exists(BASE_REPO_DIR):
            for d in os.listdir(BASE_REPO_DIR):
                if d.endswith('_data'):
                    try:
                        with open(os.path.join(BASE_REPO_DIR, d, "metadata.json"), 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            refs = data.get('citations', []) + data.get('cited_by', [])
                            for r in refs:
                                pid = r.get('Publication Number')
                                if pid and not os.path.exists(os.path.join(BASE_REPO_DIR, f"{pid}_data")):
                                    if pid not in all_refs: all_refs[pid] = r
                    except: pass
        
        # 显示到右侧
        for item in self.relation_tree.get_children(): self.relation_tree.delete(item)
        for pid, ref in all_refs.items():
            rem = "用户标记：不下载" if pid in self.skipped_patents else "未下载"
            tag = "skipped" if pid in self.skipped_patents else ""
            self.relation_tree.insert("", tk.END, values=(
                pid, ref.get('Publication Date', ''), "Unknown", ref.get('Assignee', ''), ref.get('Title', ''), rem
            ), tags=(tag, ref.get('Link', '')))
        self.update_log(f"发现 {len(all_refs)} 个全局未下载项")

    # ================= 线程控制 =================
    def start_download_thread(self):
        if self.is_downloading: return
        self.is_downloading = True
        self.is_paused = False
        self.btn_start.config(state='disabled', bg='#dddddd')
        threading.Thread(target=self.worker_thread, daemon=True).start()

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        self.update_log(f"状态切换: {'暂停' if self.is_paused else '运行中'}")

    def skip_current_task(self):
        self.skip_current = True
        self.update_log("正在跳过当前任务...")

    def worker_thread(self):
        while True:
            if self.is_paused:
                time.sleep(1)
                continue
            
            try:
                url = self.download_queue.get(timeout=2)
            except queue.Empty:
                if self.is_downloading: 
                    self.root.after(0, lambda: self.progress_label.config(text="队列空闲"))
                continue
            
            self.skip_current = False
            # 简单提取ID用于显示
            clean_id = url.split('/')[-1]
            if 'patent' in url: clean_id = url.split('/')[-2]

            self.root.after(0, lambda: self.progress_label.config(text=f"下载中: {clean_id}"))
            
            # 执行下载
            success = self.scraper.scrape_patent(url)
            
            if success:
                # 1. 下载成功，移除黑名单（如果是强制下载的情况）
                if clean_id in self.skipped_patents:
                    self.skipped_patents.remove(clean_id)
                    self.save_skipped_list()
                
                # 2. [关键] 刷新左侧列表 (Pending 数减少)
                self.root.after(0, self.refresh_local_list)
                
                # 3. [关键] 刷新右侧行状态 (变绿, 填入真实Status)
                self.root.after(0, lambda: self.update_right_row_dynamic(clean_id))
            
            self.download_queue.task_done()
            self.root.after(0, lambda: self.progress_label.config(text=f"剩余任务: {self.download_queue.qsize()}"))

if __name__ == "__main__":
    root = tk.Tk()
    app = PatentApp(root)
    root.mainloop()