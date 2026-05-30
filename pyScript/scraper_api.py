"""
AeroScope Scraper API Server
Provides HTTP endpoints for admin.html to trigger patent collection.
Usage: python pyScript/scraper_api.py [--port 8765]
"""
import os, sys, json, threading, uuid
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from dotenv import load_dotenv; load_dotenv()
from collector_core import CollectorCore
from admin_patent_collector import CompanyPatentCollector

PORT = 8765
active_tasks = {}  # task_id -> {"status": "running/done/fail", "result": ...}


class ScraperHandler(BaseHTTPRequestHandler):
    def _send_json(self, data, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        params = parse_qs(urlparse(self.path).query)

        if path == "/api/patents/companies":
            core = CollectorCore()
            if not core.db: return self._send_json({"error": "DB not connected"}, 500)
            r = core.db.table("companies").select("id,name,primary_category") \
                .not_.is_("name", "null").order("name").execute()
            companies = [{"id": c["id"], "name": c["name"] or "", "category": c.get("primary_category","")}
                         for c in (r.data or []) if len(c.get("name","")) >= 2]
            self._send_json({"companies": companies})

        elif path == "/api/patents/by_company":
            company_name = params.get("company", [None])[0]
            if not company_name: return self._send_json({"error": "company required"}, 400)
            collector = CompanyPatentCollector()
            patents = collector.get_company_patents(company_name)
            self._send_json({"company": company_name, "patents": patents, "count": len(patents)})

        elif path == "/api/patents/search_new":
            company_name = params.get("company", [None])[0]
            max_results = int(params.get("max", [10])[0])
            if not company_name: return self._send_json({"error": "company required"}, 400)
            collector = CompanyPatentCollector()
            results = collector.search_new_patents(company_name, max_results)
            self._send_json({"company": company_name, "found": len(results), "results": results})

        elif path == "/api/patents/status":
            task_id = params.get("task_id", [None])[0]
            if task_id and task_id in active_tasks:
                self._send_json(active_tasks[task_id])
            else:
                self._send_json({"status": "unknown"})

        elif path == "/api/patents/health":
            self._send_json({"status": "ok", "active_tasks": len(active_tasks)})

        else:
            self._send_json({"error": "not found"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        content_len = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(content_len)) if content_len else {}

        if path == "/api/patents/add_url":
            company_name = body.get("company_name", "")
            patent_url = body.get("patent_url", "")
            if not company_name or not patent_url:
                return self._send_json({"error": "company_name and patent_url required"}, 400)

            import uuid
            task_id = str(uuid.uuid4())[:8]
            active_tasks[task_id] = {"status": "running", "action": "add_url", "url": patent_url, "result": None}

            def run_task():
                try:
                    collector = CompanyPatentCollector()
                    result = collector.add_patent_url(patent_url, company_name)
                    active_tasks[task_id] = {"status": "done", "result": result}
                except Exception as e:
                    active_tasks[task_id] = {"status": "fail", "error": str(e)}
            threading.Thread(target=run_task, daemon=True).start()
            self._send_json({"task_id": task_id, "status": "started"})

        elif path == "/api/patents/collect":
            company_name = body.get("company_name", "")
            max_results = body.get("max_results", 10)
            if not company_name:
                return self._send_json({"error": "company_name required"}, 400)

            import uuid
            task_id = str(uuid.uuid4())[:8]
            active_tasks[task_id] = {"status": "running", "action": "collect", "company": company_name, "result": None}

            def run_collect():
                try:
                    collector = CompanyPatentCollector()
                    result = collector.collect_new_patents(company_name, max_results)
                    active_tasks[task_id] = {"status": "done", "company": company_name, "result": result}
                except Exception as e:
                    active_tasks[task_id] = {"status": "fail", "error": str(e)}
            threading.Thread(target=run_collect, daemon=True).start()
            self._send_json({"task_id": task_id, "status": "started"})


def start_server(port=PORT):
    print(f"Starting AeroScope Scraper API on http://127.0.0.1:{port}")
    print("Endpoints:")
    print("  GET  /api/patents/companies   - List all companies")
    print("  POST /api/patents/search       - Search patents by company")
    print("  GET  /api/patents/status       - Check task status")
    print("  GET  /api/patents/health       - Health check")
    server = HTTPServer(("127.0.0.1", port), ScraperHandler)
    server.serve_forever()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args()
    start_server(args.port)
