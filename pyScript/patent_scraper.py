import sys
import os
import re
import json
import threading
import queue
import time
import requests
import pandas as pd
from urllib.parse import urljoin
from bs4 import BeautifulSoup

# ================= 配置与全局常量 =================
# 自动定位到上一级目录的 Patents 文件夹
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_REPO_DIR = os.path.join(os.path.dirname(CURRENT_DIR), "Patents")
SKIPPED_FILE = os.path.join(BASE_REPO_DIR, "skipped_patents.json")

# 伪装请求头
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
}

# 确保基础目录存在
if not os.path.exists(BASE_REPO_DIR):
    os.makedirs(BASE_REPO_DIR)

# ================= 核心逻辑：爬虫类 (保持原有逻辑) =================
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
        if os.path.exists(save_path):
            self.log(f"   [Skip] File exists: {os.path.basename(save_path)}")
            return True
        try:
            # 处理相对路径
            if url.startswith('//'): url = 'https:' + url
            if not url.startswith('http'): url = 'https://patents.google.com' + url
            
            resp = requests.get(url, headers=HEADERS, stream=True, timeout=60)
            resp.raise_for_status()
            with open(save_path, 'wb') as f:
                for chunk in resp.iter_content(8192):
                    f.write(chunk)
            return True
        except Exception as e:
            self.log(f"   [Error] Download failed {url}: {e}")
            return False

    def scrape_patent(self, patent_url):
        # 1. 解析专利号
        try:
            parts = [p for p in patent_url.split('/') if p]
            if 'patent' in parts:
                idx = parts.index('patent')
                patent_id = parts[idx+1] if idx + 1 < len(parts) else parts[-1]
            else:
                patent_id = parts[-1]
            # 移除语言后缀 (如 /zh, /en)
            if patent_id.lower() in ['zh', 'en', 'de', 'jp']:
                patent_id = parts[-2]
            # 清理 URL 参数
            patent_id = patent_id.split('?')[0]
        except Exception as e:
            self.log(f"[Error] URL parse failed: {patent_url}")
            return False

        # 2. 创建目录
        save_dir = os.path.join(BASE_REPO_DIR, f"{patent_id}_data")
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        json_path = os.path.join(save_dir, "metadata.json")
        self.log(f"Analyzing: {patent_id} ...")
        
        # 3. 请求网页
        try:
            resp = requests.get(patent_url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            resp.encoding = 'utf-8'
            soup = BeautifulSoup(resp.text, 'html.parser')
        except Exception as e:
            self.log(f"[Fail] Web request error: {e}")
            return False

        # 4. 提取元数据
        title = "Unknown Title"
        h1_tag = soup.find('h1')
        if h1_tag: title = self.clean_text(h1_tag.get_text())

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

        inventor = "Unknown"
        for elem in soup.find_all(string=re.compile("Inventor")):
            parent = elem.find_parent()
            if parent:
                full_text = self.clean_text(parent.get_text())
                if "Inventor" in full_text:
                    inventor = full_text.split("Inventor")[-1].replace(":", "").strip()
                break

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

        citations = self.extract_table_data(soup, "backwardReferences")
        cited_by = self.extract_table_data(soup, "forwardReferences")
        similar_docs = self.extract_similar_docs(soup)

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

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=4)
        
        # 5. 保存摘要
        abs_path = os.path.join(save_dir, 'abstract.txt')
        if not os.path.exists(abs_path):
            abstract_text = "N/A"
            abs_section = soup.find('section', {'itemprop': 'abstract'})
            if abs_section:
                abstract_text = abs_section.get_text(separator="\n", strip=True)
                if abstract_text.lower().startswith("abstract"): abstract_text = abstract_text[8:].strip()
            with open(abs_path, 'w', encoding='utf-8') as f:
                f.write(f"URL: {patent_url}\n\n{abstract_text}")

        # 6. 下载 PDF
        pdf_path = os.path.join(save_dir, f"{patent_id}.pdf")
        if not os.path.exists(pdf_path):
            pdf_link = None
            for a in soup.find_all('a', href=re.compile(r'\.pdf$')):
                pdf_link = a['href']
                break
            if pdf_link:
                self.log(f"   [Download] PDF...")
                self.download_file(pdf_link, pdf_path)

        # 7. 保存描述 HTML 和内嵌图片
        html_path = os.path.join(save_dir, 'description.html')
        if not os.path.exists(html_path):
            desc_section = soup.find('section', {'itemprop': 'description'})
            if desc_section:
                desc_img_dir = os.path.join(save_dir, 'description_images')
                if not os.path.exists(desc_img_dir): os.makedirs(desc_img_dir)
                
                # 下载描述中的图片
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
                
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(f"<html><head><meta charset='utf-8'></head><body><h1>{patent_id}</h1>{str(desc_section)}</body></html>")

        # 8. 下载附图 (Figures)
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
        data = []
        rows = soup.find_all('tr', {'itemprop': itemprop})
        if not rows: return []
        for row in rows:
            cells = row.find_all('td')
            if not cells: continue
            link_tag = cells[0].find('a')
            pub_num = self.clean_text(cells[0].get_text())
            link = ("https://patents.google.com" + link_tag['href']) if link_tag else ""
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

