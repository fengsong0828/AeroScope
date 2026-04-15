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
import platform
import subprocess

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

# ================= 核心逻辑：爬虫类 (完整无删减版) =================
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
            self.log(f"   [Skip] File exists: {os.path.basename(save_path)}")
            return True
        try:
            resp = requests.get(url, headers=HEADERS, stream=True, timeout=30)
            resp.raise_for_status()
            with open(save_path, 'wb') as f:
                for chunk in resp.iter_content(8192):
                    f.write(chunk)
            return True
        except Exception as e:
            self.log(f"   [Error] Download failed {url}: {e}")
            return False

    def scrape_patent(self, patent_url):
        """核心采集逻辑：包含元数据提取和所有文件下载"""
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
            self.log(f"[Error] URL parse failed: {patent_url}")
            return False

        # 2. 创建文件夹
        save_dir = os.path.join(BASE_REPO_DIR, f"{patent_id}_data")
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        json_path = os.path.join(save_dir, "metadata.json")
        self.log(f"Analyzing: {patent_id} ...")
        
        try:
            resp = requests.get(patent_url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            resp.encoding = 'utf-8'
            soup = BeautifulSoup(resp.text, 'html.parser')
        except Exception as e:
            self.log(f"[Fail] Web request error: {e}")
            return False

        # --- A. 提取基础元数据 ---
        
        # 标题 (Title): 优先读取 h1，保证获取完整的原始标题（含ID）
        title = "Unknown Title"
        h1_tag = soup.find('h1')
        if h1_tag: 
            title = self.clean_text(h1_tag.get_text())
        else:
            meta_title = soup.find('meta', attrs={'name': 'DC.title'})
            if meta_title: title = self.clean_text(meta_title['content'])

        # 公开日期 (Publication Date)
        pub_date = ""
        meta_date = soup.find('meta', attrs={'name': 'citation_publication_date'})
        if not meta_date:
            meta_date = soup.find('meta', attrs={'name': 'DC.date'})
        
        if meta_date:
            pub_date = meta_date['content']
        else:
            # 备用：在表格文本中查找 YYYY-MM-DD
            for cell in soup.find_all('td'):
                txt = cell.get_text().strip()
                if re.match(r'\d{4}-\d{2}-\d{2}', txt):
                    pub_date = txt
                    break

        # 申请人 (Assignee)
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

        # 发明人 (Inventor)
        inventor = "Unknown"
        for elem in soup.find_all(string=re.compile("Inventor")):
            parent = elem.find_parent()
            if parent:
                full_text = self.clean_text(parent.get_text())
                if "Inventor" in full_text:
                    inventor = full_text.split("Inventor")[-1].replace(":", "").strip()
                break

        # 状态 (Status)
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
            "publication_date": pub_date,
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
        
        # --- C. 下载文件 (完整逻辑) ---
        
        # 1. 摘要 (Abstract)
        abs_path = os.path.join(save_dir, 'abstract.txt')
        if not os.path.exists(abs_path):
            abstract_text = "N/A"
            abs_section = soup.find('section', {'itemprop': 'abstract'})
            if abs_section:
                abstract_text = abs_section.get_text(separator="\n", strip=True)
                if abstract_text.lower().startswith("abstract"): abstract_text = abstract_text[8:].strip()
            with open(abs_path, 'w', encoding='utf-8') as f:
                f.write(f"URL: {patent_url}\n\n{abstract_text}")

        # 2. PDF 文件
        pdf_path = os.path.join(save_dir, f"{patent_id}.pdf")
        if not os.path.exists(pdf_path):
            pdf_link = None
            for a in soup.find_all('a', href=re.compile(r'\.pdf$')):
                pdf_link = a['href']
                break
            if pdf_link:
                self.log(f"   [Download] PDF...")
                self.download_file(pdf_link, pdf_path)

        # 3. HTML 正文 + 内嵌图片 (Description Images)
        html_path = os.path.join(save_dir, 'description.html')
        if not os.path.exists(html_path):
            desc_section = soup.find('section', {'itemprop': 'description'})
            if desc_section:
                desc_img_dir = os.path.join(save_dir, 'description_images')
                if not os.path.exists(desc_img_dir): os.makedirs(desc_img_dir)
                
                # 遍历下载正文中的所有图片
                for i, img in enumerate(desc_section.find_all('img')):
                    src = img.get('src')
                    if not src: continue
                    
                    # 补全图片链接
                    img_url = src if src.startswith('http') else ('https:' + src if src.startswith('//') else 'https://patents.google.com' + src)
                    ext = 'jpg' if 'jpg' in img_url or 'jpeg' in img_url else 'png'
                    local_filename = f"desc_img_{i}.{ext}"
                    local_path = os.path.join(desc_img_dir, local_filename)
                    
                    if self.download_file(img_url, local_path):
                        # 修改 HTML 中的图片链接为本地路径
                        img['src'] = f'./description_images/{local_filename}'
                        if 'srcset' in img.attrs: del img['srcset']
                
                # 保存修改后的 HTML
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(f"<html><head><meta charset='utf-8'></head><body><h1>{patent_id}</h1>{str(desc_section)}</body></html>")

        # 4. 高清附图 (Full Figures)
        image_metas = soup.find_all('meta', {'itemprop': 'full'})
        for i, meta in enumerate(image_metas):
            img_url = meta['content']
            img_url = 'https:' + img_url if img_url.startswith('//') else img_url
            ext = 'png'
            if 'jpg' in img_url: ext = 'jpg'
            
            fig_path = os.path.join(save_dir, f"figure_{i+1}.{ext}")
            if not os.path.exists(fig_path):
                self.download_file(img_url, fig_path)

        self.log(f"[Success] {patent_id} Updated")
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
        self.root.geometry("1400x850")
        
        # --- UI Config ---
        self.current_lang = 'zh' # 默认中文
        self.filter_mode = 'all' # all, citations, cited_by
        self.current_refs_data = {'citations': [], 'cited_by': []} # 缓存当前选中专利的引用数据
        
        self.fonts = {
            'main': ('Segoe UI', 10),
            'bold': ('Segoe UI', 10, 'bold'),
            'mono': ('Consolas', 10),
            'header': ('Segoe UI', 11, 'bold')
        }
        self.colors = {
            'bg': '#F2F2F7',         
            'card': '#FFFFFF',       
            'text': '#1C1C1E',       
            'text_light': '#8E8E93', 
            'accent': '#007AFF',     
            'success': '#34C759',    
            'warning': '#FF3B30',    
            'border': '#E5E5EA',
            'active_filter': '#007AFF',
            'inactive_filter': '#E5E5EA'
        }
        
        self.root.configure(bg=self.colors['bg'])
        
        # --- Language Dictionary ---
        self.texts = {
            'zh': {
                'title': 'Google Patents Collector Pro - Ultimate',
                'url_label': '专利链接/URL:',
                'btn_single': '单条下载',
                'btn_import': '导入 Excel',
                'lbl_local': '本地专利库 (Local Repository)',
                'btn_refresh': '刷新列表',
                'lbl_remote': '关联专利信息',
                'btn_down_sel': '下载选中项',
                'btn_mark_skip': '标记[不下载]',
                'btn_unmark': '取消[不下载]',
                'lbl_control': '任务控制台',
                'btn_start': '▶ 开始处理',
                'btn_pause': '暂停 / 继续',
                'btn_skip': '跳过当前',
                'btn_scan': '扫描未下载项',
                'status_wait': '等待任务...',
                'status_idle': '队列空闲',
                # 更新后的列名 (名称在前，ID隐藏)
                'col_local': ["名称 (Title)", "公开日期", "待下载"], 
                'col_remote': ["专利号", "公开日期", "状态", "发明单位", "名称", "备注/进度"],
                'lang_switch': 'English',
                'filter_all': '全部关联',
                'filter_citations': '引用 (Citations)',
                'filter_citedby': '被引 (Cited By)',
                # 弹窗多语言
                'popup_title': '专利详情',
                'tab_overview': '概览',
                'tab_desc': '说明书',
                'btn_open_pdf': '📄 打开 PDF 文件',
                'lbl_assignee': '申请人:',
                'lbl_inventor': '发明人:',
                'lbl_status': '状态:',
                'lbl_abstract': '摘要:'
            },
            'en': {
                'title': 'Google Patents Collector Pro - Ultimate',
                'url_label': 'Patent URL:',
                'btn_single': 'Add Single URL',
                'btn_import': 'Import Excel',
                'lbl_local': 'Local Repository',
                'btn_refresh': 'Refresh List',
                'lbl_remote': 'Related Patents',
                'btn_down_sel': 'Download Selected',
                'btn_mark_skip': 'Mark as Skip',
                'btn_unmark': 'Unmark Skip',
                'lbl_control': 'Task Console',
                'btn_start': '▶ Start Queue',
                'btn_pause': 'Pause / Resume',
                'btn_skip': 'Skip Current',
                'btn_scan': 'Scan Missing',
                'status_wait': 'Waiting...',
                'status_idle': 'Queue Idle',
                'col_local': ["Title", "Date", "Pending"],
                'col_remote': ["ID", "Date", "Status", "Assignee", "Title", "Remark"],
                'lang_switch': '中文',
                'filter_all': 'All',
                'filter_citations': 'Citations',
                'filter_citedby': 'Cited By',
                'popup_title': 'Patent Details',
                'tab_overview': 'Overview',
                'tab_desc': 'Description',
                'btn_open_pdf': '📄 Open PDF',
                'lbl_assignee': 'Assignee:',
                'lbl_inventor': 'Inventor:',
                'lbl_status': 'Status:',
                'lbl_abstract': 'Abstract:'
            }
        }

        self.scraper = PatentScraper(update_callback=self.update_log)
        self.download_queue = queue.Queue()
        self.is_downloading = False
        self.is_paused = False
        self.skip_current = False
        self.skipped_patents = self.load_skipped_list()

        self.setup_ui()
        self.update_ui_text() 
        
        # 启动后稍微延迟一下刷新列表
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

    def create_styled_button(self, parent, key, command, bg=None, fg=None):
        """创建扁平化风格按钮的辅助函数"""
        if bg is None: bg = self.colors['card']
        if fg is None: fg = self.colors['text']
        
        btn = tk.Button(parent, text=self.texts[self.current_lang].get(key, key),
                        command=command,
                        bg=bg, fg=fg,
                        activebackground=self.colors['border'],
                        relief='flat', bd=0,
                        padx=15, pady=5,
                        font=self.fonts['main'],
                        cursor='hand2')
        btn.config(highlightbackground=self.colors['border'], highlightthickness=1)
        # Store key for dynamic text update
        btn.key = key 
        return btn

    def setup_ui(self):
        # 定义Treeview样式
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure("Treeview.Heading", 
                        background=self.colors['card'], 
                        foreground=self.colors['text_light'],
                        relief="flat",
                        font=self.fonts['bold'])
        
        style.configure("Treeview", 
                        background=self.colors['card'],
                        fieldbackground=self.colors['card'],
                        foreground=self.colors['text'],
                        rowheight=28, # 增加行高
                        borderwidth=0,
                        font=self.fonts['main'])
        
        style.map("Treeview", 
                  background=[('selected', self.colors['accent'])],
                  foreground=[('selected', '#FFFFFF')])

        # 滚动条样式
        style.configure("Vertical.TScrollbar", 
                        gripcount=0,
                        background=self.colors['bg'],
                        troughcolor=self.colors['bg'],
                        bordercolor=self.colors['bg'],
                        arrowcolor=self.colors['text_light'])

        # --- Top Frame (Top Card) ---
        top_frame = tk.Frame(self.root, pady=15, padx=15, bg=self.colors['bg'])
        top_frame.pack(fill=tk.X)
        
        self.lbl_url = tk.Label(top_frame, text="", bg=self.colors['bg'], font=self.fonts['bold'])
        self.lbl_url.pack(side=tk.LEFT)
        
        self.url_entry = tk.Entry(top_frame, width=50, font=self.fonts['main'], 
                                  relief='flat', highlightthickness=1, highlightbackground=self.colors['border'])
        self.url_entry.pack(side=tk.LEFT, padx=10, ipady=5)
        
        self.btn_single = self.create_styled_button(top_frame, 'btn_single', self.add_single_url, bg=self.colors['accent'], fg='#FFFFFF')
        self.btn_single.pack(side=tk.LEFT, padx=5)
        
        self.btn_import = self.create_styled_button(top_frame, 'btn_import', self.import_xlsx)
        self.btn_import.pack(side=tk.LEFT, padx=5)

        # 语言切换按钮 (Top Right)
        self.btn_lang = tk.Button(top_frame, text="English", command=self.toggle_language,
                                  bg=self.colors['bg'], fg=self.colors['text_light'],
                                  font=self.fonts['main'], relief='flat', bd=0, cursor='hand2')
        self.btn_lang.pack(side=tk.RIGHT)

        # --- PanedWindow (中间分割) ---
        paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, bg=self.colors['bg'], sashwidth=6, sashrelief='flat')
        paned.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)
        
        # === Left Frame: Local Repo ===
        self.left_frame = tk.LabelFrame(paned, text="", bg=self.colors['bg'], fg=self.colors['text'], font=self.fonts['header'],
                                        bd=0, highlightthickness=0)
        paned.add(self.left_frame, width=420)
        
        # 容器用于白色背景
        l_container = tk.Frame(self.left_frame, bg=self.colors['card'], bd=1, relief='solid')
        l_container.pack(fill=tk.BOTH, expand=True, padx=0, pady=(5,0))
        tk.Frame(l_container, bg=self.colors['border']).place(relx=0, rely=0, relwidth=1, relheight=1)
        l_inner = tk.Frame(l_container, bg=self.colors['card'])
        l_inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        # Columns: Title (Name), Date, Pending. (ID is hidden)
        self.local_tree = ttk.Treeview(l_inner, columns=(0,1,2), show="headings")
        self.local_tree.column(0, width=240) # Title
        self.local_tree.column(1, width=90, anchor='center') # Date
        self.local_tree.column(2, width=60, anchor='center') # Pending
        
        # 滚动条
        l_scroll = ttk.Scrollbar(l_inner, orient="vertical", command=self.local_tree.yview)
        self.local_tree.configure(yscrollcommand=l_scroll.set)
        
        self.local_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        l_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.local_tree.bind("<<TreeviewSelect>>", self.on_local_select)
        # [NEW] 绑定双击事件
        self.local_tree.bind("<Double-1>", self.on_local_double_click)
        
        self.btn_refresh = self.create_styled_button(self.left_frame, 'btn_refresh', self.refresh_local_list)
        self.btn_refresh.pack(fill=tk.X, pady=5)

        # === Right Frame: Remote Info ===
        self.right_frame = tk.LabelFrame(paned, text="", bg=self.colors['bg'], fg=self.colors['text'], font=self.fonts['header'],
                                         bd=0, highlightthickness=0)
        paned.add(self.right_frame)
        
        # Filter Buttons
        filter_frame = tk.Frame(self.right_frame, bg=self.colors['bg'])
        filter_frame.pack(fill=tk.X, pady=(0, 2))

        self.filter_var = tk.StringVar(value='all')
        
        def create_filter_btn(val, key):
            btn = tk.Radiobutton(filter_frame, text=key, variable=self.filter_var, value=val,
                                 indicatoron=0, # 去掉圆点，变为按钮样式
                                 command=self.refresh_right_view, # 点击即刷新
                                 bg=self.colors['card'], selectcolor=self.colors['active_filter'],
                                 fg=self.colors['text'], 
                                 font=self.fonts['main'], relief='flat', bd=0, padx=10, pady=3,
                                 cursor='hand2')
            btn.pack(side=tk.LEFT, padx=2)
            btn.key = key
            return btn

        self.btn_filter_all = create_filter_btn('all', 'filter_all')
        self.btn_filter_cite = create_filter_btn('citations', 'filter_citations')
        self.btn_filter_citedby = create_filter_btn('cited_by', 'filter_citedby')

        r_container = tk.Frame(self.right_frame, bg=self.colors['card'], bd=1, relief='solid')
        r_container.pack(fill=tk.BOTH, expand=True, padx=0, pady=(2,0))
        tk.Frame(r_container, bg=self.colors['border']).place(relx=0, rely=0, relwidth=1, relheight=1)
        r_inner = tk.Frame(r_container, bg=self.colors['card'])
        r_inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        
        self.relation_tree = ttk.Treeview(r_inner, columns=(0,1,2,3,4,5), show="headings")
        self.relation_tree.column(0, width=120)
        self.relation_tree.column(1, width=100)
        self.relation_tree.column(2, width=90)
        self.relation_tree.column(3, width=150)
        self.relation_tree.column(4, width=250)
        self.relation_tree.column(5, width=120)
        
        # 配置颜色 Tag
        self.relation_tree.tag_configure("downloaded", background="#E8F5E9", foreground="#1E3A2F") # 浅绿
        self.relation_tree.tag_configure("skipped", foreground="#999999")   # 灰

        r_scroll = ttk.Scrollbar(r_inner, orient="vertical", command=self.relation_tree.yview)
        self.relation_tree.configure(yscrollcommand=r_scroll.set)
        
        self.relation_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        r_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Right Action Bar
        action_bar = tk.Frame(self.right_frame, bg=self.colors['bg'])
        action_bar.pack(fill=tk.X, pady=5)
        self.btn_down_sel = self.create_styled_button(action_bar, 'btn_down_sel', self.download_selected_relations, bg=self.colors['success'], fg='#FFFFFF')
        self.btn_down_sel.pack(side=tk.LEFT, padx=5)
        self.btn_mark_skip = self.create_styled_button(action_bar, 'btn_mark_skip', self.mark_as_skipped)
        self.btn_mark_skip.pack(side=tk.LEFT, padx=5)
        self.btn_unmark = self.create_styled_button(action_bar, 'btn_unmark', self.unmark_skipped)
        self.btn_unmark.pack(side=tk.LEFT, padx=5)

        # --- Bottom Frame: Control & Log ---
        self.bottom_frame = tk.LabelFrame(self.root, text="", bg=self.colors['bg'], fg=self.colors['text'], font=self.fonts['header'],
                                          bd=0, highlightthickness=0)
        self.bottom_frame.pack(fill=tk.X, padx=15, pady=10)
        
        ctrl_frame = tk.Frame(self.bottom_frame, bg=self.colors['bg'])
        ctrl_frame.pack(fill=tk.X, pady=5)
        
        self.btn_start = self.create_styled_button(ctrl_frame, 'btn_start', self.start_download_thread, bg=self.colors['accent'], fg='#FFFFFF')
        self.btn_start.pack(side=tk.LEFT, padx=10)
        
        self.btn_pause = self.create_styled_button(ctrl_frame, 'btn_pause', self.toggle_pause)
        self.btn_pause.pack(side=tk.LEFT, padx=5)
        
        self.btn_skip = self.create_styled_button(ctrl_frame, 'btn_skip', self.skip_current_task, bg=self.colors['warning'], fg='#FFFFFF')
        self.btn_skip.pack(side=tk.LEFT, padx=5)
        
        self.btn_scan = self.create_styled_button(ctrl_frame, 'btn_scan', self.load_all_undownloaded)
        self.btn_scan.pack(side=tk.LEFT, padx=20)
        
        self.progress_label = tk.Label(ctrl_frame, text="", bg=self.colors['bg'], font=self.fonts['mono'], fg=self.colors['text_light'])
        self.progress_label.pack(side=tk.LEFT, padx=10)
        
        # Log Text (Card style)
        log_container = tk.Frame(self.bottom_frame, bg=self.colors['card'], bd=1, relief='solid')
        log_container.pack(fill=tk.X, pady=5)
        tk.Frame(log_container, bg=self.colors['border']).place(relx=0, rely=0, relwidth=1, relheight=1) # border hack
        
        self.log_text = tk.Text(log_container, height=8, state='disabled', 
                                font=self.fonts['mono'], bg=self.colors['card'], fg=self.colors['text'],
                                relief='flat', bd=5)
        self.log_text.pack(fill=tk.X, padx=1, pady=1)

    def toggle_language(self):
        self.current_lang = 'en' if self.current_lang == 'zh' else 'zh'
        self.update_ui_text()

    def update_ui_text(self):
        t = self.texts[self.current_lang]
        
        self.root.title(t['title'])
        self.lbl_url.config(text=t['url_label'])
        
        # Update styled buttons
        for btn in [self.btn_single, self.btn_import, self.btn_refresh, self.btn_down_sel, self.btn_mark_skip, self.btn_unmark, self.btn_start, self.btn_pause, self.btn_skip, self.btn_scan]:
            if hasattr(btn, 'key') and btn.key in t:
                btn.config(text=t[btn.key])

        self.btn_lang.config(text=t['lang_switch'])
        self.left_frame.config(text=t['lbl_local'])
        self.right_frame.config(text=t['lbl_remote'])
        self.bottom_frame.config(text=t['lbl_control'])

        # Update filter buttons
        self.btn_filter_all.config(text=t['filter_all'])
        self.btn_filter_cite.config(text=t['filter_citations'])
        self.btn_filter_citedby.config(text=t['filter_citedby'])
        
        for i, col_name in enumerate(t['col_local']):
            self.local_tree.heading(i, text=col_name)
        for i, col_name in enumerate(t['col_remote']):
            self.relation_tree.heading(i, text=col_name)

        if not self.is_downloading:
            self.progress_label.config(text=t['status_wait'])

    # ================= 辅助功能 =================
    def update_log(self, msg):
        self.root.after(0, self._append_log, msg)

    def _append_log(self, msg):
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')

    def open_file_in_system(self, filepath):
        """Cross-platform file opener"""
        if platform.system() == 'Windows':
            os.startfile(filepath)
        elif platform.system() == 'Darwin':
            subprocess.call(('open', filepath))
        else:
            subprocess.call(('xdg-open', filepath))

    def on_local_double_click(self, event):
        """[NEW] Double click handler for popup"""
        selected = self.local_tree.selection()
        if not selected: return
        pid = selected[0]
        self.show_detail_popup(pid)

    def show_detail_popup(self, pid):
        """[NEW] Display detailed info popup"""
        t = self.texts[self.current_lang]
        
        # Load Data
        base_path = os.path.join(BASE_REPO_DIR, f"{pid}_data")
        json_path = os.path.join(base_path, "metadata.json")
        abs_path = os.path.join(base_path, "abstract.txt")
        desc_path = os.path.join(base_path, "description.html")
        pdf_path = os.path.join(base_path, f"{pid}.pdf")
        
        if not os.path.exists(json_path): return
        
        with open(json_path, 'r', encoding='utf-8') as f:
            meta = json.load(f)
            
        # Create Window
        top = tk.Toplevel(self.root)
        top.title(f"{t['popup_title']} - {pid}")
        top.geometry("900x700")
        top.configure(bg=self.colors['bg'])
        
        # Header
        header = tk.Frame(top, bg=self.colors['card'], padx=20, pady=15)
        header.pack(fill=tk.X)
        
        tk.Label(header, text=meta.get('title', pid), font=('Segoe UI', 14, 'bold'), bg=self.colors['card'], fg=self.colors['text'], wraplength=800, justify='left').pack(anchor='w')
        
        info_frame = tk.Frame(header, bg=self.colors['card'], pady=5)
        info_frame.pack(anchor='w', fill=tk.X)
        
        def add_info(label, value):
            f = tk.Frame(info_frame, bg=self.colors['card'])
            f.pack(side=tk.LEFT, padx=(0, 20))
            tk.Label(f, text=label, font=('Segoe UI', 9, 'bold'), fg=self.colors['text_light'], bg=self.colors['card']).pack(side=tk.LEFT)
            tk.Label(f, text=value, font=('Segoe UI', 9), fg=self.colors['text'], bg=self.colors['card']).pack(side=tk.LEFT, padx=5)

        add_info(t['lbl_assignee'], meta.get('assignee', 'N/A'))
        add_info(t['lbl_inventor'], meta.get('inventor', 'N/A'))
        add_info(t['lbl_status'], meta.get('status', 'N/A'))

        # Tabs
        nb = ttk.Notebook(top)
        nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tab 1: Overview (Abstract + PDF Button)
        f_overview = tk.Frame(nb, bg=self.colors['bg'], padx=15, pady=15)
        nb.add(f_overview, text=t['tab_overview'])
        
        # Abstract
        tk.Label(f_overview, text=t['lbl_abstract'], font=('Segoe UI', 11, 'bold'), bg=self.colors['bg']).pack(anchor='w')
        
        txt_abstract = tk.Text(f_overview, height=10, font=('Segoe UI', 11), wrap=tk.WORD, relief='flat', padx=10, pady=10)
        txt_abstract.pack(fill=tk.X, pady=(5, 15))
        
        if os.path.exists(abs_path):
            with open(abs_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Remove URL line if present
                if content.startswith("URL:"):
                    content = content.split("\n\n", 1)[-1]
                txt_abstract.insert(tk.END, content)
        else:
            txt_abstract.insert(tk.END, "No abstract available.")
        txt_abstract.config(state='disabled')
        
        # PDF Button
        if os.path.exists(pdf_path):
            btn_pdf = tk.Button(f_overview, text=t['btn_open_pdf'], 
                                command=lambda: self.open_file_in_system(os.path.abspath(pdf_path)),
                                bg=self.colors['accent'], fg='#FFFFFF', font=('Segoe UI', 11, 'bold'),
                                padx=20, pady=10, relief='flat', cursor='hand2')
            btn_pdf.pack(anchor='w')
        else:
            tk.Label(f_overview, text="[No PDF Available]", fg=self.colors['text_light'], bg=self.colors['bg']).pack(anchor='w')

        # Tab 2: Description (HTML Text)
        f_desc = tk.Frame(nb, bg=self.colors['bg'])
        nb.add(f_desc, text=t['tab_desc'])
        
        txt_desc = tk.Text(f_desc, font=('Segoe UI', 10), wrap=tk.WORD, relief='flat', padx=10, pady=10)
        scroll_desc = ttk.Scrollbar(f_desc, orient="vertical", command=txt_desc.yview)
        txt_desc.configure(yscrollcommand=scroll_desc.set)
        
        txt_desc.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_desc.pack(side=tk.RIGHT, fill=tk.Y)
        
        if os.path.exists(desc_path):
            try:
                with open(desc_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                    soup = BeautifulSoup(html_content, 'html.parser')
                    # Extract text properly
                    clean_text = soup.get_text(separator='\n\n')
                    txt_desc.insert(tk.END, clean_text)
            except Exception as e:
                txt_desc.insert(tk.END, f"Error loading description: {e}")
        else:
            txt_desc.insert(tk.END, "No description available.")
        txt_desc.config(state='disabled')

    def refresh_local_list(self):
        """
        Refreshes the Left Treeview with ID, Date, Pending, Title.
        Reads local metadata.json for details.
        """
        for item in self.local_tree.get_children():
            self.local_tree.delete(item)
        
        if not os.path.exists(BASE_REPO_DIR):
            return

        dirs = sorted([d for d in os.listdir(BASE_REPO_DIR) if d.endswith('_data')])
        
        for d in dirs:
            pid = d.replace('_data', '')
            json_path = os.path.join(BASE_REPO_DIR, d, "metadata.json")
            
            pending_c = 0
            title_text = ""
            date_text = ""
            
            if os.path.exists(json_path):
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # [Modify] Keep the raw title (prefix included)
                    title_text = data.get('title', pid)
                    date_text = data.get('publication_date', '')
                    
                    all_refs = data.get('citations', []) + data.get('cited_by', [])
                    ref_ids = set()
                    for r in all_refs:
                        rid = r.get('Publication Number')
                        if rid: ref_ids.add(rid)
                    
                    for rid in ref_ids:
                        if rid not in self.skipped_patents:
                            if not os.path.exists(os.path.join(BASE_REPO_DIR, f"{rid}_data")):
                                pending_c += 1
                except Exception:
                    pass

            self.local_tree.insert("", tk.END, iid=pid, values=(title_text, date_text, pending_c))

    def on_local_select(self, event):
        """Modified to load data into memory and then refresh view based on filter"""
        selected = self.local_tree.selection()
        if not selected: return
        
        pid = self.local_tree.item(selected[0])['values'][0]
        json_path = os.path.join(BASE_REPO_DIR, f"{pid}_data", "metadata.json")
        
        if not os.path.exists(json_path): return
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.update_log(f"=== {data.get('patent_id')} ===")
            self.update_log(f"Title: {data.get('title')}")
            
            self.current_refs_data['citations'] = data.get('citations', [])
            self.current_refs_data['cited_by'] = data.get('cited_by', [])
            
            self.refresh_right_view()
                
        except Exception as e:
            self.update_log(f"Error: {e}")

    def refresh_right_view(self):
        """Clears tree and populates based on filter_var and current_refs_data"""
        # 清空当前列表
        for item in self.relation_tree.get_children():
            self.relation_tree.delete(item)
            
        mode = self.filter_var.get()
        target_list = []
        
        if mode == 'citations':
            target_list = self.current_refs_data['citations']
        elif mode == 'cited_by':
            target_list = self.current_refs_data['cited_by']
        else: # all
            target_list = self.current_refs_data['citations'] + self.current_refs_data['cited_by']

        # 去重并处理
        seen = set()
        unique_refs = []
        for r in target_list:
            rid = r.get('Publication Number')
            if rid and rid not in seen:
                seen.add(rid)
                unique_refs.append(r)
        
        for ref in unique_refs:
            rid = ref.get('Publication Number')
            status_txt = "Unknown" 
            remark = "" # Default empty
            row_tag = ""
            
            local_meta = os.path.join(BASE_REPO_DIR, f"{rid}_data", "metadata.json")
            if os.path.exists(local_meta):
                remark = "Done" if self.current_lang == 'en' else "已下载"
                row_tag = "downloaded"
                try:
                    with open(local_meta, 'r', encoding='utf-8') as lf:
                        ld = json.load(lf)
                        status_txt = ld.get('status', 'Unknown')
                        ref['Assignee'] = ld.get('assignee', ref.get('Assignee'))
                        ref['Title'] = ld.get('title', ref.get('Title'))
                except: pass
            elif rid in self.skipped_patents:
                remark = "Skipped" if self.current_lang == 'en' else "不下载"
                row_tag = "skipped"
            
            # Pending stays empty

            self.relation_tree.insert("", tk.END, values=(
                rid,
                ref.get('Publication Date', ''),
                status_txt,
                ref.get('Assignee', ''),
                ref.get('Title', ''),
                remark
            ), tags=(row_tag, ref.get('Link', '')))

    def update_right_row_dynamic(self, downloaded_pid):
        for item in self.relation_tree.get_children():
            vals = self.relation_tree.item(item)['values']
            rid = vals[0]
            if rid == downloaded_pid:
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
                
                done_text = "Done" if self.current_lang == 'en' else "已下载"
                
                self.relation_tree.item(item, values=(
                    rid,
                    vals[1],      
                    new_status,   
                    new_assignee, 
                    new_title,    
                    done_text      
                ))
                
                current_tags = list(self.relation_tree.item(item)['tags'])
                if "downloaded" not in current_tags:
                    current_tags.insert(0, "downloaded")
                if "skipped" in current_tags:
                    current_tags.remove("skipped")
                
                self.relation_tree.item(item, tags=current_tags)
                break

    # ================= 按钮响应函数 =================
    def add_single_url(self):
        u = self.url_entry.get().strip()
        if u: 
            self.download_queue.put(u)
            self.update_log(f"Queue Add: {u}")
            self.progress_label.config(text=f"Q: {self.download_queue.qsize()}")

    def import_xlsx(self):
        fp = filedialog.askopenfilename(filetypes=[("Excel Files", "*.xlsx")])
        if not fp: return
        try:
            df = pd.read_excel(fp)
            col = next((c for c in df.columns if 'link' in str(c).lower()), None)
            if not col: return messagebox.showerror("Error", "No 'link' column found")
            c = 0
            for l in df[col]:
                if isinstance(l, str) and l.startswith('http'): 
                    self.download_queue.put(l)
                    c += 1
            self.update_log(f"Imported {c} URLs")
            self.progress_label.config(text=f"Q: {self.download_queue.qsize()}")
        except Exception as e: messagebox.showerror("Error", str(e))

    def mark_as_skipped(self):
        selected = self.relation_tree.selection()
        if not selected: return
        txt = "Skipped" if self.current_lang == 'en' else "不下载"
        for item in selected:
            pid = self.relation_tree.item(item)['values'][0]
            self.skipped_patents.add(pid)
            self.relation_tree.set(item, 5, txt)
            self.relation_tree.item(item, tags=("skipped",))
        self.save_skipped_list()
        self.refresh_local_list()

    def unmark_skipped(self):
        selected = self.relation_tree.selection()
        if not selected: return
        txt = "" # Empty for pending
        for item in selected:
            pid = self.relation_tree.item(item)['values'][0]
            if pid in self.skipped_patents:
                self.skipped_patents.remove(pid)
                self.relation_tree.set(item, 5, txt)
                self.relation_tree.item(item, tags=("",))
        self.save_skipped_list()
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
                msg = f"{pid} is skipped. Download anyway?" if self.current_lang == 'en' else f"{pid} 已被标记跳过，确认强制下载？"
                if not messagebox.askyesno("Confirm", msg): continue
                self.skipped_patents.remove(pid)
                self.save_skipped_list()
            
            self.download_queue.put(url)
            txt = "Queued" if self.current_lang == 'en' else "已加入队列"
            self.relation_tree.set(item, 5, txt)
            c += 1
        self.update_log(f"Added {c} tasks")

    def load_all_undownloaded(self):
        self.update_log("Scanning..." if self.current_lang == 'en' else "正在全盘扫描...")
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
        
        self.current_refs_data['citations'] = list(all_refs.values())
        self.current_refs_data['cited_by'] = []
        self.filter_var.set('all')
        self.refresh_right_view()
        
        self.update_log(f"Found {len(all_refs)} items")

    # ================= 线程控制 =================
    def start_download_thread(self):
        if self.is_downloading: return
        self.is_downloading = True
        self.is_paused = False
        self.btn_start.config(state='disabled', bg='#E5E5EA')
        threading.Thread(target=self.worker_thread, daemon=True).start()

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        status = "Paused" if self.is_paused else "Running"
        self.update_log(f"System {status}")

    def skip_current_task(self):
        self.skip_current = True
        self.update_log("Skipping..." if self.current_lang == 'en' else "正在跳过...")

    def worker_thread(self):
        while True:
            if self.is_paused:
                time.sleep(1)
                continue
            
            try:
                url = self.download_queue.get(timeout=2)
            except queue.Empty:
                if self.is_downloading: 
                    txt = self.texts[self.current_lang]['status_idle']
                    self.root.after(0, lambda: self.progress_label.config(text=txt))
                continue
            
            self.skip_current = False
            clean_id = url.split('/')[-1]
            if 'patent' in url: clean_id = url.split('/')[-2]

            msg = f"Downloading: {clean_id}" if self.current_lang == 'en' else f"下载中: {clean_id}"
            self.root.after(0, lambda: self.progress_label.config(text=msg))
            
            success = self.scraper.scrape_patent(url)
            
            if success:
                if clean_id in self.skipped_patents:
                    self.skipped_patents.remove(clean_id)
                    self.save_skipped_list()
                
                self.root.after(0, self.refresh_local_list)
                self.root.after(0, lambda: self.update_right_row_dynamic(clean_id))
            
            self.download_queue.task_done()
            rem_txt = f"Remain: {self.download_queue.qsize()}" if self.current_lang == 'en' else f"剩余: {self.download_queue.qsize()}"
            self.root.after(0, lambda: self.progress_label.config(text=rem_txt))

if __name__ == "__main__":
    root = tk.Tk()
    app = PatentApp(root)
    root.mainloop()