"""
AeroScope Unified Server
- 启动专利采集 API + 静态文件服务
- 自动打开浏览器
Usage: python serve.py [--port 8765]
"""
import os, sys, json, threading, uuid, webbrowser, ssl
ssl._create_default_https_context = ssl._create_unverified_context
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# 项目根目录（serve.py 在 pyScript/ 下，需指向上一级）
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT_DIR, "pyScript"))
from dotenv import load_dotenv; load_dotenv()
from collector_core import CollectorCore
from admin_patent_collector import CompanyPatentCollector
from patent_sweeper import PatentSweeper

import oss2

PORT = 8765
active_tasks = {}


class AeroServe(BaseHTTPRequestHandler):
    """统一处理器: API + 静态文件"""

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        params = parse_qs(urlparse(self.path).query)

        # API 路由
        if path.startswith("/api/"):
            self._json(self._handle_api_get(path, params))
            return

        # PDF 代理路由 - 从OSS获取并以内嵌方式返回
        if path.startswith("/pdf/"):
            self._serve_pdf(path)
            return

        # 静态文件（从项目根目录读取）
        req_path = self.path.split("?")[0].lstrip("/")
        file_path = os.path.join(ROOT_DIR, req_path or "index.html")
        if os.path.isfile(file_path):
            ext = os.path.splitext(file_path)[1].lower()
            ctype = {"html": "text/html", "css": "text/css", "js": "application/javascript", "json": "application/json", "png": "image/png", "jpg": "image/jpeg", "svg": "image/svg+xml", "ico": "image/x-icon"}.get(ext, "text/html")
            with open(file_path, "rb") as f:
                self.send_response(200)
                self.send_header("Content-Type", f"{ctype}; charset=utf-8")
                self.end_headers()
                self.wfile.write(f.read())
        else:
            # 真正的 404
            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(f"404 Not Found: {req_path}".encode())

    def do_POST(self):
        path = urlparse(self.path).path
        cl = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(cl)) if cl else {}

        if path == "/api/chat":
            self._handle_chat(body)
            return

        if path == "/api/patents/import":
            self._handle_patent_import(body)
            return

        self._json(self._handle_api_post(path, body))

    def _handle_patent_import(self, body):
        """接收一条专利 JSON，upsert 到 Supabase"""
        if not body or not body.get("patent_number"):
            self._json({"error": "patent_number required"}, 400)
            return
        try:
            from collector_core import CollectorCore
            core = CollectorCore()
            # 清理非法字段
            for bad in ['_html','created_at','country_code']:
                body.pop(bad, None)
            body.setdefault('draft', False)
            ok = core.upsert('patents', body, 'patent_number')
            print(f"[IMPORT] {'OK' if ok else 'FAIL'}: {body.get('patent_number')} — {body.get('title','')[:40]}")
            self._json({"status": "ok" if ok else "fail", "patent_number": body["patent_number"]})
        except Exception as e:
            print(f"[IMPORT ERROR] {e}")
            self._json({"error": str(e)[:200]}, 500)

    def _serve_pdf(self, path):
        """代理OSS PDF，强制返回 Content-Disposition: inline"""
        key = path[len("/pdf/"):]
        if not key:
            self._json({"error": "missing pdf path"}, 400)
            return
        try:
            auth = oss2.Auth(os.getenv("ALIBABA_ACCESS_KEY_ID"), os.getenv("ALIBABA_ACCESS_KEY_SECRET"))
            bucket = oss2.Bucket(auth, os.getenv("OSS_ENDPOINT"), os.getenv("OSS_PRIVATE_BUCKET"))
            obj = bucket.get_object(key)
            pdf_bytes = obj.read()
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Disposition", "inline; filename={}".format(key.split("/")[-1]))
            self.send_header("Content-Length", str(len(pdf_bytes)))
            self.send_header("Cache-Control", "public, max-age=86400")
            self.end_headers()
            self.wfile.write(pdf_bytes)
        except Exception as e:
            self._json({"error": str(e)[:200]}, 404)

    def _handle_api_get(self, path, params):
        if path == "/api/patents/companies":
            core = CollectorCore()
            if not core.db:
                return {"error": "DB not connected"}
            r = core.db.table("companies").select("id,name,primary_category") \
                .not_.is_("name", "null").order("name").execute()
            companies = [{"id": c["id"], "name": c["name"] or "", "category": c.get("primary_category","")}
                         for c in (r.data or []) if len(c.get("name","")) >= 2]
            return {"companies": companies}

        elif path == "/api/patents/by_company":
            cn = params.get("company", [None])[0]
            if not cn: return {"error": "company required"}
            try:
                collector = CompanyPatentCollector()
                patents = collector.get_company_patents(cn)
                return {"company": cn, "patents": patents, "count": len(patents)}
            except Exception as e:
                return {"company": cn, "patents": [], "count": 0, "error": str(e)[:100]}

        elif path == "/api/patents/crawler_status":
            tid = params.get("task_id", [None])[0]
            if tid and tid in active_tasks:
                return active_tasks[tid]
            import json
            progress_file = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                         "agent-workspace", "data-engineer", "data-schemas", "crawler_progress.json")
            if os.path.exists(progress_file):
                with open(progress_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                stats = data.get("stats", {})
                latest3 = [p.get("patent_number","") + " " + p.get("title","")[:30]
                          for p in data.get("stored", [])[-3:]]
                return {
                    "visited": stats.get("visited", 0),
                    "matched": stats.get("matched", 0),
                    "backlog": stats.get("backlog", 0),
                    "saved": stats.get("saved", 0),
                    "latest": latest3
                }
            return {"visited": 0, "matched": 0, "backlog": 0, "saved": 0, "latest": []}

        elif path == "/api/patents/crawler_start":
            seed = params.get("seed", [None])[0]
            maxv = int(params.get("max", [200])[0])
            if not seed: return {"error": "seed required"}
            tid = str(uuid.uuid4())[:8]
            active_tasks[tid] = {"status": "running"}
            def run():
                try:
                    from patent_crawler import PatentCrawler
                    crawler = PatentCrawler()
                    result = crawler.crawl(seed, maxv)
                    active_tasks[tid] = {"status": "done", "result": result}
                except Exception as e:
                    active_tasks[tid] = {"status": "fail", "error": str(e)}
            threading.Thread(target=run, daemon=True).start()
            return {"task_id": tid, "status": "started"}

        elif path == "/api/patents/search_new":
            cn = params.get("company", [None])[0]
            mx = int(params.get("max", [10])[0])
            if not cn: return {"error": "company required"}
            collector = CompanyPatentCollector()
            results = collector.search_new_patents(cn, mx)
            return {"company": cn, "found": len(results), "results": results}

        elif path == "/api/patents/export":
            cn = params.get("company", [None])[0]
            if not cn: return {"error": "company required"}
            sweeper = PatentSweeper(cn)
            sweeper.export_summary_csv()
            return {"status": "ok", "path": sweeper._csv_path()}

        elif path == "/api/patents/status":
            tid = params.get("task_id", [None])[0]
            return active_tasks.get(tid, {"status": "unknown"})

        elif path == "/api/patents/health":
            return {"status": "ok"}

        return {"error": "not found"}

    def _handle_api_post(self, path, body):
        if path == "/api/patents/add_url":
            cn = body.get("company_name", "")
            pu = body.get("patent_url", "")
            if not cn or not pu:
                return {"error": "company_name and patent_url required"}
            tid = str(uuid.uuid4())[:8]
            active_tasks[tid] = {"status": "running"}
            def run():
                try:
                    collector = CompanyPatentCollector()
                    collector.add_patent_url(pu, cn)
                    active_tasks[tid] = {"status": "done", "result": {"status": "ok", "patent_id": collector._extract_patent_id(pu) or pu.split('/')[-1]}}
                except Exception as e:
                    active_tasks[tid] = {"status": "fail", "error": str(e)}
            threading.Thread(target=run, daemon=True).start()
            return {"task_id": tid, "status": "started"}

        elif path == "/api/patents/discover":
            cn = body.get("company_name", "")
            seed = body.get("seed_url", "")
            mx = body.get("max_patents", 30)
            if not cn or not seed:
                return {"error": "company_name and seed_url required"}

            tid = str(uuid.uuid4())[:8]
            active_tasks[tid] = {"status": "running"}
            def run():
                try:
                    sweeper = PatentSweeper(cn)
                    result = sweeper.quick_sweep(seed, mx)
                    active_tasks[tid] = {"status": "done", "result": result}
                except Exception as e:
                    active_tasks[tid] = {"status": "fail", "error": str(e)}
            threading.Thread(target=run, daemon=True).start()
            return {"task_id": tid, "status": "started"}

        elif path == "/api/policies/import-url":
            url = body.get("url", "")
            if not url: return {"error": "url required"}
            tid = str(uuid.uuid4())[:8]
            active_tasks[tid] = {"status": "running"}
            def run_import():
                try:
                    import requests as req
                    from bs4 import BeautifulSoup
                    from collector_core import CollectorCore
                    from llm_prompts import PATENT_PROMPT
                    resp = req.get(url, headers={'User-Agent':'Mozilla/5.0'}, timeout=15)
                    resp.encoding = 'utf-8'
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    for t in soup(['script','style','nav','footer']): t.decompose()
                    text = soup.get_text(separator='\n', strip=True)[:6000]
                    core = CollectorCore()
                    llm = core.call_llm(PATENT_PROMPT, text)
                    data = core.parse_llm_json(llm)
                    if data:
                        data['source_url'] = url; data['draft'] = True; data['level'] = '国家级'
                        active_tasks[tid] = {"status": "done", "result": data}
                    else:
                        active_tasks[tid] = {"status": "fail", "error": "LLM parse failed"}
                except Exception as e:
                    active_tasks[tid] = {"status": "fail", "error": str(e)}
            threading.Thread(target=run_import, daemon=True).start()
            return {"task_id": tid}

        elif path == "/api/policies/import-save":
            data = body.get("data", {})
            force = body.get("force", False)
            if not data or not data.get("title"): return {"error": "data required"}
            try:
                from collector_core import CollectorCore
                from difflib import SequenceMatcher
                data['draft'] = False
                core = CollectorCore()
                existing = core.db.table('policies').select('id').eq('title', data['title']).execute()
                if existing.data:
                    core.db_write.table('policies').update(data).eq('id', existing.data[0]['id']).execute()
                    return {"status": "ok", "action": "updated"}

                if not force:
                    alike = core.db.table('policies').select('id,title').limit(200).execute()
                    new_title = data['title']
                    for p in (alike.data or []):
                        score = SequenceMatcher(None, new_title, p['title']).ratio()
                        if score > 0.65:
                            return {
                                "status": "duplicate",
                                "action": "warn",
                                "similar": {"id": p['id'], "title": p['title'], "score": round(score, 2)},
                                "message": f"相似度{round(score*100)}%: 「{p['title'][:60]}」"
                            }

                core.db_write.table('policies').insert(data).execute()
                return {"status": "ok", "action": "created"}
            except Exception as e:
                return {"error": str(e)}

        return {"error": "not found"}

    def _handle_chat(self, body):
        question = (body or {}).get("message", "").strip()
        if not question:
            self._json({"error": "message is required"}, 400)
            return
        try:
            from chat_handler import ChatHandler
            handler = ChatHandler()
            result = handler.handle(question)
            self._json(result)
        except Exception as e:
            self._json({"error": str(e)[:300], "reply": "AI 服务暂时不可用，请稍后重试。"}, 500)

    def _json(self, data, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def _send404(self):
        self.send_response(302)
        self.send_header("Location", "/index.html")
        self.end_headers()

    def log_message(self, format, *args):
        pass  # 静默日志


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    print(f"╔══════════════════════════════════════╗")
    print(f"║   AeroScope Server                  ║")
    print(f"║   http://0.0.0.0:{args.port}          ║")
    print(f"╚══════════════════════════════════════╝")
    print(f"   API: http://0.0.0.0:{args.port}/api/patents/health")
    print(f"   Admin: http://0.0.0.0:{args.port}/admin/admin.html")
    print()

    if not args.no_browser:
        webbrowser.open(f"http://127.0.0.1:{args.port}/admin/admin.html")

    server = HTTPServer(("0.0.0.0", args.port), AeroServe)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.shutdown()
