import io
import json
import re
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

# Heavy imports deferred to request time so import failures return 500 instead of FUNCTION_INVOCATION_FAILED
MAX_CSV_FNAME = 255


def _sanitize_filename(s: str) -> str:
    name = re.sub(r"[\s:]+", "_", s)[:MAX_CSV_FNAME]
    return name or "scholar_results"


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict):
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _load_deps():
    """Load pandas and sortgs_runner; raise on failure."""
    import pandas as pd  # noqa: F401
    _api_dir = Path(__file__).resolve().parent
    if str(_api_dir) not in sys.path:
        sys.path.insert(0, str(_api_dir))
    import sortgs_runner  # noqa: E402
    return pd, sortgs_runner.run_search


class handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # avoid stderr output that can interfere on serverless

    def do_GET(self):
        """Health check so we can confirm the function is deployed."""
        _json_response(self, 200, {"status": "ok", "service": "search"})
        return

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        try:
            return self._do_post_impl()
        except Exception as e:
            _json_response(self, 500, {"error": f"Server error: {type(e).__name__}: {str(e)}"})
            return

    def _do_post_impl(self):
        try:
            pd, run_search = _load_deps()
        except Exception as e:
            return _json_response(self, 500, {"error": f"Dependency load failed: {type(e).__name__}: {str(e)}"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length > 0 else b"{}"
            data = json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            return _json_response(self, 400, {"error": "Invalid JSON body"})

        keyword = str(data.get("keyword", "")).strip()
        if not keyword:
            return _json_response(self, 400, {"error": "keyword is required"})

        exact_phrase = bool(data.get("exact_phrase", False))
        if exact_phrase:
            keyword = f"'{keyword}'"

        sortby = data.get("sortby", "Citations")
        if sortby not in ("Citations", "cit/year"):
            sortby = "Citations"

        start_year = data.get("start_year", None)
        end_year = data.get("end_year", None)
        try:
            start_year = int(start_year) if start_year is not None else None
        except Exception:
            start_year = None
        try:
            end_year = int(end_year) if end_year is not None else None
        except Exception:
            end_year = None

        langfilter = data.get("langfilter", None)
        if isinstance(langfilter, list) and len(langfilter) > 0:
            langfilter_val = [str(x) for x in langfilter]
        else:
            langfilter_val = "All"

        nresults = data.get("nresults", 100)
        try:
            nresults = int(nresults)
        except Exception:
            nresults = 100
        # Cap at 30 for serverless (3 pages) to stay within Vercel maxDuration
        nresults = max(10, min(30, nresults))

        fmt = str(data.get("format", "xlsx")).lower()
        if fmt not in ("xlsx", "csv"):
            fmt = "xlsx"

        try:
            df = run_search(
                keyword=keyword,
                nresults=nresults,
                sortby=sortby,
                start_year=start_year,
                end_year=end_year,
                langfilter=langfilter_val,
                debug=False,
                delay_seconds=0,
                request_timeout=8,
            )
        except Exception as e:
            return _json_response(self, 502, {"error": f"Search failed: {str(e)}"})

        base_name = _sanitize_filename(keyword.replace("'", ""))
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")

        if fmt == "csv":
            buf = io.StringIO()
            df.to_csv(buf, encoding="utf-8", index=True)
            payload = buf.getvalue().encode("utf-8")
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header(
                "Content-Disposition", f'attachment; filename="{base_name}.csv"'
            )
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        # xlsx
        b = io.BytesIO()
        with pd.ExcelWriter(b, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Results", index=True)
        payload = b.getvalue()
        self.send_header(
            "Content-Type",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.send_header(
            "Content-Disposition", f'attachment; filename="{base_name}.xlsx"'
        )
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)