# ================= 共享状态与后台逻辑 =================
download_queue = queue.Queue()
is_downloading = False
is_paused = False
skip_current = False
skipped_patents = set()
log_messages = []

def load_skipped_list():
    global skipped_patents
    if os.path.exists(SKIPPED_FILE):
        try:
            with open(SKIPPED_FILE, 'r', encoding='utf-8') as f:
                skipped_patents = set(json.load(f))
        except:
            skipped_patents = set()
    else:
        skipped_patents = set()

def save_skipped_list():
    try:
        with open(SKIPPED_FILE, 'w', encoding='utf-8') as f:
            json.dump(list(skipped_patents), f)
    except:
        pass

def server_log(msg):
    global log_messages
    print(f"[Core] {msg}")
    # 保留最近50条日志供前端轮询
    log_messages.append(msg)
    if len(log_messages) > 50:
        log_messages.pop(0)

# 初始化爬虫实例
scraper = PatentScraper(update_callback=server_log)
load_skipped_list()

# 工作线程：不断从队列取 URL 并下载
def worker_thread():
    global is_downloading, is_paused, skip_current
    while True:
        if is_paused:
            time.sleep(1)
            continue
        
        try:
            # 队列等待 2秒
            url = download_queue.get(timeout=2)
        except queue.Empty:
            # 空闲状态，什么也不做
            continue
        
        # 开始处理任务
        skip_current = False
        try:
            clean_id = url.split('/')[-1]
            if 'patent' in url: clean_id = url.split('/')[-2]
        except:
            clean_id = "unknown"

        server_log(f"Processing: {clean_id}")
        
        # 执行爬虫
        success = scraper.scrape_patent(url)
        
        if success:
            if clean_id in skipped_patents:
                skipped_patents.remove(clean_id)
                save_skipped_list()
        
        download_queue.task_done()

# 启动后台线程
bg_thread = threading.Thread(target=worker_thread, daemon=True)
bg_thread.start()


# ================= FastAPI App (Web API) =================
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

# 允许跨域，方便 admin.html 调用
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class UrlItem(BaseModel):
    url: str

@app.get("/api/patents/list")
def get_patents_list():
    """返回 Patents 目录下的所有专利状态"""
    if not os.path.exists(BASE_REPO_DIR):
        return {"data": []}
    
    # 扫描所有 _data 文件夹
    dirs = sorted([d for d in os.listdir(BASE_REPO_DIR) if d.endswith('_data')])
    results = []
    
    for d in dirs:
        pid = d.replace('_data', '')
        json_path = os.path.join(BASE_REPO_DIR, d, "metadata.json")
        
        # 默认状态
        status = "Pending"
        if pid in skipped_patents: status = "Skipped"
        
        item = {
            "id": pid,
            "status": status,
            "title": "N/A",
            "patent_status": "Unknown"
        }
        
        # 如果 metadata.json 存在，说明已下载
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    item['status'] = "Done"
                    item['patent_status'] = data.get('status', 'Unknown')
                    item['title'] = data.get('title', '')
            except: 
                pass
        
        results.append(item)
    return {"data": results}

@app.post("/api/patents/add")
def add_url(item: UrlItem):
    """前端添加下载任务"""
    if item.url:
        download_queue.put(item.url)
        return {"status": "ok", "msg": f"Added {item.url}"}
    return {"status": "error", "msg": "Empty URL"}

