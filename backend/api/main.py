"""
Optional lightweight read-only API server for summary metrics, forecasts, and decision logs.
Supports FastAPI if installed, with a zero-dependency http.server fallback.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = ROOT / "data" / "output"
GT_DIR = ROOT / "data" / "ground_truth"

def get_summary():
    path = OUTPUT_DIR / "summary.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"error": "Summary data not found. Run generator first."}

def get_table(table_name: str, limit: int = 50):
    path = OUTPUT_DIR / f"{table_name}.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data[:limit]
    return {"error": f"Table {table_name} not found"}

def get_ground_truth(limit: int = 50):
    path = GT_DIR / "ground_truth.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data[:limit]
    return {"error": "Ground truth not found"}

try:
    from fastapi import FastAPI
    import uvicorn

    app = FastAPI(title="Course Demand Planner API", version="1.0.0")

    @app.get("/api/summary")
    def api_summary():
        return get_summary()

    @app.get("/api/forecasts")
    def api_forecasts(limit: int = 50):
        return get_table("demand_forecast", limit)

    @app.get("/api/sections")
    def api_sections(limit: int = 50):
        return get_table("section", limit)

    @app.get("/api/decisions")
    def api_decisions(limit: int = 50):
        return get_table("decision_log", limit)

    @app.get("/api/ground_truth")
    def api_ground_truth(limit: int = 50):
        return get_ground_truth(limit)

    def run_server():
        uvicorn.run(app, host="127.0.0.1", port=8000)

except ImportError:
    import http.server
    import socketserver

    class CustomHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/api/summary":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(get_summary()).encode("utf-8"))
            elif self.path.startswith("/api/forecasts"):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(get_table("demand_forecast")).encode("utf-8"))
            elif self.path.startswith("/api/decisions"):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(get_table("decision_log")).encode("utf-8"))
            elif self.path.startswith("/api/ground_truth"):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(get_ground_truth()).encode("utf-8"))
            else:
                super().do_GET()

    def run_server():
        PORT = 8000
        with socketserver.TCPServer(("127.0.0.1", PORT), CustomHandler) as httpd:
            print(f"API Server running at http://127.0.0.1:{PORT}/api/summary")
            httpd.serve_forever()

if __name__ == "__main__":
    run_server()

