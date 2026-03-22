#!/usr/bin/env python3
"""VibeSafe Web Scanner — API server."""
from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path

# Add project root to path
PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading
import subprocess
import tempfile
import shutil


# In-memory scan results store
SCANS: dict[str, dict] = {}

STATIC_DIR = Path(__file__).parent / "static"


class VibeSafeHandler(SimpleHTTPRequestHandler):
    """Handle API requests and serve static files."""

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/scan/status":
            scan_id = parse_qs(parsed.query).get("id", [None])[0]
            if not scan_id or scan_id not in SCANS:
                self._json_response({"error": "not found"}, 404)
                return
            self._json_response(SCANS[scan_id])
            return

        # Serve static files
        if parsed.path == "/":
            self._serve_file(STATIC_DIR / "index.html", "text/html")
        elif parsed.path.startswith("/static/"):
            file_path = STATIC_DIR / parsed.path[8:]
            if file_path.exists():
                content_type = "text/css" if str(file_path).endswith(".css") else "application/javascript"
                self._serve_file(file_path, content_type)
            else:
                self.send_error(404)
        else:
            self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/scan":
            content_length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(content_length)) if content_length else {}
            repo_url = body.get("url", "").strip()

            # Normalize URL for beginner-friendly input
            repo_url = repo_url.rstrip("/")
            if repo_url.startswith("github.com/"):
                repo_url = "https://" + repo_url
            # Strip /tree/main, /tree/master, /blob/... suffixes
            for suffix in ["/tree/main", "/tree/master", "/tree/", "/blob/"]:
                idx = repo_url.find(suffix)
                if idx > 0:
                    repo_url = repo_url[:idx]
                    break

            if not repo_url or not repo_url.startswith("https://github.com/"):
                self._json_response({"error": "Please enter a GitHub URL (e.g. github.com/your/repo)"}, 400)
                return

            scan_id = str(uuid.uuid4())[:8]
            SCANS[scan_id] = {"status": "scanning", "url": repo_url}

            # Run scan in background thread
            thread = threading.Thread(target=self._run_scan, args=(scan_id, repo_url))
            thread.daemon = True
            thread.start()

            self._json_response({"id": scan_id, "status": "scanning"})
            return

        self.send_error(404)

    def _run_scan(self, scan_id: str, repo_url: str):
        """Run scan in background."""
        try:
            result = subprocess.run(
                [sys.executable, str(PROJECT_DIR / "tools" / "cli_scanner.py"),
                 repo_url, "--json", "--light"],
                capture_output=True, text=True, timeout=90,
                env={**os.environ, "SEMGREP_MAX_MEMORY": "400"},
            )
            if result.returncode == 0:
                scan_data = json.loads(result.stdout)
                SCANS[scan_id] = {
                    "status": "done",
                    "url": repo_url,
                    "results": scan_data,
                }
            else:
                SCANS[scan_id] = {
                    "status": "error",
                    "url": repo_url,
                    "error": result.stdout[:500] or result.stderr[:500],
                }
        except subprocess.TimeoutExpired:
            SCANS[scan_id] = {"status": "error", "url": repo_url, "error": "This repo is too large for our free scanner. Try a smaller repo, or install the GitHub Action for unlimited scanning."}
        except Exception as e:
            SCANS[scan_id] = {"status": "error", "url": repo_url, "error": str(e)}

    def _json_response(self, data: dict, code: int = 200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _serve_file(self, path: Path, content_type: str):
        if not path.exists():
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.end_headers()
        self.wfile.write(path.read_bytes())

    def log_message(self, format, *args):
        """Suppress default logging for cleaner output."""
        pass


def main():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), VibeSafeHandler)
    print(f"VibeSafe Web Scanner running at http://localhost:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