@app.get("/api/patents/control")
def control_task(action: str):
    """控制爬虫状态: start, pause, skip"""
    global is_downloading, is_paused, skip_current
    msg = ""
    if action == "start":
        is_downloading = True
        is_paused = False
        msg = "Task Started"
    elif action == "pause":
        is_paused = not is_paused
        msg = "Paused" if is_paused else "Resumed"
    elif action == "skip":
        skip_current = True
        msg = "Skipped Current"
    
    return {
        "status": "ok", 
        "msg": msg, 
        "is_paused": is_paused, 
        "is_downloading": is_downloading
    }

@app.get("/api/patents/logs")
def get_logs():
    """前端轮询日志"""
    return {"logs": log_messages, "queue_size": download_queue.qsize()}


# ================= GUI / Server 启动入口 =================
if __name__ == "__main__":
    # 如果命令行带 --server 参数，只启动 Web 服务 (云端模式)
    if len(sys.argv) > 1 and sys.argv[1] == '--server':
        import uvicorn
        print("Starting Headless Server Mode (FastAPI)...")
        uvicorn.run(app, host="0.0.0.0", port=8001)
    
    else:
        # 否则启动 Tkinter GUI (本地模式)，同时在后台启动 FastAPI 方便调试
        import tkinter as tk
        from tkinter import ttk, filedialog, messagebox
        
        class PatentAppGUI:
            def __init__(self, root):
                self.root = root
                self.root.title("Google Patents Collector (Local GUI)")
                self.root.geometry("1000x700")
                
                # 将爬虫日志重定向到 GUI
                global scraper
                scraper.update_callback = self.gui_log

                # UI 布局
                top_frame = tk.Frame(root, pady=10)
                top_frame.pack(fill=tk.X)
                
                tk.Label(top_frame, text="URL:").pack(side=tk.LEFT, padx=5)
                self.url_entry = tk.Entry(top_frame, width=50)
                self.url_entry.pack(side=tk.LEFT, padx=5)
                
                tk.Button(top_frame, text="Add", command=self.add_url).pack(side=tk.LEFT)
                tk.Button(top_frame, text="Start Queue", command=self.start_queue).pack(side=tk.LEFT, padx=5)
                tk.Button(top_frame, text="Refresh List", command=self.refresh_list).pack(side=tk.LEFT)

                # 列表
                self.tree = ttk.Treeview(root, columns=("ID", "Status", "Title"), show="headings")
                self.tree.heading("ID", text="ID")
                self.tree.column("ID", width=150)
                self.tree.heading("Status", text="Status")
                self.tree.column("Status", width=100)
                self.tree.heading("Title", text="Title")
                self.tree.column("Title", width=600)
                self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                
                # 日志框
                self.log_text = tk.Text(root, height=10)
                self.log_text.pack(fill=tk.X, padx=10, pady=10)

                self.refresh_list()

            def gui_log(self, msg):
                self.log_text.insert(tk.END, msg + "\n")
                self.log_text.see(tk.END)
                # 同时写入服务器日志缓存，防止丢失
                server_log(msg) 

            def add_url(self):
                u = self.url_entry.get()
                if u: 
                    download_queue.put(u)
                    self.gui_log(f"Added to queue: {u}")
                    self.url_entry.delete(0, tk.END)

            def start_queue(self):
                global is_downloading, is_paused
                is_downloading = True
                is_paused = False
                self.gui_log("Queue Started")

            def refresh_list(self):
                # 清空现有
                for i in self.tree.get_children(): self.tree.delete(i)
                # 调用 API 函数获取数据 (直接调用函数，不走 HTTP，因为是同进程)
                data = get_patents_list()['data']
                for item in data:
                    self.tree.insert("", tk.END, values=(item['id'], item['status'], item['title']))

        root = tk.Tk()
        app_gui = PatentAppGUI(root)
        
        # 在守护线程中启动 FastAPI，这样 GUI 不会卡死
        def run_api_local():
            import uvicorn
            # 本地运行在 8001 端口
            uvicorn.run(app, host="127.0.0.1", port=8001, log_level="error")
        
        api_thread = threading.Thread(target=run_api_local, daemon=True)
        api_thread.start()
        
        print("Local GUI Started. API available at http://127.0.0.1:8001")
        root.mainloop()